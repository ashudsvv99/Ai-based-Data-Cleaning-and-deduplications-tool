"""
Domain profiler: Two-pass domain detection.

Pass 1 — Fast keyword heuristic (no LLM, always runs).
Pass 2 — LLM verification: sends column names + sample values so the
          LLM can confirm, override, or detect domains the keyword list
          doesn't cover (e.g. Real Estate, Legal, Manufacturing, Logistics).

The heuristic result is shown to the LLM as a hint; the LLM can
accept it or replace it with something more precise.
"""
import json
import pandas as pd
from typing import Optional


# ──────────────────────────────────────────────
# Domains keyword dictionary (fast pre-filter)
# ──────────────────────────────────────────────
DOMAIN_KEYWORDS = {
    "Retail": [
        "customer", "order", "delivery", "sku", "product", "cart",
        "shipping", "retail", "payment", "priority", "invoice", "purchase",
        "checkout", "discount", "coupon", "fulfillment",
    ],
    "Finance": [
        "transaction", "account", "balance", "amount", "credit", "debit",
        "finance", "interest", "loan", "bank", "portfolio", "asset",
        "liability", "revenue", "profit", "ledger", "invoice",
    ],
    "Healthcare": [
        "patient", "diagnosis", "treatment", "mrn", "blood_pressure",
        "medical", "health", "prescription", "doctor", "hospital",
        "icd", "drug", "dosage", "clinical", "symptom", "vital",
    ],
    "Education": [
        "student", "course", "grade", "enrollment", "teacher",
        "class", "semester", "gpa", "degree", "curriculum",
        "marks", "attendance", "faculty", "subject",
    ],
    "HR": [
        "employee", "salary", "department", "hire_date", "designation",
        "leave", "performance", "payroll", "headcount", "appraisal",
        "onboarding", "attrition", "recruiter", "workforce",
    ],
    "Logistics": [
        "shipment", "tracking", "carrier", "warehouse", "dispatch",
        "freight", "route", "vehicle", "delivery_date", "manifest",
        "consignment", "origin", "destination",
    ],
    "Real Estate": [
        "property", "listing", "rent", "mortgage", "bedroom", "sqft",
        "location", "agent", "buyer", "seller", "lease", "valuation",
    ],
    "Manufacturing": [
        "batch", "production", "machine", "defect", "yield",
        "raw_material", "assembly", "shift", "downtime", "qc",
        "inspection", "plant", "unit_cost",
    ],
    "E-Commerce": [
        "seller", "marketplace", "rating", "review", "return",
        "refund", "wishlist", "category", "listing", "bid",
    ],
}


