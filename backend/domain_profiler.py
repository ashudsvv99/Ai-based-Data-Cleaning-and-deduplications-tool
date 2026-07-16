"""
Domain & Intent Profiler — LLM-First Detection.

Architecture (two-pass, LLM-primary):
  Pass 1 — Keyword heuristic (fast, always runs, no LLM).
            Produces a score-ranked list of candidate domains.
            This score is sent as a HINT to the LLM, not used as the final answer.
  Pass 2 — LLM is the PRIMARY decision maker.
            It receives: column names, dtypes, sample values, value distributions,
            missing%, unique counts, non-ASCII ratio, detected scripts, and the
            heuristic scores as context — then makes a holistic judgment.
            If LLM is offline or fails → heuristic result is used as fallback.

DATASET INTENT:
  Every dataset is classified into ONE of two intents:
    "Predictive"              — ML training, statistical analysis, forecasting, BI
    "Non-Predictive Business" — CRM, ERP, HR, transactional records, master data

  SUB-INTENT (additional granularity):
    "Master Data"    — Customer/product/employee master records (CRM, HR)
    "Transactional"  — Orders, payments, events (Retail, Finance)
    "Analytical"     — Pre-processed features for ML/BI
    "Operational"    — IoT sensors, logistics tracking, real-time data

  The intent drives:
    - Imputation strategy    (statistical vs preserve-as-null)
    - Outlier handling       (clip vs skip for business metrics)
    - Deduplication mode     (lightweight vs full 16-rule business logic)
    - Target variable detection (for Predictive datasets)
"""
import json
import re
import pandas as pd
import numpy as np
from typing import Optional


# ──────────────────────────────────────────────
# Extended domain keyword dictionary (hint only)
# ──────────────────────────────────────────────
DOMAIN_KEYWORDS = {
    "Retail": [
        "customer", "order", "delivery", "sku", "product", "cart",
        "shipping", "retail", "payment", "priority", "invoice", "purchase",
        "checkout", "discount", "coupon", "fulfillment", "pos",
    ],
    "Finance": [
        "transaction", "account", "balance", "amount", "credit", "debit",
        "finance", "interest", "loan", "bank", "portfolio", "asset",
        "liability", "revenue", "profit", "ledger", "invoice", "currency",
        "exchange_rate", "settlement", "clearing",
    ],
    "Healthcare": [
        "patient", "diagnosis", "treatment", "mrn", "blood_pressure",
        "medical", "health", "prescription", "doctor", "hospital",
        "icd", "drug", "dosage", "clinical", "symptom", "vital",
        "bmi", "pulse", "temperature", "glucose", "cholesterol",
        "ehr", "emr", "lab_result", "pathology",
    ],
    "Education": [
        "student", "course", "grade", "enrollment", "teacher",
        "class", "semester", "gpa", "degree", "curriculum",
        "marks", "attendance", "faculty", "subject", "exam",
        "school", "university", "college", "lecture",
    ],
    "HR": [
        "employee", "salary", "department", "hire_date", "designation",
        "leave", "performance", "payroll", "headcount", "appraisal",
        "onboarding", "attrition", "recruiter", "workforce", "job_title",
        "tenure", "bonus", "manager", "band", "level",
    ],
    "Logistics": [
        "shipment", "tracking", "carrier", "warehouse", "dispatch",
        "freight", "route", "vehicle", "delivery_date", "manifest",
        "consignment", "origin", "destination", "pod", "eta",
        "last_mile", "3pl", "fulfillment_center",
    ],
    "Real Estate": [
        "property", "listing", "rent", "mortgage", "bedroom", "sqft",
        "location", "agent", "buyer", "seller", "lease", "valuation",
        "floor", "bhk", "amenities", "colony", "plot",
    ],
    "Manufacturing": [
        "batch", "production", "machine", "defect", "yield",
        "raw_material", "assembly", "shift", "downtime", "qc",
        "inspection", "plant", "unit_cost", "sku", "wip",
        "bom", "mrp", "cycle_time",
    ],
    "E-Commerce": [
        "seller", "marketplace", "rating", "review", "return",
        "refund", "wishlist", "category", "listing", "bid",
        "cart_value", "gmv", "ctr", "conversion", "add_to_cart",
        "abandoned", "flash_sale",
    ],
    "CRM": [
        "lead", "opportunity", "pipeline", "contact", "deal",
        "crm", "prospect", "sales_rep", "account_manager", "follow_up",
        "stage", "funnel", "win_rate", "churn_risk", "ltv",
        "nps", "csat", "renewal", "upsell", "cross_sell",
    ],
    "Insurance": [
        "policy", "premium", "claim", "coverage", "beneficiary",
        "underwriting", "risk_score", "insurer", "insured",
        "deductible", "actuarial", "reinsurance", "rider",
        "lob", "endorsement",
    ],
    "Pharma": [
        "drug", "molecule", "clinical_trial", "fda", "approval",
        "dosage_form", "indication", "contraindication", "adr",
        "pharmacokinetic", "compound", "api", "excipient",
        "formulation", "batch_number", "expiry",
    ],
    "Supply Chain": [
        "supplier", "vendor", "procurement", "purchase_order",
        "rfq", "inventory", "stock", "reorder_point", "lead_time",
        "sourcing", "bom", "demand_forecast", "safety_stock",
    ],
    "IoT": [
        "sensor", "device_id", "timestamp", "reading", "telemetry",
        "iot", "gateway", "firmware", "signal", "threshold",
        "alert", "anomaly", "stream", "mqtt", "event_log",
    ],
    "Legal": [
        "case", "contract", "clause", "jurisdiction", "party",
        "litigation", "counsel", "verdict", "statute", "compliance",
        "regulation", "audit", "penalty", "dispute",
    ],
    "Agriculture": [
        "crop", "harvest", "irrigation", "fertilizer", "pesticide",
        "farm", "soil", "yield", "livestock", "acreage",
        "sowing", "rainfall", "mandi", "produce", "commodity",
    ],
    "Sports": [
        "player", "team", "match", "score", "goal", "wicket",
        "season", "league", "tournament", "fixture", "innings",
        "athlete", "coach", "stadium", "referee", "ranking",
    ],
    "Telecommunications": [
        "subscriber", "sim", "recharge", "data_usage", "call",
        "network", "bandwidth", "plan", "roaming", "tariff",
        "tower", "signal_strength", "imei", "operator", "postpaid",
    ],
    "Government": [
        "citizen", "aadhar", "pan", "voter", "ward", "district",
        "scheme", "beneficiary", "ministry", "department_code",
        "census", "election", "constituency", "municipality",
    ],
    "Environmental": [
        "emission", "pollution", "carbon", "co2", "temperature",
        "rainfall", "air_quality", "pm2_5", "water_quality",
        "species", "biodiversity", "deforestation", "climate",
    ],
    "Cybersecurity": [
        "ip_address", "vulnerability", "exploit", "malware", "firewall",
        "intrusion", "cve", "threat", "patch", "incident",
        "log", "access_control", "breach", "phishing", "endpoint",
    ],
    "Research": [
        "experiment", "hypothesis", "sample", "control", "variable",
        "observation", "measurement", "trial", "dataset", "study",
        "survey", "respondent", "questionnaire", "findings",
    ],
}

