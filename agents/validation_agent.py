"""
LLM-based validation agent: spot-checks cleaned data quality by sending
a sample of rows to the LLM for review.
"""
import os
import json
import pandas as pd
from agents.llm_client import LMStudioClient


class ValidationAgent:
    """
    Post-cleaning spot-check: sends a small sample of cleaned rows to
    the LLM and asks it to evaluate the quality.
    """

    def __init__(self, llm_client: LMStudioClient = None):
        self.llm_client = llm_client or LMStudioClient()

    def spot_check(self, df: pd.DataFrame, num_samples: int = 5, log_callback=print) -> dict:
        """
        Send a random sample of rows to the LLM for quality review.
        Returns a confidence score and list of issues.
        """
        sample = df.sample(min(num_samples, len(df))).to_dict(orient="records")

        # Load prompt template
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "validation.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = (
                "Review these cleaned data rows. Return JSON with "
                "overall_confidence (0-100), issues (array), and summary (string)."
            )

        user_prompt = f"Cleaned data sample:\n{json.dumps(sample, ensure_ascii=False, default=str)}"

        log_callback("ValidationAgent: Spot-checking cleaned data quality with LLM...")
        result = self.llm_client.chat_completion_json(
            system_prompt, user_prompt, num_expected_keys=3, enable_thinking=True
        )

        if isinstance(result, dict):
            return {
                "llm_confidence": result.get("overall_confidence", 0),
                "llm_issues": result.get("issues", []),
                "llm_summary": result.get("summary", "No summary"),
            }
        return {"llm_confidence": 0, "llm_issues": ["LLM validation failed"], "llm_summary": "Validation unavailable"}
