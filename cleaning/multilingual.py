"""
Chunked multilingual translation engine.
This is the CORE FIX for the column detection + LLM overflow problem.

Key design decisions:
1. Only non-ASCII values are sent to the LLM (ASCII values are handled locally)
2. Non-ASCII values are sent in small chunks (10-15 items) to prevent token overflow
3. Separate prompts for translation (categories) vs transliteration (names)
4. Fallback to single-item queries for any keys the LLM misses
"""
import re
import json
import pandas as pd
from typing import Dict, List, Tuple
from agents.llm_client import LMStudioClient
from backend.schema_detector import has_non_ascii
import config


class MultilingualEngine:
    """
    Handles all multilingual processing: script detection, chunked translation,
    and chunked transliteration.
    """

    def __init__(self, llm_client: LMStudioClient = None):
        self.llm_client = llm_client or LMStudioClient()
        self.chunk_size = config.LLM_CHUNK_SIZE
        self.stats = {}  # Track what was translated/transliterated

    def _chunk_list(self, items: list, size: int) -> List[list]:
        """Split a list into chunks of the given size."""
        return [items[i:i + size] for i in range(0, len(items), size)]

    # ──────────────────────────────────────────────
    #  CATEGORICAL TRANSLATION (e.g. customer_type, order_status)
    # ──────────────────────────────────────────────
    def translate_categorical_column(
        self, series: pd.Series, column_name: str
    ) -> Dict[str, str]:
        """
        Translate and standardize all values in a categorical column.
        Only non-ASCII values go to the LLM; ASCII values are normalized locally.
        Returns a mapping: {original_value -> standardized_english_value}
        """
        unique_vals = [
            str(v).strip()
            for v in series.dropna().unique()
            if str(v).strip() not in ["", "nan", "None", "<NA>"]
        ]

        ascii_vals = [v for v in unique_vals if not has_non_ascii(v)]
        non_ascii_vals = [v for v in unique_vals if has_non_ascii(v)]

        mapping = {}

        # Step 1: Normalize ASCII values locally (no LLM needed)
        # Group by case-insensitive match and pick canonical form
        ascii_groups = {}
        for v in ascii_vals:
            key = v.strip().lower()
            if key not in ascii_groups:
                ascii_groups[key] = v.strip()
        for v in ascii_vals:
            canonical = ascii_groups[v.strip().lower()]
            # Preserve known acronyms
            if canonical.upper() in ["B2B", "B2C", "B2G", "COD", "EMI", "ID", "SKU"]:
                mapping[v] = canonical.upper()
            else:
                mapping[v] = canonical.title()

        # Step 2: Translate non-ASCII values via LLM in chunks
        if non_ascii_vals:
            print(f"  [Multilingual] Translating {len(non_ascii_vals)} non-English values in '{column_name}' ({len(non_ascii_vals) // self.chunk_size + 1} chunks)...")

            # Collect known English targets from ASCII values to anchor translations
            known_english = list(set(mapping.values()))

            chunks = self._chunk_list(non_ascii_vals, self.chunk_size)
            for i, chunk in enumerate(chunks):
                print(f"    -> Chunk {i + 1}/{len(chunks)} ({len(chunk)} items)...")
                chunk_map = self._translate_chunk(chunk, column_name, known_english)
                mapping.update(chunk_map)

            # Fallback: any non-ASCII values that the LLM missed
            for val in non_ascii_vals:
                if val not in mapping:
                    mapping[val] = self._translate_single_fallback(val, column_name)

        self.stats[column_name] = {
            "task": "Translation/Standardization",
            "ascii_normalized": len(ascii_vals),
            "llm_translated": len(non_ascii_vals),
            "mapping": mapping,
        }

        return mapping

    def _translate_chunk(
        self, values: list, column_name: str, known_english: list
    ) -> Dict[str, str]:
        """Send a chunk of non-ASCII values to the LLM for translation."""
        known_hint = ""
        if known_english:
            known_hint = (
                f"\nKnown valid English values for this column: {json.dumps(known_english[:15])}\n"
                f"Map translations to one of these where appropriate.\n"
            )

        system_prompt = (
            f"You are a professional data translation engine.\n"
            f"Translate non-English values to their correct English equivalent.\n"
            f"{known_hint}\n"
            f"RULES:\n"
            f"1. Return ONLY a JSON object mapping each input value to its English translation.\n"
            f"2. Every input key MUST appear in the output.\n"
            f"3. Translate accurately (e.g., Hindi 'भुगतान' -> 'Paid', Tamil 'செலுத்தப்பட்டது' -> 'Paid').\n"
            f"4. Do not include any markdown, conversational text, or explanations.\n\n"
            f"EXAMPLE INPUT:\n"
            f'["खुदरा", "रद्द"]\n'
            f"EXAMPLE OUTPUT:\n"
            f'{{"खुदरा": "Retail", "रद्द": "Cancelled"}}'
        )
        user_prompt = f"Values:\n{json.dumps(values, ensure_ascii=False)}\n\nOUTPUT JSON:"

        result = self.llm_client.chat_completion_json(
            system_prompt, user_prompt, num_expected_keys=len(values)
        )

        if isinstance(result, dict):
            # Normalize the returned values
            cleaned = {}
            for k, v in result.items():
                k_str = str(k).strip()
                v_str = str(v).strip()
                if v_str and v_str.lower() not in ["nan", "none", ""]:
                    cleaned[k_str] = v_str.title() if v_str.upper() not in ["B2B", "B2C", "B2G", "COD"] else v_str.upper()
            return cleaned
        return {}

    def _translate_single_fallback(self, term: str, column_name: str) -> str:
        """Single-item translation fallback when batch LLM misses a key."""
        if not has_non_ascii(term):
            return term.title()

        print(f"      [Fallback] Translating '{term}'...")
        system_prompt = (
            f"Translate this value from the column '{column_name}' to English.\n"
            f"Return ONLY the English translation. No quotes, no explanation.\n"
            f"EXAMPLE: खुदरा -> Retail"
        )
        user_prompt = f"Value: {term}\n\nTranslation:"

        result = self.llm_client.chat_completion(
            system_prompt, user_prompt, max_tokens=100
        )
        result = re.sub(r'^[`"\'\s]+|[`"\'\s]+$', "", result).strip()
        return result.title() if result else term

    # ──────────────────────────────────────────────
    #  NAME TRANSLITERATION (e.g. customer_name)
    # ──────────────────────────────────────────────
    def transliterate_name_column(self, series: pd.Series) -> Dict[str, str]:
        """
        Transliterate non-ASCII names to Latin English phonetically.
        Only non-ASCII names go to the LLM. ASCII names are kept as-is.
        Returns a mapping: {original_name -> transliterated_name}
        """
        unique_names = [
            str(v).strip()
            for v in series.dropna().unique()
            if str(v).strip() not in ["", "nan", "None", "<NA>"]
        ]

        ascii_names = [n for n in unique_names if not has_non_ascii(n)]
        non_ascii_names = [n for n in unique_names if has_non_ascii(n)]

        mapping = {}

        # ASCII names: normalize spacing and casing
        for name in ascii_names:
            cleaned = re.sub(r'\s+', ' ', name.strip()).title()
            mapping[name] = cleaned

        # Non-ASCII names: transliterate via LLM in chunks
        if non_ascii_names:
            print(f"  [Multilingual] Transliterating {len(non_ascii_names)} non-Latin names ({len(non_ascii_names) // self.chunk_size + 1} chunks)...")

            chunks = self._chunk_list(non_ascii_names, self.chunk_size)
            for i, chunk in enumerate(chunks):
                print(f"    -> Chunk {i + 1}/{len(chunks)} ({len(chunk)} items)...")
                chunk_map = self._transliterate_chunk(chunk)
                mapping.update(chunk_map)

            # Fallback: any names the LLM missed
            for name in non_ascii_names:
                if name not in mapping:
                    mapping[name] = self._transliterate_single_fallback(name)

        return mapping

    def _transliterate_chunk(self, names: list) -> Dict[str, str]:
        """Send a chunk of non-ASCII names to the LLM for transliteration."""
        system_prompt = (
            "You are a precise name transliteration engine.\n"
            "Transliterate each non-Latin name to its English phonetic representation.\n\n"
            "CRITICAL RULES:\n"
            "1. Phonetic transliteration ONLY. Do NOT translate meaning.\n"
            "   - आकाश -> Akash (NOT 'Sky')\n"
            "   - समीप -> Sameep (NOT 'Near')\n"
            "2. Return ONLY a valid JSON object mapping original names to transliterated names.\n"
            "3. Do not include any markdown formatting, conversational text, or explanations.\n\n"
            "EXAMPLE INPUT:\n"
            '["आकाश", "நேஹா"]\n'
            "EXAMPLE OUTPUT:\n"
            '{"आकाश": "Akash", "நேஹா": "Neha"}'
        )
        user_prompt = f"Names:\n{json.dumps(names, ensure_ascii=False)}\n\nOUTPUT JSON:"

        result = self.llm_client.chat_completion_json(
            system_prompt, user_prompt, num_expected_keys=len(names)
        )

        if isinstance(result, dict):
            cleaned = {}
            for k, v in result.items():
                k_str = str(k).strip()
                v_str = str(v).strip()
                if v_str and v_str.lower() not in ["nan", "none", ""]:
                    # Title-case the name
                    cleaned[k_str] = re.sub(r'\s+', ' ', v_str).title()
            return cleaned
        return {}

    def _transliterate_single_fallback(self, name: str) -> str:
        """Single-item transliteration fallback."""
        if not has_non_ascii(name):
            return name.title()

        print(f"      [Fallback] Transliterating '{name}'...")
        system_prompt = (
            "Transliterate this name phonetically to Latin English script.\n"
            "Do NOT translate meaning. Return ONLY the transliterated name.\n"
            "EXAMPLE: आकाश -> Akash\n"
            "EXAMPLE: நேஹா -> Neha"
        )
        user_prompt = f"Name: {name}\n\nTransliteration:"

        result = self.llm_client.chat_completion(
            system_prompt, user_prompt, max_tokens=100
        )
        result = re.sub(r'^[`"\'\s]+|[`"\'\s]+$', "", result).strip()
        return result.title() if result else name
