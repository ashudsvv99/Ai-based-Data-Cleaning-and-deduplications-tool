"""
Enhanced LLM client for LM Studio with retry logic, dynamic token sizing,
and robust JSON extraction + repair.

JSON Extraction Strategy (7-pass):
  1. Strip <think>/<thought> reasoning blocks
  2. Normalize unicode quotes and whitespace
  3. Extract from markdown code fences (```json, ```JSON, ```javascript, etc.)
  4. Try direct parse of the entire response
  5. Find the largest { } or [ ] block in the text
  6. Attempt JSON repair (trailing commas, unclosed brackets, bad escapes)
  7. If all fail, return {} and log the raw response for debugging
"""
import os
import re
import json
import time
import requests
import config


class LMStudioClient:
    """
    Connects to a local LM Studio instance.
    Features:
    - Dynamic max_tokens based on input size
    - Retry with exponential backoff
    - Robust JSON extraction + repair from LLM responses
    - Key-count validation with auto-retry on mismatch
    """

    def __init__(self, base_url=None, model=None):
        self.base_url = base_url or config.LLM_BASE_URL
        self.model = model or config.LLM_MODEL_NAME
        self.max_retries = config.LLM_MAX_RETRIES
        self.retry_delay = config.LLM_RETRY_DELAY_SECONDS
        self.timeout = config.LLM_TIMEOUT_SECONDS
        self._cached_active_model = None

    def _get_active_model(self) -> str:
        """Dynamically fetch the currently loaded model from LM Studio."""
        if self._cached_active_model:
            return self._cached_active_model

        if self.model and self.model != "local-model":
            return self.model

        try:
            url = f"{self.base_url}/models"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    self._cached_active_model = data["data"][0]["id"]
                    return self._cached_active_model
        except Exception:
            pass  # Silently fallback to default

        return self.model or "local-model"

    def _estimate_max_tokens(self, num_items: int, user_prompt: str = "") -> int:
        """Dynamically set max_tokens based on expected output size and input prompt length."""
        # 1 token ≈ 4 characters. Auto-adjust based on input text size and dataset chunk size.
        input_tokens_estimate = len(user_prompt) // 4
        # Each output JSON key-value pair is roughly 30-50 tokens; allocate generous headroom (120)
        # plus half the input size for reasoning steps.
        estimated = max(config.LLM_MAX_TOKENS_DEFAULT, (num_items * 120) + (input_tokens_estimate // 2))
        return min(estimated, config.LLM_MAX_TOKENS_CEILING)

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = None,
        max_tokens: int = None,
        enable_thinking: bool = False,
    ) -> str:
        """
        Send a chat completion request with retry logic.
        Dynamically instructs reasoning models to think (or not).
        Returns the raw text response from the LLM.
        """
        temperature = temperature if temperature is not None else config.LLM_TEMPERATURE
        max_tokens = max_tokens or config.LLM_MAX_TOKENS_DEFAULT
        url = f"{self.base_url}/chat/completions"

        if enable_thinking:
            system_prompt += (
                "\n\nIMPORTANT: Think step-by-step before answering. "
                "Wrap your reasoning in <think>...</think> tags, then output ONLY valid JSON."
            )
        else:
            system_prompt += (
                "\n\nIMPORTANT: Output ONLY valid JSON. "
                "No markdown fences, no explanations, no <think> tags. JSON only."
            )

        payload = {
            "model": self._get_active_model(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                return self.clean_reasoning_tags(content)

            except requests.exceptions.ConnectionError:
                raise ConnectionError(
                    f"Could not connect to LM Studio at {self.base_url}. "
                    "Ensure LM Studio is running and the Local Server is started."
                )
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait = self.retry_delay * (2 ** (attempt - 1))
                    print(f"    [LLM] Attempt {attempt} failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"    [LLM] All {self.max_retries} attempts failed. Last error: {e}")

        return "{}"

    def chat_completion_json(
        self,
        system_prompt: str,
        user_prompt: str,
        num_expected_keys: int = 10,
        temperature: float = None,
        enable_thinking: bool = False,
    ) -> dict:
        """
        Send a request and guarantee a parsed JSON dict/list response.
        Uses dynamic token sizing, robust JSON extraction + repair, and
        key-count validation with one automatic retry on mismatch.
        """
        max_tokens = self._estimate_max_tokens(num_expected_keys, user_prompt)
        raw = self.chat_completion(
            system_prompt, user_prompt, temperature, max_tokens,
            enable_thinking=enable_thinking,
        )
        result = self.extract_json(raw)

        # Key-count validation: if we got far fewer keys than expected, retry once
        # with a stricter "JSON only" prompt to coax a better response.
        if (
            num_expected_keys > 1
            and isinstance(result, dict)
            and len(result) < max(1, num_expected_keys // 3)
        ):
            print(
                f"    [LLM] JSON result has {len(result)} keys, expected ~{num_expected_keys}. "
                "Retrying with stricter JSON-only prompt..."
            )
            retry_system = (
                system_prompt
                + "\n\nCRITICAL: Your previous response was incomplete. "
                "Output ONLY a valid JSON object with ALL required keys. "
                "Do not truncate. Do not add any text outside the JSON."
            )
            raw2 = self.chat_completion(
                retry_system, user_prompt, temperature, max_tokens,
                enable_thinking=False,
            )
            result2 = self.extract_json(raw2)
            # Take whichever result has more keys
            if isinstance(result2, dict) and len(result2) > len(result):
                result = result2
            elif isinstance(result2, list) and len(result2) > 0:
                result = result2

        return result

    # ──────────────────────────────────────────────
    # JSON extraction + repair pipeline
    # ──────────────────────────────────────────────

    @staticmethod
    def extract_json(raw_response: str):
        """
        Robustly extract a JSON object or array from an LLM response.

        7-pass extraction with repair:
          Pass 1: Strip reasoning tags
          Pass 2: Normalize unicode quotes & whitespace
          Pass 3: Extract from markdown code fences
          Pass 4: Direct parse of full text
          Pass 5: Find largest { } or [ ] block
          Pass 6: Repair + reparse (trailing commas, unclosed brackets)
          Pass 7: Extract any partial key-value pairs as a best-effort dict
        """
        if not raw_response:
            return {}

        text = raw_response.strip()

        # ── Pass 1: Strip reasoning tags ──
        text = LMStudioClient.clean_reasoning_tags(text)
        if not text:
            return {}

        # ── Pass 2: Normalize unicode quotes ──
        text = LMStudioClient._normalize_quotes(text)

        # ── Pass 3: Extract from markdown code fences ──
        fence_result = LMStudioClient._extract_from_fence(text)
        if fence_result is not None:
            return fence_result

        # ── Pass 4: Direct parse ──
        direct = LMStudioClient._try_parse(text)
        if direct is not None:
            return direct

        # ── Pass 5: Find largest JSON block ──
        block_result = LMStudioClient._extract_largest_block(text)
        if block_result is not None:
            return block_result

        # ── Pass 6: Repair + reparse ──
        repaired = LMStudioClient._repair_json(text)
        if repaired:
            fixed = LMStudioClient._try_parse(repaired)
            if fixed is not None:
                return fixed

        # ── Pass 7: Best-effort key-value extraction ──
        partial = LMStudioClient._extract_partial_kv(text)
        if partial:
            print(f"    [LLM/JSON] Warning: used partial extraction ({len(partial)} keys recovered).")
            return partial

        print(f"    [LLM/JSON] Warning: all extraction passes failed. Raw snippet: {text[:200]!r}")
        return {}

    @staticmethod
    def _normalize_quotes(text: str) -> str:
        """Replace unicode curly quotes, backticks, and other quote variants with standard ASCII."""
        # Unicode left/right double quotes → "
        text = text.replace('\u201c', '"').replace('\u201d', '"')
        # Unicode left/right single quotes → '
        text = text.replace('\u2018', "'").replace('\u2019', "'")
        # Backtick-quoted strings (not code fences) → "
        # Only replace standalone backticks used as quote marks, not ``` fences
        text = re.sub(r'(?<!`)`(?!`)', '"', text)
        # Non-breaking spaces → regular spaces
        text = text.replace('\u00a0', ' ')
        return text

    @staticmethod
    def _extract_from_fence(text: str):
        """
        Extract JSON from markdown code fences.
        Handles: ```json, ```JSON, ```javascript, ```js, ``` (no lang), and
        multiple fences (picks the largest valid one).
        """
        # Match any code fence with optional language tag
        fence_pattern = re.compile(
            r'```(?:json|JSON|javascript|js|python|py|text|)?\s*\n?(.*?)\n?\s*```',
            re.DOTALL | re.IGNORECASE,
        )
        candidates = []
        for match in fence_pattern.finditer(text):
            content = match.group(1).strip()
            parsed = LMStudioClient._try_parse(content)
            if parsed is not None:
                candidates.append((len(content), parsed))
            else:
                # Try repairing the fenced content
                repaired = LMStudioClient._repair_json(content)
                if repaired:
                    parsed = LMStudioClient._try_parse(repaired)
                    if parsed is not None:
                        candidates.append((len(content), parsed))

        if candidates:
            # Return the result from the largest fence block
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
        return None

    @staticmethod
    def _try_parse(text: str):
        """Attempt json.loads(); return None on failure."""
        if not text or not text.strip():
            return None
        try:
            result = json.loads(text.strip())
            if isinstance(result, (dict, list)):
                return result
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    @staticmethod
    def _extract_largest_block(text: str):
        """
        Find all { } and [ ] blocks in the text and return the largest
        successfully-parsed one.
        """
        candidates = []
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            for start_idx in range(len(text)):
                if text[start_idx] != start_char:
                    continue
                depth = 0
                in_string = False
                escape_next = False
                for i in range(start_idx, len(text)):
                    ch = text[i]
                    if escape_next:
                        escape_next = False
                        continue
                    if ch == '\\' and in_string:
                        escape_next = True
                        continue
                    if ch == '"' and not escape_next:
                        in_string = not in_string
                    if not in_string:
                        if ch == start_char:
                            depth += 1
                        elif ch == end_char:
                            depth -= 1
                        if depth == 0:
                            candidate_text = text[start_idx:i + 1]
                            parsed = LMStudioClient._try_parse(candidate_text)
                            if parsed is not None:
                                candidates.append((len(candidate_text), parsed))
                            else:
                                # Try repair on this block
                                repaired = LMStudioClient._repair_json(candidate_text)
                                if repaired:
                                    parsed = LMStudioClient._try_parse(repaired)
                                    if parsed is not None:
                                        candidates.append((len(candidate_text), parsed))
                            break

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
        return None

    @staticmethod
    def _repair_json(text: str) -> str:
        """
        Attempt to repair common JSON errors produced by LLMs:

        1. Remove trailing commas before } or ] (LLMs add these constantly)
        2. Close unclosed string literals
        3. Add missing closing brackets/braces for truncated JSON
        4. Remove non-JSON prefix/suffix text
        5. Fix unquoted keys
        """
        if not text:
            return ""

        # Step 1: Isolate JSON — find the first { or [
        start = -1
        for i, ch in enumerate(text):
            if ch in ('{', '['):
                start = i
                break
        if start == -1:
            return ""
        text = text[start:]

        # Step 2: Remove trailing commas before } or ]
        # Pattern: comma followed by optional whitespace then } or ]
        text = re.sub(r',\s*([}\]])', r'\1', text)

        # Step 3: Remove JavaScript-style comments
        text = re.sub(r'//[^\n]*', '', text)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

        # Step 4: Fix unquoted keys (word: → "word":)
        # Only apply where key is clearly unquoted alphanumeric
        text = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', text)

        # Step 5: Close unclosed string at end (truncated)
        # Count quotes — if odd number of unescaped quotes, the last string is open
        def _count_unescaped_quotes(s):
            count = 0
            i = 0
            while i < len(s):
                if s[i] == '\\':
                    i += 2
                    continue
                if s[i] == '"':
                    count += 1
                i += 1
            return count

        quote_count = _count_unescaped_quotes(text)
        if quote_count % 2 == 1:
            text = text + '"'  # Close the open string

        # Step 6: Close unclosed brackets/braces (truncated JSON)
        open_chars = []
        in_string = False
        escape_next = False
        for ch in text:
            if escape_next:
                escape_next = False
                continue
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
            if not in_string:
                if ch == '{':
                    open_chars.append('}')
                elif ch == '[':
                    open_chars.append(']')
                elif ch in ('}', ']') and open_chars:
                    open_chars.pop()

        # Append missing closing chars in reverse order
        for closing in reversed(open_chars):
            text = text + closing

        return text

    @staticmethod
    def _extract_partial_kv(text: str) -> dict:
        """
        Best-effort extraction of key-value pairs from malformed JSON.
        Looks for patterns like: "key": "value" or "key": number
        Used as a last resort when all other methods fail.
        """
        result = {}
        # Match "key": "value" or "key": number or "key": true/false/null
        pattern = re.compile(
            r'"([^"]+)"\s*:\s*(?:"([^"]*?)"|(\d+\.?\d*)|(\btrue\b|\bfalse\b|\bnull\b))',
            re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            key = match.group(1)
            if match.group(2) is not None:
                result[key] = match.group(2)
            elif match.group(3) is not None:
                val = match.group(3)
                result[key] = float(val) if '.' in val else int(val)
            elif match.group(4) is not None:
                v = match.group(4).lower()
                result[key] = True if v == 'true' else (False if v == 'false' else None)
        return result

    # ──────────────────────────────────────────────
    # Reasoning tag cleaner
    # ──────────────────────────────────────────────

    @staticmethod
    def clean_reasoning_tags(content: str) -> str:
        """Strip reasoning thoughts (e.g. <think>...</think>) from local LLM responses."""
        if not content:
            return ""
        # Remove closed think/thought blocks
        content = re.sub(
            r'<(think|thought|reasoning|scratchpad)>.*?</\1>',
            '', content, flags=re.DOTALL | re.IGNORECASE,
        ).strip()
        # If there's an unclosed <think> or <thought> tag left, strip it and everything after
        content = re.sub(
            r'<(think|thought|reasoning|scratchpad)>.*',
            '', content, flags=re.DOTALL | re.IGNORECASE,
        ).strip()
        return content
