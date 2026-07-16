"""
Currency detection and conversion module.
Detects mixed-currency columns (USD, EUR, GBP, JPY, etc.) and converts
all values to Indian Rupees (INR).

Exchange rates are fetched live from the free Frankfurter API
(https://api.frankfurter.app) with a hardcoded fallback if offline.
"""
import re
import requests
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional


# ─────────────────────────────────────────────────────────────
# Currency symbol / code → ISO 4217 code mapping
# ─────────────────────────────────────────────────────────────
SYMBOL_TO_CODE: Dict[str, str] = {
    "$":   "USD",
    "us$": "USD",
    "usd": "USD",
    "€":   "EUR",
    "eur": "EUR",
    "£":   "GBP",
    "gbp": "GBP",
    "¥":   "JPY",
    "jpy": "JPY",
    "¥":   "CNY",   # also used for Chinese yuan — context-dependent
    "cny": "CNY",
    "rmb": "CNY",
    "₹":   "INR",
    "rs":  "INR",
    "rs.": "INR",
    "inr": "INR",
    "au$": "AUD",
    "aud": "AUD",
    "ca$": "CAD",
    "cad": "CAD",
    "chf": "CHF",
    "sgd": "SGD",
    "s$":  "SGD",
    "aed": "AED",
    "dh":  "AED",
    "sar": "SAR",
    "hkd": "HKD",
    "hk$": "HKD",
    "myr": "MYR",
    "rm":  "MYR",
    "brl": "BRL",
    "r$":  "BRL",
    "krw": "KRW",
    "₩":   "KRW",
    "rub": "RUB",
    "₽":   "RUB",
    "try": "TRY",
    "₺":   "TRY",
    "nzd": "NZD",
    "nz$": "NZD",
    "zar": "ZAR",
    "r":   "ZAR",
    "pkr": "PKR",
    "bdt": "BDT",
    "lkr": "LKR",
    "npr": "NPR",
}

# Fallback exchange rates (to INR) if Frankfurter is offline
FALLBACK_RATES: Dict[str, float] = {
    "USD": 83.50,
    "EUR": 90.10,
    "GBP": 105.80,
    "JPY":  0.56,
    "CNY": 11.55,
    "INR":  1.00,
    "AUD": 54.40,
    "CAD": 61.80,
    "CHF": 93.20,
    "SGD": 62.10,
    "AED": 22.74,
    "SAR": 22.26,
    "HKD": 10.70,
    "MYR": 17.90,
    "BRL": 16.20,
    "KRW":  0.063,
    "RUB":  0.92,
    "TRY":  2.61,
    "NZD": 50.50,
    "ZAR":  4.60,
    "PKR":  0.30,
    "BDT":  0.76,
    "LKR":  0.26,
    "NPR":  0.63,
}


def _fetch_live_rates(source_codes: list) -> Dict[str, float]:
    """
    Fetch live exchange rates from Frankfurter (free, no API key).
    Returns {currency_code: rate_to_INR}.
    Falls back to FALLBACK_RATES if the request fails.
    """
    unique_codes = [c for c in set(source_codes) if c != "INR"]
    if not unique_codes:
        return {}

    rates: Dict[str, float] = {}
    try:
        # Frankfurter API: base=INR, get how many foreign units = 1 INR
        # We need INR per foreign unit, so we fetch base=foreign, amount=1
        symbols = ",".join(unique_codes)
        url = f"https://api.frankfurter.app/latest?from=INR&to={symbols}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        # data['rates'] = {USD: 0.01196, EUR: 0.011, ...}  (1 INR = X foreign)
        # We want: 1 foreign = ? INR  → invert
        for code, fwd_rate in data.get("rates", {}).items():
            if fwd_rate and fwd_rate != 0:
                rates[code] = round(1.0 / fwd_rate, 6)
        print(f"  [Currency] Live rates fetched for: {list(rates.keys())}")
    except Exception as e:
        print(f"  [Currency] Live rate fetch failed ({e}). Using fallback rates.")
        for code in unique_codes:
            rates[code] = FALLBACK_RATES.get(code, 1.0)

    # Always include INR → INR = 1
    rates["INR"] = 1.0
    return rates


# ─────────────────────────────────────────────────────────────
# Value parser: extracts currency code + numeric amount
# ─────────────────────────────────────────────────────────────
# Regex: optional symbol, optional space, numeric, optional code
_VALUE_RE = re.compile(
    r"^"
    r"(?P<sym1>[^\d\s\-\.]{0,4})?"   # leading symbol (e.g., $, £, ₹)
    r"\s*"
    r"(?P<num>-?[\d,]+\.?\d*)"       # the number, possibly with commas
    r"\s*"
    r"(?P<sym2>[a-zA-Z$€£¥₹₩₽₺]{0,5})?"  # trailing code (e.g., USD, EUR)
    r"$",
    re.IGNORECASE,
)


