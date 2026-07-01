"""
Explanation agent: generates human-readable explanations for cleaning
decisions to create an audit trail.
"""
import os
import json
from typing import Dict, List
from agents.llm_client import LMStudioClient


class ExplanationAgent:
    """
    Generates natural language explanations for each cleaning transformation,
    creating a human-readable audit trail.
    """

    def __init__(self, llm_client: LMStudioClient = None):
        self.llm_client = llm_client or LMStudioClient()

    def explain_transformations(self, translation_stats: dict) -> List[dict]:
        """
        Generate explanations for the translation/transliteration mappings.
        For efficiency, only explains a subset of transformations.
        """
        explanations = []

        for col, stats in translation_stats.items():
            mapping = stats.get("mapping", {})
            task = stats.get("task", "Unknown")

            # Only explain non-identity mappings (where input != output)
            changes = {k: v for k, v in mapping.items() if k != v}

            if not changes:
                continue

            # Take a sample of up to 10 changes
            sample_changes = dict(list(changes.items())[:10])

            for original, cleaned in sample_changes.items():
                explanations.append({
                    "column": col,
                    "task": task,
                    "original": original,
                    "cleaned": cleaned,
                    "explanation": self._generate_explanation(original, cleaned, task, col),
                })

        return explanations

    def _generate_explanation(
        self, original: str, cleaned: str, task: str, column: str
    ) -> str:
        """Generate a human-readable explanation for a single transformation."""
        # For simple cases, generate explanation without LLM
        if original.lower().strip() == cleaned.lower().strip():
            return f"Normalized casing from '{original}' to '{cleaned}'"

        if original.isascii() and cleaned.isascii():
            return f"Standardized '{original}' to canonical form '{cleaned}'"

        if "transliteration" in task.lower():
            return f"Phonetically transliterated '{original}' to Latin script as '{cleaned}'"

        if "translation" in task.lower():
            return f"Translated non-English value '{original}' to English equivalent '{cleaned}'"

        return f"Transformed '{original}' to '{cleaned}' during {task}"
