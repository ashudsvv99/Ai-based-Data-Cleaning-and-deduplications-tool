"""
Enhanced LLM client for LM Studio with retry logic, dynamic token sizing,
and guaranteed JSON extraction.
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
    - Robust JSON extraction from LLM responses
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
            pass # Silently fallback to default
            
        return self.model or "local-model"

    def _estimate_max_tokens(self, num_items: int, user_prompt: str = "") -> int:
        """Dynamically set max_tokens based on expected output size and input prompt length."""
        # 1 token ≈ 4 characters. We auto-adjust based on the input text size and dataset chunk size.
        input_tokens_estimate = len(user_prompt) // 4
        
        # Each output JSON key-value pair is roughly 30-50 tokens, but we allocate generous headroom (100)
        # plus half the input size for reasoning steps.
        estimated = max(config.LLM_MAX_TOKENS_DEFAULT, (num_items * 100) + (input_tokens_estimate // 2))
        
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
            system_prompt += "\n\nIMPORTANT: You must think step-by-step before answering. Wrap your detailed thoughts in <think>...</think> tags."
        else:
            system_prompt += "\n\nIMPORTANT: Output your final response directly. Do NOT use <think> tags or reasoning blocks. Be fast and direct."

        payload = {
            "model": self._get_active_model(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
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
        Send a request and guarantee a parsed JSON dict response.
        Uses dynamic token sizing and robust JSON extraction.
        """
        max_tokens = self._estimate_max_tokens(num_expected_keys, user_prompt)
        raw = self.chat_completion(system_prompt, user_prompt, temperature, max_tokens, enable_thinking=enable_thinking)
        return self.extract_json(raw)

    @staticmethod
    def extract_json(raw_response: str) -> dict:
        """
        Robustly extract a JSON object from an LLM response that may
        contain markdown code fences, conversational text, or other noise.
        """
        if not raw_response or raw_response.strip() == "{}":
            return {}

        text = raw_response.strip()

        # Try 1: Extract JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try 1b: Extract JSON array from markdown code block
        arr_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, re.DOTALL)
        if arr_match:
            try:
                result = json.loads(arr_match.group(1))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # Try 2: Direct JSON parse
        try:
            result = json.loads(text)
            if isinstance(result, (dict, list)):
                return result
        except json.JSONDecodeError:
            pass

        # Try 3: Find the first { ... } or [ ... ] in the text
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            start_idx = text.find(start_char)
            if start_idx == -1:
                continue
            # Find matching closing bracket
            depth = 0
            for i in range(start_idx, len(text)):
                if text[i] == start_char:
                    depth += 1
                elif text[i] == end_char:
                    depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start_idx:i + 1])
                    except json.JSONDecodeError:
                        break

        return {}

    @staticmethod
    def clean_reasoning_tags(content: str) -> str:
        """Strip reasoning thoughts (e.g. <think>...</think>) from local LLM responses."""
        if not content:
            return ""
        # 1. Remove closed think/thought blocks
        content = re.sub(r'<(think|thought)>.*?</\1>', '', content, flags=re.DOTALL | re.IGNORECASE).strip()
        # 2. If there's an unclosed <think> or <thought> tag left, strip it and everything after it
        content = re.sub(r'<(think|thought)>.*', '', content, flags=re.DOTALL | re.IGNORECASE).strip()
        return content