def _parse_value(raw: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Parse a raw string into (amount_float, currency_code).
    Returns (None, None) if unparseable.
    """
    raw = str(raw).strip()
    m   = _VALUE_RE.match(raw)
    if not m:
        return None, None

    num_str = m.group("num").replace(",", "")
    try:
        amount = float(num_str)
    except ValueError:
        return None, None

    # Identify currency from symbol1 or symbol2
    sym1 = (m.group("sym1") or "").strip().lower()
    sym2 = (m.group("sym2") or "").strip().lower()

    for sym in [sym1, sym2]:
        if sym in SYMBOL_TO_CODE:
            return amount, SYMBOL_TO_CODE[sym]

    # No explicit currency found — assume "unknown" (caller will decide)
    return amount, None


# ─────────────────────────────────────────────────────────────
# CurrencyConverter
# ─────────────────────────────────────────────────────────────
class CurrencyConverter:
    """
    Detects columns with mixed-currency values and converts them to INR.

    Usage:
        converter = CurrencyConverter()
        df, report = converter.convert_all(df)
    """

    def __init__(self):
        self.conversion_report: list = []   # per-column summary for the UI

    def _detect_currency_columns(self, df: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """
        Scan all string columns for currency patterns.
        Returns {col: {currency_code: count}} for columns that have
        at least one non-INR currency value.
        """
        candidate_cols: Dict[str, Dict[str, int]] = {}

        # Consider string columns AND numeric columns whose name hints at money
        money_keywords = {
            "price", "cost", "fee", "fare", "amount", "salary",
            "revenue", "earning", "income", "pay", "wage",
            "budget", "charge", "rate", "value", "total",
        }

        for col in df.columns:
            col_lower = col.lower()
            is_money_name = any(kw in col_lower for kw in money_keywords)

            series    = df[col].dropna().astype(str)
            if len(series) == 0:
                continue

            currency_counts: Dict[str, int] = {}
            parseable = 0

            for val in series:
                amount, code = _parse_value(val)
                if amount is not None:
                    parseable += 1
                    detected_code = code or "UNKNOWN"
                    currency_counts[detected_code] = currency_counts.get(detected_code, 0) + 1

            # Column qualifies if:
            #  - Has mixed non-INR currencies, OR
            #  - Name is money-related and has any recognised currency symbol
            has_foreign = any(c not in ("INR", "UNKNOWN") for c in currency_counts)
            has_mixed   = len([c for c in currency_counts if c != "UNKNOWN"]) > 1

            if (has_foreign or has_mixed) and parseable > 0:
                candidate_cols[col] = currency_counts

        return candidate_cols

    def convert_all(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
        """
        Detect currency columns and convert all values to INR.
        Returns the modified DataFrame and a conversion_report list.
        """
        self.conversion_report = []
        currency_cols = self._detect_currency_columns(df)

        if not currency_cols:
            print("  [Currency] No mixed-currency columns detected.")
            return df, []

        print(f"  [Currency] Detected {len(currency_cols)} currency column(s): {list(currency_cols.keys())}")

        # Collect all unique currency codes across all columns
        all_codes = set()
        for counts in currency_cols.values():
            all_codes.update(counts.keys())
        all_codes.discard("UNKNOWN")
        all_codes.discard("INR")

        # Fetch live rates once for all needed currencies
        rates = _fetch_live_rates(list(all_codes))

        for col, currency_counts in currency_cols.items():
            df, col_report = self._convert_column(df, col, rates, currency_counts)
            self.conversion_report.append(col_report)

        return df, self.conversion_report

    def _convert_column(
        self,
        df: pd.DataFrame,
        col: str,
        rates: Dict[str, float],
        currency_counts: Dict[str, int],
    ) -> Tuple[pd.DataFrame, dict]:
        """Convert all values in a single column to INR floats."""
        converted_values  = []
        rows_converted    = 0
        rows_assumed_inr  = 0
        rows_failed       = 0
        currencies_seen: Dict[str, int] = {}

        for val in df[col]:
            if pd.isna(val) or str(val).strip() == "":
                converted_values.append(np.nan)
                continue

            amount, code = _parse_value(str(val))

            if amount is None:
                # Cannot parse at all — keep original as NaN
                converted_values.append(np.nan)
                rows_failed += 1
                continue

            if code is None or code == "UNKNOWN":
                # No explicit symbol — assume already INR (or dominant currency)
                converted_values.append(round(amount, 2))
                rows_assumed_inr += 1
                continue

            rate = rates.get(code, FALLBACK_RATES.get(code, 1.0))
            inr_amount = round(amount * rate, 2)
            converted_values.append(inr_amount)
            rows_converted += 1
            currencies_seen[code] = currencies_seen.get(code, 0) + 1

        df[col] = converted_values
        # Ensure column is numeric
        df[col] = pd.to_numeric(df[col], errors="coerce")

        col_report = {
            "column":            col,
            "currencies_found":  currency_counts,
            "rates_used":        {c: rates.get(c, FALLBACK_RATES.get(c, 1.0)) for c in currencies_seen},
            "rows_converted":    rows_converted,
            "rows_assumed_inr":  rows_assumed_inr,
            "rows_failed":       rows_failed,
            "target_currency":   "INR (₹)",
        }

        print(
            f"  [Currency] '{col}': {rows_converted} values converted to INR "
            f"({', '.join(currencies_seen.keys()) or 'none'})"
        )
        return df, col_report
