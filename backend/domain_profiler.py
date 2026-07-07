"""
Domain & Intent Profiler — Two-pass detection.

Pass 1 — Fast keyword heuristic (no LLM, always runs).
Pass 2 — LLM verification: sends column names + sample values so the
          LLM can confirm, override, or detect domains the keyword list
          doesn't cover (e.g. Real Estate, Legal, Manufacturing, Logistics).

DATASET INTENT:
  Every dataset is classified into ONE of two intents:
    "Predictive"              — ML, statistical analysis, forecasting, BI
    "Non-Predictive Business" — CRM, ERP, HR, transactional records

  The intent drives:
    - Imputation strategy    (statistical vs preserve-as-null)
    - Outlier handling       (clip vs skip for business metrics)
    - Deduplication mode     (lightweight vs full 16-rule business logic)
    - Target variable detection (for Predictive datasets)
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

# ──────────────────────────────────────────────
# Predictive intent keyword hints (heuristic only)
# ──────────────────────────────────────────────
_PREDICTIVE_HINTS = [
    "churn", "label", "target", "class", "prediction", "outcome",
    "fraud", "default", "survival", "prognosis", "risk_score",
    "propensity", "conversion", "response", "will_", "_flag",
    "is_", "has_", "y_train", "y_test", "forecast", "demand",
]


class DomainProfiler:
    """
    Two-pass domain & intent detector.

    Pass 1: Fast keyword scoring (always runs, no LLM).
    Pass 2: LLM confirmation/override (runs when llm_client is provided).

    Returns a dict with keys:
        domain, intent, confidence, method, reasoning,
        target_variables, is_time_series, heuristic_scores
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
        Returns:
        {
            "domain":           "Retail",
            "intent":           "Non-Predictive Business",
            "confidence":       "High",
            "method":           "LLM-confirmed" | "Heuristic",
            "reasoning":        "...",
            "target_variables": [],
            "is_time_series":   False,
            "heuristic_scores": {...}
        }
        """
        log = log_callback or print

        # ── Pass 1: Keyword heuristic ──
        heuristic_result = self._keyword_score(df)
        heuristic_intent = self._heuristic_intent(df)
        log(f"  [Domain/Heuristic] Best match: {heuristic_result['domain']} "
            f"(score={heuristic_result['score']}) | Intent: {heuristic_intent}")

        if self.llm_client is None:
            return {
                "domain":           heuristic_result["domain"],
                "intent":           heuristic_intent,
                "confidence":       "Medium" if heuristic_result["score"] > 0 else "Low",
                "method":           "Heuristic",
                "reasoning":        f"Keyword match score: {heuristic_result['score']}",
                "target_variables": [],
                "is_time_series":   self._heuristic_time_series(df),
                "heuristic_scores": heuristic_result["all_scores"],
            }

        # ── Pass 2: LLM verification ──
        try:
            llm_result = self._llm_detect(df, heuristic_result, heuristic_intent)
            log(f"  [Domain/LLM] Domain: {llm_result['domain']} | Intent: {llm_result['intent']} "
                f"(confidence={llm_result['confidence']})")
            if llm_result.get("reasoning"):
                log(f"  [Domain/LLM] Reason: {llm_result['reasoning']}")
            llm_result["heuristic_scores"] = heuristic_result["all_scores"]
            return llm_result
        except Exception as e:
            log(f"  [Domain/LLM] LLM detection failed ({e}), using heuristic.")
            return {
                "domain":           heuristic_result["domain"],
                "intent":           heuristic_intent,
                "confidence":       "Medium",
                "method":           "Heuristic (LLM failed)",
                "reasoning":        str(e),
                "target_variables": [],
                "is_time_series":   self._heuristic_time_series(df),
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

        # Scan sample values of string columns
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]):
                sample_vals = df[col].dropna().astype(str).str.lower().head(20).tolist()
                for val in sample_vals:
                    for domain, keywords in DOMAIN_KEYWORDS.items():
                        if any(kw in val for kw in keywords):
                            scores[domain] += 0.5

        best = max(scores, key=scores.get)
        return {
            "domain": best if scores[best] > 0 else "Generic",
            "score":  round(scores[best], 1),
            "all_scores": {k: round(v, 1) for k, v in scores.items()},
        }

    def _heuristic_intent(self, df: pd.DataFrame) -> str:
        """Quick heuristic: look for target-like column names."""
        cols_lower = [str(c).lower() for c in df.columns]
        if any(hint in col for col in cols_lower for hint in _PREDICTIVE_HINTS):
            return "Predictive"
        # If mostly numeric features with no contact-like columns → probably Predictive
        numeric_ratio = df.select_dtypes(include="number").shape[1] / max(len(df.columns), 1)
        contact_cols  = sum(1 for c in cols_lower if any(k in c for k in ["email", "phone", "mobile", "name"]))
        if numeric_ratio > 0.7 and contact_cols == 0:
            return "Predictive"
        return "Non-Predictive Business"

    def _heuristic_time_series(self, df: pd.DataFrame) -> bool:
        """Simple check for date-like columns."""
        cols_lower = [str(c).lower() for c in df.columns]
        return any(k in c for c in cols_lower for k in ["date", "time", "timestamp", "period", "month", "year", "quarter"])

    # ────────────────────────────────────────
    # Pass 2: LLM verification
    # ────────────────────────────────────────
    def _llm_detect(self, df: pd.DataFrame, heuristic: dict, heuristic_intent: str) -> dict:
        """Ask the LLM to confirm domain AND dataset intent, plus identify target variables."""
        columns     = list(df.columns)
        sample_rows = df.head(3).astype(str).to_dict(orient="records")
        col_dtypes  = {str(c): str(df[c].dtype) for c in df.columns}

        known_domains = list(DOMAIN_KEYWORDS.keys()) + ["Generic", "Other"]

        system_prompt = (
            "You are an expert data scientist and data analyst.\n"
            "Given dataset column names, data types, and sample rows, you must determine:\n"
            "  1. The industry DOMAIN (e.g. Retail, Finance, Healthcare, HR, CRM, Logistics, etc.)\n"
            "  2. The DATASET INTENT — EXACTLY one of:\n"
            "       \"Predictive\"              (used for ML, forecasting, analytics, classification)\n"
            "       \"Non-Predictive Business\" (CRM, ERP, HR records, customer databases, transactional logs)\n"
            "  3. TARGET VARIABLES — columns that are prediction targets (empty list if Non-Predictive)\n"
            "  4. IS_TIME_SERIES — true if the dataset has a temporal ordering column\n\n"
            "Return ONLY a JSON object with these exact keys:\n"
            '{\n'
            '  "domain": "<domain>",\n'
            '  "intent": "Predictive" | "Non-Predictive Business",\n'
            '  "confidence": "High" | "Medium" | "Low",\n'
            '  "reasoning": "<one sentence>",\n'
            '  "target_variables": ["<col1>"],\n'
            '  "is_time_series": true | false\n'
            '}\n\n'
            "RULES:\n"
            "- If columns include contact info (email, phone, name, address) → likely Non-Predictive Business\n"
            "- If a column name looks like a prediction label (churn, fraud, default, label, target, class, y) → Predictive\n"
            "- Mostly numeric feature columns with no contact info → likely Predictive\n"
            f"Known domains: {json.dumps(known_domains)}"
        )

        user_prompt = (
            f"Heuristic domain: {heuristic['domain']} (score={heuristic['score']})\n"
            f"Heuristic intent: {heuristic_intent}\n\n"
            f"Column names: {json.dumps(columns)}\n"
            f"Column dtypes: {json.dumps(col_dtypes)}\n\n"
            f"Sample rows:\n{json.dumps(sample_rows, ensure_ascii=False, default=str)}\n\n"
            "OUTPUT JSON:"
        )

        raw = self.llm_client.chat_completion_json(
            system_prompt, user_prompt, num_expected_keys=6, enable_thinking=True
        )

        if isinstance(raw, dict) and "domain" in raw:
            intent = str(raw.get("intent", heuristic_intent)).strip()
            # Normalise intent string
            if "predictive" in intent.lower() and "non" not in intent.lower():
                intent = "Predictive"
            else:
                intent = "Non-Predictive Business"

            target_vars = raw.get("target_variables", [])
            if not isinstance(target_vars, list):
                target_vars = []

            return {
                "domain":           str(raw.get("domain", heuristic["domain"])).strip(),
                "intent":           intent,
                "confidence":       str(raw.get("confidence", "Medium")).strip(),
                "method":           "LLM-confirmed",
                "reasoning":        str(raw.get("reasoning", "LLM domain & intent detection")).strip(),
                "target_variables": [str(v) for v in target_vars if v in list(df.columns)],
                "is_time_series":   bool(raw.get("is_time_series", False)),
            }

        # LLM parse failed — fall back
        return {
            "domain":           heuristic["domain"],
            "intent":           heuristic_intent,
            "confidence":       "Medium",
            "method":           "Heuristic (LLM parse failed)",
            "reasoning":        f"Raw LLM response: {str(raw)[:100]}",
            "target_variables": [],
            "is_time_series":   self._heuristic_time_series(df),
        }
