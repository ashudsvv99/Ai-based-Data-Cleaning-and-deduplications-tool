# `agents/llm_client.py` - The Universal AI Interface

If all 5 agents (Schema, Planner, Validation, etc.) had to write their own HTTP request logic to talk to LM Studio, the codebase would be bloated and fragile. `LMStudioClient` abstracts all AI communication into a single, highly-resilient utility class.

## Full Working Process & Logic

### 1. Dynamic Model Discovery
- **Problem**: Early versions of this script hardcoded `model="qwen2"`. If the user unloaded Qwen and loaded DeepSeek in LM Studio, every API call would crash with a `ModelNotFoundError`.
- **Solution**: The `__init__` method hits the `http://localhost:1234/v1/models` REST endpoint using `requests.get()`. 
- **Action**: It parses the JSON response, extracts the exact ID of the currently loaded model in RAM (`models["data"][0]["id"]`), and saves it to `self.model_id`. All future POST requests use this dynamic ID, ensuring 100% model-agnostic compatibility.

### 2. Exponential Backoff (Retry Loops)
- **Problem**: Local AI inference runs on the user's GPU. If the GPU gets overloaded, the API will time out or throw a 500 Server Error.
- **Solution**: The `chat_completion_json` method is wrapped in a `for attempt in range(max_retries):` loop.
- **Action**: If a `requests.exceptions.RequestException` occurs, it catches it, prints a warning, and executes `time.sleep(2 ** attempt)`. This means it waits 1 second, then 2 seconds, then 4 seconds. This "exponential backoff" gives the GPU time to clear its VRAM before trying again.

### 3. Strict JSON Enforcement
- **Logic**: We pass `response_format={"type": "json_object"}` in the API payload.
- **Why**: An LLM naturally wants to chat ("Here is your JSON..."). If it outputs conversational text, `json.loads()` will crash. By passing this flag, we trigger the LLM's "Grammar Constrained Decoding". The API physically prevents the LLM from outputting any token that violates JSON syntax.
- **Validation**: After receiving the response, the script runs a regex `re.sub(r'[\x00-\x1F\x7F-\x9F]', '', content)` to strip out invisible control characters that sometimes hallucinate, ensuring `json.loads(content)` executes perfectly.