# ──────────────────────────────────────────────
# Predictive intent keyword hints (heuristic)
# ──────────────────────────────────────────────
_PREDICTIVE_HINTS = [
    "churn", "label", "target", "class", "prediction", "outcome",
    "fraud", "default", "survival", "prognosis", "risk_score",
    "propensity", "conversion", "response", "will_", "_flag",
    "is_", "has_", "y_train", "y_test", "forecast", "demand",
    "predict", "score", "probability", "feature", "embedding",
    "x_train", "x_test", "train_", "test_", "val_",
]

# Sub-intent classification per domain
_DOMAIN_SUB_INTENT = {
    "Retail":            "Transactional",
    "Finance":           "Transactional",
    "Healthcare":        "Master Data",
    "Education":         "Master Data",
    "HR":                "Master Data",
    "Logistics":         "Operational",
    "Real Estate":       "Master Data",
    "Manufacturing":     "Operational",
    "E-Commerce":        "Transactional",
    "CRM":               "Master Data",
    "Insurance":         "Master Data",
    "Pharma":            "Analytical",
    "Supply Chain":      "Operational",
    "IoT":               "Operational",
    "Legal":             "Master Data",
    "Agriculture":       "Operational",
    "Sports":            "Analytical",
    "Telecommunications":"Transactional",
    "Government":        "Master Data",
    "Environmental":     "Analytical",
    "Cybersecurity":     "Operational",
    "Research":          "Analytical",
    "Generic":           "Master Data",
}