class DomainProfiler:
    """
    Two-pass domain detector.
    Pass 1: Fast keyword scoring (always runs, no LLM).
    Pass 2: LLM confirmation/override (runs when an llm_client is provided).
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    # ────────────────────────────────────────
    # Public entry point
    # ────────────────────────────────────────
    def detect_domain(
        self,
        df: pd.DataFrame,
        log_callback=None,
    ) -> dict:
        """
        Detect the dataset domain using heuristics + optional LLM verification.

        Returns a dict:
        {
            "domain":      "Retail",
            "confidence":  "High",
            "method":      "LLM-confirmed" | "Heuristic",
            "reasoning":   "...",
            "heuristic_scores": {...}
        }
        """
        log = log_callback or print

        # ── Pass 1: Keyword heuristic ──
        heuristic_result = self._keyword_score(df)
        log(f"  [Domain/Heuristic] Best match: {heuristic_result['domain']} "
            f"(score={heuristic_result['score']})")

        if self.llm_client is None:
            return {
                "domain": heuristic_result["domain"],
                "confidence": "Medium" if heuristic_result["score"] > 0 else "Low",
                "method": "Heuristic",
                "reasoning": f"Keyword match score: {heuristic_result['score']}",
                "heuristic_scores": heuristic_result["all_scores"],
            }

        # ── Pass 2: LLM verification ──
        try:
            llm_result = self._llm_detect(df, heuristic_result)
            log(f"  [Domain/LLM] Confirmed: {llm_result['domain']} "
                f"(confidence={llm_result['confidence']})")
            llm_result["heuristic_scores"] = heuristic_result["all_scores"]
            return llm_result
        except Exception as e:
            log(f"  [Domain/LLM] LLM detection failed ({e}), using heuristic.")
            return {
                "domain": heuristic_result["domain"],
                "confidence": "Medium",
                "method": "Heuristic (LLM failed)",
                "reasoning": str(e),
                "heuristic_scores": heuristic_result["all_scores"],
            }

    # ────────────────────────────────────────
    # Pass 1: keyword scoring
    # ────────────────────────────────────────
    def _keyword_score(self, df: pd.DataFrame) -> dict:
        cols = [str(c).lower().replace(" ", "_") for c in df.columns]
        scores = {domain: 0 for domain in DOMAIN_KEYWORDS}

        for col in cols:
            for domain, keywords in DOMAIN_KEYWORDS.items():
                if any(kw in col for kw in keywords):
                    scores[domain] += 1

        # Also scan sample values of string columns for domain clues
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]):
                sample_vals = df[col].dropna().astype(str).str.lower().head(20).tolist()
                for val in sample_vals:
                    for domain, keywords in DOMAIN_KEYWORDS.items():
                        if any(kw in val for kw in keywords):
                            scores[domain] += 0.5  # half weight for value matches

        best = max(scores, key=scores.get)
        return {
            "domain": best if scores[best] > 0 else "Generic",
            "score": round(scores[best], 1),
            "all_scores": {k: round(v, 1) for k, v in scores.items()},
        }

    # ────────────────────────────────────────
    # Pass 2: LLM verification
    # ────────────────────────────────────────
    def _llm_detect(self, df: pd.DataFrame, heuristic: dict) -> dict:
        """Ask the LLM to confirm or override the heuristic domain guess."""
        columns = list(df.columns)
        # Build a compact sample: 3 rows, string-only preview
        sample_rows = df.head(3).astype(str).to_dict(orient="records")

        known_domains = list(DOMAIN_KEYWORDS.keys()) + ["Generic", "Other"]

        system_prompt = (
            "You are an expert data analyst. "
            "Given dataset column names and sample values, identify the industry domain.\n\n"
            f"Known domains: {json.dumps(known_domains)}\n\n"
            "Return ONLY a JSON object with these exact keys:\n"
            '{"domain": "<domain>", "confidence": "High|Medium|Low", "reasoning": "<one sentence>"}\n\n'
            "EXAMPLE OUTPUT:\n"
            '{"domain": "Retail", "confidence": "High", "reasoning": "Columns like order_status and customer_type are typical of retail order management."}'
        )

        user_prompt = (
            f"Heuristic suggestion: {heuristic['domain']} (score={heuristic['score']})\n\n"
            f"Column names: {json.dumps(columns)}\n\n"
            f"Sample rows:\n{json.dumps(sample_rows, ensure_ascii=False, default=str)}\n\n"
            "OUTPUT JSON:"
        )

        raw = self.llm_client.chat_completion_json(
            system_prompt, user_prompt, num_expected_keys=3, enable_thinking=True
        )

        if isinstance(raw, dict) and "domain" in raw:
            return {
                "domain": str(raw.get("domain", heuristic["domain"])).strip(),
                "confidence": str(raw.get("confidence", "Medium")).strip(),
                "method": "LLM-confirmed",
                "reasoning": str(raw.get("reasoning", "LLM domain detection")).strip(),
            }

        # LLM returned empty or unexpected — fall back
        return {
            "domain": heuristic["domain"],
            "confidence": "Medium",
            "method": "Heuristic (LLM parse failed)",
            "reasoning": f"Raw LLM response: {str(raw)[:100]}",
        }