class DomainProfiler:
    """
    LLM-first domain & intent detector.

    Pass 1: Fast keyword scoring (always runs, no LLM) → produces a ranked
            list of candidate domains used as a HINT for the LLM.
    Pass 2: LLM is the PRIMARY decision maker — it receives full dataset
            context (columns, dtypes, distributions, samples, scripts) and
            makes a holistic judgment.  Falls back to heuristic if LLM fails.

    Returns a dict with keys:
        domain, intent, sub_intent, confidence, method, reasoning,
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
        Returns a domain detection result dict.
        """
        log = log_callback or print

        # ── Pass 1: Keyword heuristic ──
        heuristic_result = self._keyword_score(df)
        heuristic_intent = self._heuristic_intent(df)
        heuristic_domain = heuristic_result["domain"]
        sub_intent       = _DOMAIN_SUB_INTENT.get(heuristic_domain, "Master Data")

        log(f"  [Domain/Heuristic] Candidate: {heuristic_domain} "
            f"(score={heuristic_result['score']}) | Intent: {heuristic_intent} | Sub: {sub_intent}")

        if self.llm_client is None:
            return {
                "domain":           heuristic_domain,
                "intent":           heuristic_intent,
                "sub_intent":       sub_intent,
                "confidence":       "Medium" if heuristic_result["score"] > 0 else "Low",
                "method":           "Heuristic",
                "reasoning":        f"Keyword match score: {heuristic_result['score']}",
                "target_variables": [],
                "is_time_series":   self._heuristic_time_series(df),
                "heuristic_scores": heuristic_result["all_scores"],
            }

        # ── Pass 2: LLM as primary detector ──
        try:
            llm_result = self._llm_detect(df, heuristic_result, heuristic_intent, log)
            llm_domain = llm_result.get("domain", heuristic_domain)
            llm_result["sub_intent"] = _DOMAIN_SUB_INTENT.get(llm_domain, sub_intent)
            log(f"  [Domain/LLM] Domain: {llm_domain} | Intent: {llm_result['intent']} "
                f"| Sub: {llm_result['sub_intent']} (confidence={llm_result['confidence']})")
            if llm_result.get("reasoning"):
                log(f"  [Domain/LLM] Reason: {llm_result['reasoning']}")
            llm_result["heuristic_scores"] = heuristic_result["all_scores"]
            return llm_result
        except Exception as e:
            log(f"  [Domain/LLM] LLM detection failed ({e}), using heuristic fallback.")
            return {
                "domain":           heuristic_domain,
                "intent":           heuristic_intent,
                "sub_intent":       sub_intent,
                "confidence":       "Medium",
                "method":           "Heuristic (LLM failed)",
                "reasoning":        str(e),
                "target_variables": [],
                "is_time_series":   self._heuristic_time_series(df),
                "heuristic_scores": heuristic_result["all_scores"],
            }

    # ────────────────────────────────────────
    # Pass 1: Keyword scoring
    # ────────────────────────────────────────
    def _keyword_score(self, df: pd.DataFrame) -> dict:
        cols = [str(c).lower().replace(" ", "_") for c in df.columns]
        scores = {domain: 0.0 for domain in DOMAIN_KEYWORDS}

        # Score column names
        for col in cols:
            for domain, keywords in DOMAIN_KEYWORDS.items():
                if any(kw in col for kw in keywords):
                    scores[domain] += 1

        # Score sample values of string columns (lightweight scan)
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]):
                sample_vals = df[col].dropna().astype(str).str.lower().head(20).tolist()
                for val in sample_vals:
                    for domain, keywords in DOMAIN_KEYWORDS.items():
                        if any(kw in val for kw in keywords):
                            scores[domain] += 0.5

        # Sort scores descending for top-3 hint
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_domain, best_score = sorted_scores[0]

        return {
            "domain":     best_domain if best_score > 0 else "Generic",
            "score":      round(best_score, 1),
            "top3":       [(d, round(s, 1)) for d, s in sorted_scores[:3]],
            "all_scores": {k: round(v, 1) for k, v in scores.items()},
        }

    def _heuristic_intent(self, df: pd.DataFrame) -> str:
        """
        Heuristic intent detection:
        1. Column names with predictive hints → Predictive
        2. High numeric ratio + binary columns + no contact cols → Predictive
        3. Contact columns (name, email, phone) present → Non-Predictive Business
        """
        cols_lower = [str(c).lower() for c in df.columns]

        # Check for explicit predictive-label column names
        if any(hint in col for col in cols_lower for hint in _PREDICTIVE_HINTS):
            return "Predictive"

        # Check for binary columns (0/1 or True/False) — typical ML flag columns
        binary_cols = 0
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                unique_vals = df[col].dropna().unique()
                if set(unique_vals).issubset({0, 1, 0.0, 1.0}):
                    binary_cols += 1

        numeric_ratio  = df.select_dtypes(include="number").shape[1] / max(len(df.columns), 1)
        contact_cols   = sum(1 for c in cols_lower if any(k in c for k in ["email", "phone", "mobile", "name"]))
        id_cols        = sum(1 for c in cols_lower if any(k in c for k in ["customer_id", "patient_id", "employee_id"]))

        if numeric_ratio > 0.65 and contact_cols == 0 and id_cols == 0:
            return "Predictive"
        if binary_cols >= 1 and numeric_ratio > 0.5 and contact_cols == 0:
            return "Predictive"

        return "Non-Predictive Business"

    def _heuristic_time_series(self, df: pd.DataFrame) -> bool:
        """Check for date/time ordering columns."""
        cols_lower = [str(c).lower() for c in df.columns]
        return any(
            k in c for c in cols_lower
            for k in ["date", "time", "timestamp", "period", "month", "year", "quarter", "week", "day"]
        )

    # ────────────────────────────────────────
    # Pass 2: LLM as primary decision maker
    # ────────────────────────────────────────
    def _llm_detect(
        self, df: pd.DataFrame, heuristic: dict, heuristic_intent: str, log=print
    ) -> dict:
        """
        Ask the LLM to be the PRIMARY domain detector.
        Sends a rich dataset profile for holistic judgment.
        Heuristic scores are provided as context hints — not the final answer.
        """
        columns    = list(df.columns)
        col_dtypes = {str(c): str(df[c].dtype) for c in df.columns}

        # Build rich per-column profiles
        col_profiles = self._build_column_profiles(df)

        # Sample rows (up to 5)
        sample_rows = df.head(5).astype(str).to_dict(orient="records")

        numeric_ratio = round(df.select_dtypes(include="number").shape[1] / max(len(df.columns), 1), 2)
        null_pct      = round(df.isna().mean().mean() * 100, 1)
        known_domains = sorted(DOMAIN_KEYWORDS.keys()) + ["Generic", "Other"]

        system_prompt = (
            "You are an expert data scientist specializing in dataset profiling and domain classification.\n"
            "Your job is to analyze a dataset and determine its DOMAIN, INTENT, and key properties.\n\n"
            "You are the PRIMARY decision maker. The heuristic keyword scores are provided as hints only —\n"
            "use your judgment based on the full column profiles and sample data.\n\n"
            "DOMAIN LIST (choose the best match or 'Generic' if none fit):\n"
            f"{json.dumps(known_domains, indent=2)}\n\n"
            "DATASET INTENT — choose EXACTLY ONE:\n"
            "  \"Predictive\"              — ML training, forecasting, analytical features, classification\n"
            "  \"Non-Predictive Business\" — CRM, ERP, HR records, transactions, master data, operational logs\n\n"
            "CLASSIFICATION RULES:\n"
            "  - Contact info (email, phone, name, address) → Non-Predictive Business\n"
            "  - Columns like: churn, fraud, label, target, class, is_*, has_*, will_* → Predictive\n"
            "  - Mostly numeric features (age, income, score, count) + no contact cols → Predictive\n"
            "  - Transaction records (order_id, invoice, payment_status) → Non-Predictive Business\n"
            "  - Clinical/patient records → Non-Predictive Business (unless explicit diagnosis label)\n"
            "  - Sensor/IoT readings with timestamps → Non-Predictive Business (Operational)\n"
            "  - Non-ASCII values (Hindi, Arabic, Tamil, etc.) in name/category columns → flag it\n\n"
            "TARGET VARIABLES: list columns that are prediction targets (empty if Non-Predictive)\n\n"
            "Return ONLY a JSON object with EXACTLY these keys:\n"
            "{\n"
            '  "domain": "<domain from list>",\n'
            '  "intent": "Predictive" | "Non-Predictive Business",\n'
            '  "confidence": "High" | "Medium" | "Low",\n'
            '  "reasoning": "<2-3 sentences explaining your decision>",\n'
            '  "target_variables": ["<col1>", "<col2>"],\n'
            '  "is_time_series": true | false,\n'
            '  "has_multilingual_data": true | false,\n'
            '  "special_characteristics": "<any unusual data patterns or domain-specific notes>"\n'
            "}"
        )

        # Compact the column profiles to avoid token overflow
        compact_profiles = {
            col: {
                "dtype": p["dtype"],
                "missing_pct": p["missing_pct"],
                "unique_count": p["unique_count"],
                "sample_values": p["sample_values"][:5],
                "non_ascii_ratio": p.get("non_ascii_ratio", 0),
            }
            for col, p in col_profiles.items()
        }

        user_prompt = (
            f"=== HEURISTIC HINT (keyword scoring — for reference only) ===\n"
            f"Top candidate domains: {json.dumps(heuristic.get('top3', []))}\n"
            f"Heuristic intent: {heuristic_intent}\n\n"
            f"=== DATASET OVERVIEW ===\n"
            f"Total columns: {len(columns)} | Numeric ratio: {numeric_ratio} | Avg null%: {null_pct}%\n"
            f"Column names: {json.dumps(columns)}\n"
            f"Column dtypes: {json.dumps(col_dtypes)}\n\n"
            f"=== COLUMN PROFILES ===\n"
            f"{json.dumps(compact_profiles, ensure_ascii=False, default=str, indent=2)}\n\n"
            f"=== SAMPLE ROWS (first 5) ===\n"
            f"{json.dumps(sample_rows, ensure_ascii=False, default=str, indent=2)}\n\n"
            "OUTPUT JSON:"
        )

        raw = self.llm_client.chat_completion_json(
            system_prompt, user_prompt, num_expected_keys=8, enable_thinking=True
        )

        if isinstance(raw, dict) and "domain" in raw:
            intent = str(raw.get("intent", heuristic_intent)).strip()
            # Normalize intent string
            if "predictive" in intent.lower() and "non" not in intent.lower():
                intent = "Predictive"
            else:
                intent = "Non-Predictive Business"

            target_vars = raw.get("target_variables", [])
            if not isinstance(target_vars, list):
                target_vars = []

            detected_domain = str(raw.get("domain", heuristic["domain"])).strip()
            # Validate domain is in our known list
            all_known = list(DOMAIN_KEYWORDS.keys()) + ["Generic"]
            if detected_domain not in all_known:
                log(f"  [Domain/LLM] Unknown domain '{detected_domain}' returned — keeping heuristic.")
                detected_domain = heuristic["domain"]

            return {
                "domain":                 detected_domain,
                "intent":                 intent,
                "confidence":             str(raw.get("confidence", "Medium")).strip(),
                "method":                 "LLM-primary",
                "reasoning":              str(raw.get("reasoning", "LLM domain & intent detection")).strip(),
                "target_variables":       [str(v) for v in target_vars if v in columns],
                "is_time_series":         bool(raw.get("is_time_series", False)),
                "has_multilingual_data":  bool(raw.get("has_multilingual_data", False)),
                "special_characteristics": str(raw.get("special_characteristics", "")).strip(),
            }

        # LLM parse failed — fall back to heuristic
        log("  [Domain/LLM] Response parse failed. Falling back to heuristic.")
        return {
            "domain":           heuristic["domain"],
            "intent":           heuristic_intent,
            "confidence":       "Medium",
            "method":           "Heuristic (LLM parse failed)",
            "reasoning":        f"LLM returned unparseable response: {str(raw)[:100]}",
            "target_variables": [],
            "is_time_series":   self._heuristic_time_series(df),
        }

    def _build_column_profiles(self, df: pd.DataFrame) -> dict:
        """Build a rich per-column profile for the LLM context."""
        from backend.schema_detector import column_non_ascii_ratio, column_script_distribution
        profiles = {}
        for col in df.columns:
            series = df[col]
            missing_count = int(series.isna().sum())
            total = len(series)
            missing_pct = round(missing_count / max(total, 1) * 100, 1)
            unique_count = int(series.nunique())

            # Sample values (non-null, up to 8)
            sample_vals = [str(v) for v in series.dropna().head(8).tolist()]

            profile = {
                "dtype":        str(series.dtype),
                "missing_pct":  missing_pct,
                "unique_count": unique_count,
                "sample_values": sample_vals,
            }

            # Numeric stats
            if pd.api.types.is_numeric_dtype(series):
                non_null = series.dropna()
                if len(non_null) > 0:
                    profile["min"]  = round(float(non_null.min()), 3)
                    profile["max"]  = round(float(non_null.max()), 3)
                    profile["mean"] = round(float(non_null.mean()), 3)

            # String / object stats
            if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
                non_ascii = column_non_ascii_ratio(series)
                profile["non_ascii_ratio"] = round(non_ascii, 3)
                if non_ascii > 0.01:
                    profile["scripts_detected"] = column_script_distribution(series)

            profiles[col] = profile
        return profiles
