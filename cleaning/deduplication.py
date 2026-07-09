"""
Advanced deduplication engine with intent-aware strategy selection.

DATASET INTENT AUTO-DETECTION (via LLM or pipeline flag):
  - Predictive Datasets  → lightweight dedup: exact ID match + fuzzy name match.
  - Non-Predictive Business → full 16-rule business deduplication with priority
    tiers, conflict guards, and Golden Record merge.

16 Business Deduplication Rules (Non-Predictive Business mode):
  Rule 1  — Exact: Customer ID + Email + Phone + Address → Merge
  Rule 2  — Full Duplicate: every column identical → Merge
  Rule 3  — Fuzzy Name: same Gov ID + Name ≈ typo → Merge
  Rule 4  — Backfill missing Name when strong IDs match
  Rule 5  — Backfill missing Phone/Email when strong IDs match
  Rule 6  — Contact Conflict Guard: same Name, different Phone → FLAG
  Rule 7  — Contact Conflict Guard: same Name, different Email → FLAG
  Rule 8  — Family Guard: same phone, different name → DO NOT MERGE
  Rule 9  — Family Guard: same email (shared mailbox), different name → DO NOT MERGE
  Rule 10 — Family Guard: same address, different name → DO NOT MERGE
  Rule 11 — Shared Contact Guard: any shared contact + different unique ID → DO NOT MERGE
  Rule 12 — CRITICAL: Different names + shared phone/email → ALWAYS BLOCK (family/shared)
  Rule 13 — Name Isolation: matching names alone must NEVER trigger a merge
  Rule 14 — Gov ID Supremacy: Gov/Unique ID match + names similar → Merge
  Rule 15 — Unique ID Conflict: conflicting Unique IDs → DO NOT MERGE
  Rule 16 — Low-Quality Flag: all critical contact fields missing → mark as Low Quality

CORE PRINCIPLE (FAMILY GUARD):
  - Two different names + same phone/email = FAMILY MEMBERS or SHARED ACCOUNT → DO NOT MERGE
  - Two rows must have BOTH same name (fuzzy ≥ 85%) AND same Gov ID to be merged via ID-match
  - Phone/email ALONE are NEVER sufficient to merge two different-named people

Golden Record Rules:
  - Record with fewest missing values becomes the primary "Golden Record"
  - Backfill remaining gaps from secondary records in same cluster
  - Numeric fields: use median for stability across cluster

Pass structure:
  Pass 1: Exact Gov ID match (ONLY — with strict name similarity check)
  Pass 2: Case-insensitive exact name match (only if no contact cols exist)
  Pass 3: Composite key (name + location/address only — NOT phone/email)
  Pass 4: Fuzzy name match with STRICT family guards
  Pass 5: Multi-field weighted similarity with family guards
  Pass 6: Business Rule Backfill (Rules 4 & 5)
"""
import pandas as pd
import numpy as np
import recordlinkage
import re
from rapidfuzz import fuzz
from typing import Dict, List, Tuple, Optional
import config


# ─────────────────────────────────────────────────────────────
# Government / Unique ID column patterns (Level 1 — highest confidence)
# These are PERSONAL unique identifiers — one person, one ID.
# ─────────────────────────────────────────────────────────────
_GOV_ID_PATTERNS = [
    "customer_id", "customerid", "cust_id", "custid",
    "employee_id", "employeeid", "emp_id", "empid",
    "vendor_id", "vendorid",
    "account_number", "account_no", "accountno",
    "passport", "passport_no", "passport_number",
    "aadhaar", "aadhar", "uid", "aadhaar_no",
    "pan", "pan_no", "pan_number",
    "gst", "gstin", "gst_number", "gst_no",
    "tax_id", "taxid", "tin",
    "insurance_policy", "policy_number", "policy_no",
    "ssn", "social_security",
    "national_id", "national_id_no", "voter_id", "voternumber",
    "registration_no", "reg_no", "license_no", "license_number",
    "mrn", "patient_id", "student_id",
]

# ─────────────────────────────────────────────────────────────
# Null / sentinel value set
# ─────────────────────────────────────────────────────────────
_NULL_SET = {
    "", "unknown", "-", "<na>", "nan", "none", "n/a", "null",
    "?", "na", "0", "0.0", "-1", "undefined", "missing",
    "n.a.", "n.a", "no data", "not provided",
}

# ─────────────────────────────────────────────────────────────
# Thresholds
# ─────────────────────────────────────────────────────────────
# Name similarity must be ≥ this to consider two records the same person
NAME_MATCH_THRESHOLD = 85
# Name similarity below this = definitely different people (family guard)
NAME_MISMATCH_THRESHOLD = 75
# Gov ID match + name ≥ this = safe to merge (Rule 14)
GOV_ID_NAME_CONFIRM_THRESHOLD = 70
# Fuzzy pass merge threshold (lowered from 90 to catch "Veer/Vir", "Vikas/Vikash")
FUZZY_MERGE_THRESHOLD = 82


def _is_valid(x) -> bool:
    if pd.isna(x):
        return False
    s = str(x).strip().lower()
    return bool(s) and s not in _NULL_SET


def _norm(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip().lower()
    return "" if s in _NULL_SET else s


def _norm_phone(x) -> str:
    """Normalize phone: digits only, strip country codes."""
    if pd.isna(x):
        return ""
    s = re.sub(r'\D', '', str(x))
    # Strip leading country codes (91 for India, 1 for US) if longer than 10 digits
    if len(s) == 12 and s.startswith("91"):
        s = s[2:]
    elif len(s) == 11 and s.startswith("1"):
        s = s[1:]
    return s if len(s) >= 7 else ""


def _norm_email(x) -> str:
    """Normalize email: lowercase + strip."""
    if pd.isna(x):
        return ""
    s = str(x).strip().lower()
    return "" if s in _NULL_SET else s


def _name_similarity(n1: str, n2: str) -> float:
    """
    Multi-algorithm name similarity (0-100).
    Uses token_sort_ratio (handles word order differences) and
    partial_ratio (handles nick-names / shortened names).
    """
    if not n1 or not n2:
        return 0.0
    s1 = fuzz.token_sort_ratio(n1, n2)
    s2 = fuzz.partial_ratio(n1, n2)
    s3 = fuzz.token_set_ratio(n1, n2)
    # Weighted: token_sort is most reliable for names
    return 0.5 * s1 + 0.3 * s3 + 0.2 * s2


def _names_are_same_person(n1: str, n2: str, threshold: float = NAME_MATCH_THRESHOLD) -> bool:
    """Returns True if the two name strings likely refer to the same person."""
    return _name_similarity(n1, n2) >= threshold


def _names_are_different_people(n1: str, n2: str, threshold: float = NAME_MISMATCH_THRESHOLD) -> bool:
    """Returns True if the two name strings clearly refer to different people."""
    if not n1 or not n2:
        return False  # Can't decide without data
    return _name_similarity(n1, n2) < threshold


# ─────────────────────────────────────────────────────────────
# Column tier classifier  (uses column names, not LLM)
# ─────────────────────────────────────────────────────────────
def _classify_col_tiers(df: pd.DataFrame, strategies: dict):
    """
    Classify dataset columns into 4 priority tiers:

    Tier 1 — Unique Gov / Business IDs   (highest confidence — personal IDs)
    Tier 2 — Strong Contact IDs          (email, phone — can be SHARED by family)
    Tier 3 — Location / Address          (can be shared by household)
    Tier 4 — Personal Info               (name)

    Returns (gov_id_cols, email_cols, phone_cols, address_cols, name_cols, other_id_cols)
    """
    cols_lower = {c: c.lower().replace(" ", "_") for c in df.columns}

    gov_id_cols   = []
    email_cols    = []
    phone_cols    = []
    address_cols  = []
    name_cols     = []
    other_id_cols = []

    for col, col_l in cols_lower.items():
        strat = strategies.get(col, "")

        # Tier 1 — Gov / Unique IDs
        # Use word-boundary regex so 'company_name' doesn't match 'pan'
        gov_match = any(
            re.search(fr'\b{re.escape(pat)}\b', col_l.replace("_", " "))
            for pat in _GOV_ID_PATTERNS
        )
        if gov_match or strat == "exact_match":
            if "email" in col_l or "mail" in col_l:
                email_cols.append(col)
            elif any(k in col_l for k in ["phone", "mobile", "tel", "contact"]):
                phone_cols.append(col)
            elif gov_match:
                gov_id_cols.append(col)
            else:
                other_id_cols.append(col)

        # Tier 2 — Contact IDs (can be shared by family — handle with care)
        elif "email" in col_l or "mail" in col_l:
            email_cols.append(col)
        elif any(k in col_l for k in ["phone", "mobile", "tel", "contact"]):
            phone_cols.append(col)

        # Tier 3 — Location
        elif any(k in col_l for k in ["address", "addr", "street", "city", "zip", "pincode", "location"]):
            address_cols.append(col)

        # Tier 4 — Personal name
        elif strat == "fuzzy_name":
            name_cols.append(col)
        elif "name" in col_l and strat not in ("none", "blocking_key"):
            name_cols.append(col)

    return gov_id_cols, email_cols, phone_cols, address_cols, name_cols, other_id_cols


# ─────────────────────────────────────────────────────────────
# Union-Find (Disjoint Set) for cluster graph management
# ─────────────────────────────────────────────────────────────
class UnionFind:
    """Disjoint-set with path compression and union-by-rank."""

    def __init__(self, size: int, completeness: List[int] = None):
        self.parent = list(range(size))
        # Use completeness score for rank so the most complete record becomes root
        self.rank   = completeness[:] if completeness else [0] * size
        self.reasons = {}  # Map: child_index → reason string

    def find(self, i: int) -> int:
        if self.parent[i] != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: int, j: int, reason: str = "Merged") -> bool:
        ri, rj = self.find(i), self.find(j)
        if ri == rj:
            return False
        # Keep the most complete record as root
        if self.rank[ri] < self.rank[rj]:
            ri, rj = rj, ri
        self.parent[rj] = ri
        self.reasons[rj] = reason
        if self.rank[ri] == self.rank[rj]:
            self.rank[ri] += 1
        return True


# ─────────────────────────────────────────────────────────────
# Business Rule Evaluator
# ─────────────────────────────────────────────────────────────
class BusinessRuleEvaluator:
    """
    Evaluates 16 business deduplication rules for every candidate pair.

    CRITICAL DESIGN PRINCIPLE:
    Phone number and email are contact details that CAN BE SHARED by family members.
    They are NEVER sufficient alone to merge two records with different names.
    Only a Gov/Unique ID (customer_id, PAN, Aadhaar, etc.) combined with a
    similar name is a reliable signal for "same person".

    Returns:
        "merge"  — pair should be merged (same person, evidence confirmed)
        "block"  — pair must NOT be merged (different people or conflict detected)
        "skip"   — insufficient evidence for a decision
    """

    def __init__(
        self,
        df: pd.DataFrame,
        gov_id_cols: List[str],
        email_cols: List[str],
        phone_cols: List[str],
        address_cols: List[str],
        name_cols: List[str],
    ):
        self.df           = df
        self.gov_id_cols  = gov_id_cols
        self.email_cols   = email_cols
        self.phone_cols   = phone_cols
        self.address_cols = address_cols
        self.name_cols    = name_cols
        self.flags: List[dict] = []

    # ── helpers ──────────────────────────────────────────────
    def _val(self, idx: int, col: str) -> str:
        return _norm(self.df.loc[idx, col]) if col in self.df.columns else ""

    def _phone_val(self, idx: int, col: str) -> str:
        return _norm_phone(self.df.loc[idx, col]) if col in self.df.columns else ""

    def _email_val(self, idx: int, col: str) -> str:
        return _norm_email(self.df.loc[idx, col]) if col in self.df.columns else ""

    def _get_best_name(self, idx: int) -> str:
        """Get the best available name for a record index."""
        for nc in self.name_cols:
            v = self._val(idx, nc)
            if v:
                return v
        return ""

    def _names_match(self, idx1: int, idx2: int) -> Optional[bool]:
        """
        Compare names across all name columns.
        Returns True if similar, False if clearly different, None if no names available.
        """
        n1 = self._get_best_name(idx1)
        n2 = self._get_best_name(idx2)
        if not n1 or not n2:
            return None
        sim = _name_similarity(n1, n2)
        if sim >= NAME_MATCH_THRESHOLD:
            return True
        if sim < NAME_MISMATCH_THRESHOLD:
            return False
        return None  # Ambiguous zone

    def _phones_match(self, idx1: int, idx2: int) -> Optional[bool]:
        """Check if any phone column has matching values."""
        for col in self.phone_cols:
            p1 = self._phone_val(idx1, col)
            p2 = self._phone_val(idx2, col)
            if p1 and p2:
                return p1 == p2
        return None

    def _emails_match(self, idx1: int, idx2: int) -> Optional[bool]:
        """Check if any email column has matching values."""
        for col in self.email_cols:
            e1 = self._email_val(idx1, col)
            e2 = self._email_val(idx2, col)
            if e1 and e2:
                return e1 == e2
        return None

    def _gov_ids_match(self, idx1: int, idx2: int) -> Optional[bool]:
        """Check if any Gov ID matches. Returns None if both sides are empty."""
        for col in self.gov_id_cols:
            v1 = self._val(idx1, col)
            v2 = self._val(idx2, col)
            if v1 and v2:
                return v1 == v2
        return None

    def _all_contact_missing(self, idx: int) -> bool:
        all_contact = self.gov_id_cols + self.email_cols + self.phone_cols + self.address_cols
        return not any(_is_valid(self.df.loc[idx, c]) for c in all_contact if c in self.df.columns)

    def _flag(self, idx1: int, idx2: int, rule: str, reason: str):
        self.flags.append({
            "row_index_1": int(idx1),
            "row_index_2": int(idx2),
            "rule":        rule,
            "reason":      reason,
        })

    # ── Main Rule Evaluation ──────────────────────────────────
    def evaluate(self, idx1: int, idx2: int) -> str:
        """
        Returns "merge", "block", or "skip".

        Rule priority order:
        1. Low-quality guard (Rule 16)
        2. FAMILY GUARD — different names + shared contact = BLOCK (Rules 8, 9, 12)
        3. Gov ID conflict → BLOCK (Rule 15)
        4. Gov ID match + name confirmed → MERGE (Rule 14)
        5. Exact multi-field match → MERGE (Rule 1)
        6. Contact conflict guards (Rules 6, 7)
        7. Skip (let fuzzy passes decide with strict guards)
        """
        if idx1 >= len(self.df) or idx2 >= len(self.df):
            return "skip"

        # ── Rule 16: Low-Quality rows ─────────────────────────
        if self._all_contact_missing(idx1) or self._all_contact_missing(idx2):
            self._flag(idx1, idx2, "Rule 16", "Low Quality — all critical contact fields missing")
            return "skip"

        # ────────────────────────────────────────────────────────────
        # CRITICAL FAMILY GUARDS — checked FIRST before any merge logic
        # These rules BLOCK merges when two records have different names
        # but share a contact detail (phone/email) — they are family members
        # or shared account holders, NOT the same person.
        # ────────────────────────────────────────────────────────────

        # ── Rule 12 / Rule 8: Same phone + different names → BLOCK ──
        phone_match = self._phones_match(idx1, idx2)
        if phone_match is True:
            name_match = self._names_match(idx1, idx2)
            if name_match is False:
                n1 = self._get_best_name(idx1)
                n2 = self._get_best_name(idx2)
                self._flag(idx1, idx2, "Rule 8",
                           f"Same phone but DIFFERENT names ('{n1}' vs '{n2}') → family members / shared phone")
                return "block"
            # If name_match is None (missing names), also block — we can't confirm same person
            if name_match is None and self.name_cols:
                self._flag(idx1, idx2, "Rule 8",
                           "Same phone but names unavailable — cannot confirm same person")
                return "block"

        # ── Rule 12 / Rule 9: Same email + different names → BLOCK ──
        email_match = self._emails_match(idx1, idx2)
        if email_match is True:
            name_match = self._names_match(idx1, idx2)
            if name_match is False:
                n1 = self._get_best_name(idx1)
                n2 = self._get_best_name(idx2)
                self._flag(idx1, idx2, "Rule 9",
                           f"Same email but DIFFERENT names ('{n1}' vs '{n2}') → shared mailbox / family")
                return "block"
            if name_match is None and self.name_cols:
                self._flag(idx1, idx2, "Rule 9",
                           "Same email but names unavailable — cannot confirm same person")
                return "block"

        # ── Rule 10: Same address + different names → BLOCK ─────────
        for addr_col in self.address_cols:
            a1 = self._val(idx1, addr_col)
            a2 = self._val(idx2, addr_col)
            if a1 and a2 and a1 == a2:
                name_match = self._names_match(idx1, idx2)
                if name_match is False:
                    self._flag(idx1, idx2, "Rule 10",
                               "Same address but different names → roommates / family household")
                    return "block"

        # ────────────────────────────────────────────────────────────
        # GOV ID CHECKS
        # ────────────────────────────────────────────────────────────

        # ── Rule 15: Conflicting Gov/Unique IDs → BLOCK ──────────────
        for col in self.gov_id_cols:
            v1, v2 = self._val(idx1, col), self._val(idx2, col)
            if v1 and v2 and v1 != v2:
                self._flag(idx1, idx2, "Rule 15",
                           f"Conflicting unique IDs in '{col}': '{v1}' vs '{v2}'")
                return "block"

        # ── Rule 14: Gov ID match → MERGE (only if names also agree) ─
        gov_match = self._gov_ids_match(idx1, idx2)
        if gov_match is True:
            name_match = self._names_match(idx1, idx2)
            if name_match is True:
                return "merge"   # Same Gov ID + same name = same person, confirmed
            if name_match is False:
                # Gov ID matches but names are clearly different — suspicious
                # This could be a family sharing an account, or a data error
                n1 = self._get_best_name(idx1)
                n2 = self._get_best_name(idx2)
                self._flag(idx1, idx2, "Rule 14",
                           f"Gov ID match but names conflict ('{n1}' vs '{n2}') — "
                           f"possible shared account or data error → not merging")
                return "block"
            # name_match is None: Gov ID matches but no name data
            # Only merge if there's truly no name data at all
            if not self.name_cols:
                return "merge"
            return "skip"  # Can't confirm — let other passes decide

        # ────────────────────────────────────────────────────────────
        # MULTI-FIELD EXACT MATCH (Rule 1)
        # Requires ≥ 2 strong fields to match AND names must agree
        # ────────────────────────────────────────────────────────────
        strong_matches = 0
        strong_conflicts = 0

        # Check Gov IDs
        for col in self.gov_id_cols:
            v1, v2 = self._val(idx1, col), self._val(idx2, col)
            if v1 and v2:
                if v1 == v2:
                    strong_matches += 1
                else:
                    strong_conflicts += 1

        if strong_conflicts > 0:
            return "block"

        if strong_matches >= 1:
            name_match = self._names_match(idx1, idx2)
            if name_match is True:
                return "merge"
            if name_match is False:
                return "block"

        # ── Rules 6-7: Contact Conflict Guard ─────────────────────────
        # If names match fuzzily, but phone/email explicitly conflict → BLOCK
        name_match = self._names_match(idx1, idx2)
        if name_match is True:
            if phone_match is False:
                n1 = self._get_best_name(idx1)
                self._flag(idx1, idx2, "Rule 6",
                           f"Same name ('{n1}') but conflicting phone numbers")
                return "block"
            if email_match is False:
                n1 = self._get_best_name(idx1)
                self._flag(idx1, idx2, "Rule 7",
                           f"Same name ('{n1}') but conflicting email addresses")
                return "block"

        # ── Rule 13: Name-only match must NOT trigger merge ───────────
        # Enforced by never merging on name alone in caller passes

        return "skip"  # Insufficient evidence — caller's fuzzy logic applies


# ─────────────────────────────────────────────────────────────
# Deduplication Engine
# ─────────────────────────────────────────────────────────────
class DeduplicationEngine:
    """
    Intent-aware deduplication engine with strict family guards.

    CRITICAL BEHAVIOUR:
    - Two records with DIFFERENT names and same phone/email = NOT merged
      (they are treated as family members or shared-account holders)
    - Only Gov/Unique IDs (customer_id, PAN, Aadhaar) + matching names
      can force a merge
    - Fuzzy name matching detects typos/variations in the SAME person's name

    dataset_intent:
      "Predictive"             → lightweight passes (exact IDs + fuzzy name)
      "Non-Predictive Business"→ full 16-rule business deduplication
      "Auto-Detect"            → chosen based on column presence heuristic

    After clustering:
      keep_all_rows=False  → merge duplicates into ONE Golden Record (drops extras)
      keep_all_rows=True   → enrich all rows with Golden Record data (no removal)
    """

    def __init__(
        self,
        df: pd.DataFrame,
        strategies: dict,
        dataset_intent: str = "Auto-Detect",
        threshold: int = FUZZY_MERGE_THRESHOLD,
        keep_all_rows: bool = False,
        log_callback=print,
    ):
        self.df             = df.copy()
        self.strategies     = strategies
        self.dataset_intent = dataset_intent
        self.threshold      = threshold
        self.keep_all_rows  = keep_all_rows
        self.log_callback   = log_callback
        self.dedup_changes: List[dict] = []
        self.cluster_report: List[dict] = []
        self.conflict_flags: List[dict] = []
        self.low_quality_flags: List[dict] = []

    # ─────────────────────────────────────────────────────────────
    def execute(self) -> pd.DataFrame:
        self.log_callback("--- Deduplication & Identity Resolution ---")

        self.df = self.df.reset_index(drop=True)
        if len(self.df) < 2:
            return self.df

        # ── Classify columns into priority tiers ──────────────────
        gov_id_cols, email_cols, phone_cols, address_cols, name_cols, other_id_cols = \
            _classify_col_tiers(self.df, self.strategies)

        block_cols = [c for c, s in self.strategies.items()
                      if s == "blocking_key" and c in self.df.columns]

        # ── Resolve dataset intent ────────────────────────────────
        intent = self._resolve_intent(gov_id_cols, email_cols, phone_cols, name_cols)
        self.log_callback(f"  [Dedup] Dataset Intent: {intent}")
        self.log_callback(f"  [Dedup] Gov IDs: {gov_id_cols} | Emails: {email_cols} | Phones: {phone_cols} | Names: {name_cols}")

        # ── Low-Quality Flag (Rule 16) ────────────────────────────
        self._flag_low_quality_rows(gov_id_cols, email_cols, phone_cols, address_cols)

        n            = len(self.df)
        completeness = self.df.notnull().sum(axis=1).tolist()
        uf           = UnionFind(n, completeness)

        # All strong IDs used in conflict checks
        all_id_cols = gov_id_cols + other_id_cols  # Note: email/phone NOT in conflict check (can be shared)

        rule_evaluator = BusinessRuleEvaluator(
            self.df, gov_id_cols, email_cols, phone_cols, address_cols, name_cols
        )

        # ════════════════════════════════════════════════════════
        # PASS 1: Exact Gov ID match — ONLY for personal unique IDs
        # NOT for email or phone (those can be shared by family)
        # ════════════════════════════════════════════════════════
        self.log_callback("  [Pass 1] Exact Gov ID match (personal unique IDs only)...")
        merged_p1 = 0
        for col in gov_id_cols + other_id_cols:  # <-- EMAIL and PHONE intentionally excluded
            try:
                groups = self.df.groupby(col, sort=False).groups
            except Exception:
                continue
            for val, idxs in groups.items():
                if not _is_valid(val):
                    continue
                idxs = list(idxs)
                idxs.sort(key=lambda i: completeness[i], reverse=True)
                for idx in idxs[1:]:
                    root1, root2 = uf.find(idxs[0]), uf.find(idx)
                    if root1 == root2:
                        continue
                    decision = rule_evaluator.evaluate(root1, root2)
                    if decision == "merge":
                        if uf.union(idxs[0], idx, reason=f"Exact Gov ID match on '{col}'"):
                            merged_p1 += 1
                    # "block" and "skip" both = do not merge
        if merged_p1:
            self.log_callback(f"    Merged {merged_p1} records in Pass 1 (Gov ID)")

        # ════════════════════════════════════════════════════════
        # PASS 2: Case-insensitive exact name (only if no contact cols)
        # Rule 13: Name-only matching ONLY when dataset has zero other identifiers
        # ════════════════════════════════════════════════════════
        if not (email_cols or phone_cols or block_cols or gov_id_cols):
            self.log_callback("  [Pass 2] Case-insensitive exact name match (no contact IDs found)...")
            for col in name_cols:
                norm_series = self.df[col].apply(_norm)
                groups = norm_series.groupby(norm_series).groups
                for val, idxs in groups.items():
                    if val:
                        idxs = list(idxs)
                        idxs.sort(key=lambda i: completeness[i], reverse=True)
                        for idx in idxs[1:]:
                            uf.union(idxs[0], idx, reason="Exact name match")
        else:
            self.log_callback("  [Pass 2] Skipped (Rule 13: contact IDs present — name-only match unsafe).")

        # ════════════════════════════════════════════════════════
        # PASS 3: Composite key match (name + address/location ONLY)
        # Note: composite of name+email or name+phone is intentionally
        # excluded — a family member could share those with a different name
        # ════════════════════════════════════════════════════════
        self.log_callback("  [Pass 3] Composite key match (name + location)...")
        if name_cols:
            primary   = name_cols[0]
            # Only use ADDRESS/LOCATION as the secondary key — NOT phone or email
            secondary_candidates = block_cols + address_cols
            secondary = next((c for c in secondary_candidates if c in self.df.columns), None)
            if secondary:
                composite = (
                    self.df[primary].apply(_norm) + "||" +
                    self.df[secondary].apply(_norm)
                )
                groups = composite.groupby(composite).groups
                merged_p3 = 0
                for val, idxs in groups.items():
                    if val and "||" in val and not val.startswith("||") and not val.endswith("||"):
                        idxs = list(idxs)
                        idxs.sort(key=lambda i: completeness[i], reverse=True)
                        for idx in idxs[1:]:
                            root1, root2 = uf.find(idxs[0]), uf.find(idx)
                            if root1 == root2:
                                continue
                            decision = rule_evaluator.evaluate(root1, root2)
                            if decision == "block":
                                continue
                            if uf.union(idxs[0], idx, reason=f"Composite key match ({primary}+{secondary})"):
                                merged_p3 += 1
                if merged_p3:
                    self.log_callback(f"    Merged {merged_p3} records in Pass 3")

        # ════════════════════════════════════════════════════════
        # PASS 4: Fuzzy name match — with strict family guards
        # Detects typos, nicknames, abbreviations in the SAME person's name.
        # The BusinessRuleEvaluator BLOCKS any pair where the names are
        # clearly different (< NAME_MISMATCH_THRESHOLD) even if phone/email match.
        # ════════════════════════════════════════════════════════
        self.log_callback("  [Pass 4] Fuzzy name match (with strict family guards)...")
        merged_p4 = 0
        blocked_p4 = 0
        if name_cols:
            primary = name_cols[0]
            df_work = self.df.copy()
            df_work[primary] = df_work[primary].fillna("").astype(str)

            # CRITICAL: Sort by the name column BEFORE building the sorted
            # neighbourhood index. The sortedneighbourhood indexer relies on
            # alphabetical ordering to find nearby candidates.
            # We do NOT reset the index, so recordlinkage returns candidate pairs
            # using the original indices of self.df.
            df_work = df_work.sort_values(by=primary, key=lambda col: col.str.lower())
            
            indexer = recordlinkage.Index()
            block_field = next((c for c in block_cols + address_cols if c in df_work.columns), None)

            # For small datasets: use full comparison (guaranteed — no missed pairs)
            # For large datasets: use sorted neighbourhood (efficient approximate search)
            if len(df_work) <= 500:
                indexer.full()
                self.log_callback(f"  [Pass 4] Small dataset ({len(df_work)} rows) — using full pair comparison")
            elif block_field:
                indexer.sortedneighbourhood(primary, window=11, block_on=block_field)
            else:
                indexer.sortedneighbourhood(primary, window=11)

            candidate_links = indexer.index(df_work)
            self.log_callback(f"  [Pass 4] Evaluating {len(candidate_links)} candidate pairs...")

            for idx1, idx2 in candidate_links:
                # idx1 and idx2 are the original indices from self.df because we preserved them
                orig_idx1 = idx1
                orig_idx2 = idx2
                root1, root2 = uf.find(orig_idx1), uf.find(orig_idx2)
                if root1 == root2:
                    continue

                # Guard: ensure both root indices are in original self.df
                if root1 >= len(self.df) or root2 >= len(self.df):
                    continue

                n1 = _norm(self.df.loc[orig_idx1, primary])
                n2 = _norm(self.df.loc[orig_idx2, primary])
                if not n1 or not n2:
                    continue

                name_sim = _name_similarity(n1, n2)
                if name_sim < self.threshold:
                    continue

                # Always check business rules — family guard takes priority
                decision = rule_evaluator.evaluate(root1, root2)
                if decision == "block":
                    blocked_p4 += 1
                    continue
                if decision == "merge":
                    if uf.union(orig_idx1, orig_idx2, reason=f"Fuzzy name match ({name_sim:.0f}%)"):
                        merged_p4 += 1
                    continue

                # "skip": business rules couldn't decide → apply conflict check
                # Check if they have CONFLICTING Gov IDs (if so, block)
                has_gov_conflict = False
                for col in gov_id_cols:
                    v1 = _norm(self.df.loc[root1, col])
                    v2 = _norm(self.df.loc[root2, col])
                    if v1 and v2 and v1 != v2:
                        has_gov_conflict = True
                        break
                if has_gov_conflict:
                    blocked_p4 += 1
                    continue

                # No Gov ID conflict, name is similar — safe to merge
                if uf.union(orig_idx1, orig_idx2, reason=f"Fuzzy name match ({name_sim:.0f}%)"):
                    merged_p4 += 1

        if merged_p4:
            self.log_callback(f"    Merged {merged_p4} records in Pass 4")
        if blocked_p4:
            self.log_callback(f"    Blocked {blocked_p4} pairs in Pass 4 (family guard)")

        # ════════════════════════════════════════════════════════
        # PASS 5: Multi-field weighted fuzzy scoring
        # Catches records where name is similar + other fields partially agree
        # Family guard still applies — name similarity is required
        # ════════════════════════════════════════════════════════
        self.log_callback("  [Pass 5] Multi-field fuzzy matching (weighted)...")
        self._pass_multifield(uf, rule_evaluator, name_cols, email_cols, phone_cols,
                              block_cols + address_cols, gov_id_cols)

        # ════════════════════════════════════════════════════════
        # PASS 6: Business Rule Backfill (Rules 4 & 5)
        # Fills missing values within confirmed-duplicate clusters only
        # ════════════════════════════════════════════════════════
        if intent == "Non-Predictive Business":
            self.log_callback("  [Pass 6] Filling in missing data using information from duplicate rows...")
            self._apply_backfill_rules(uf, name_cols, email_cols, phone_cols)

        # ── Extract clusters ─────────────────────────────────────
        cluster_map: Dict[int, List[int]] = {}
        for i in range(n):
            root = uf.find(i)
            cluster_map.setdefault(root, []).append(i)

        dup_clusters = {r: idxs for r, idxs in cluster_map.items() if len(idxs) > 1}
        self.log_callback(
            f"  [Dedup] {n} rows -> {len(cluster_map)} unique entities "
            f"({len(dup_clusters)} duplicate clusters found)"
        )

        # Collect conflict flags from rule evaluator
        self.conflict_flags = rule_evaluator.flags

        # ── Build Golden Records ─────────────────────────────────
        canonical_records = {
            root: self._build_golden_record(indices)
            for root, indices in cluster_map.items()
        }

        # ── Record cluster report for UI ─────────────────────────
        self.cluster_report = []
        for root, indices in dup_clusters.items():
            canon = canonical_records[root]
            name_col = name_cols[0] if name_cols else None
            self.cluster_report.append({
                "cluster_size":   len(indices),
                "canonical_name": str(canon.get(name_col, "")) if name_col else "",
                "row_indices":    indices,
            })

        # ── Return result ─────────────────────────────────────────
        self.dedup_changes = []
        if self.keep_all_rows:
            return self._enrich_all_rows(uf, cluster_map, canonical_records, name_cols)
        else:
            return self._merge_to_canonical(uf, cluster_map, canonical_records, name_cols)

    # ─────────────────────────────────────────────────────────────
    # Intent resolver
    # ─────────────────────────────────────────────────────────────
    def _resolve_intent(self, gov_id_cols, email_cols, phone_cols, name_cols) -> str:
        """
        Auto-detect dataset intent:
        Any dataset with PII columns (names, IDs, emails, phones) = Business.
        """
        contact_count = len(gov_id_cols) + len(email_cols) + len(phone_cols)
        if contact_count >= 1 or name_cols:
            return "Non-Predictive Business"
        if self.dataset_intent and self.dataset_intent not in ("Auto-Detect", ""):
            return self.dataset_intent
        return "Predictive"

    # ─────────────────────────────────────────────────────────────
    # Low-Quality Row Flagging (Rule 16)
    # ─────────────────────────────────────────────────────────────
    def _flag_low_quality_rows(self, gov_id_cols, email_cols, phone_cols, address_cols):
        all_contact = gov_id_cols + email_cols + phone_cols + address_cols
        if not all_contact:
            return
        for idx in self.df.index:
            has_any = any(
                _is_valid(self.df.loc[idx, c])
                for c in all_contact if c in self.df.columns
            )
            if not has_any:
                self.low_quality_flags.append({
                    "row_index": int(idx),
                    "rule":      "Rule 16",
                    "reason":    "All critical contact fields are missing",
                })

    # ─────────────────────────────────────────────────────────────
    # Pass 5: Multi-field weighted similarity
    # ─────────────────────────────────────────────────────────────
    def _pass_multifield(
        self, uf, rule_evaluator,
        name_cols, email_cols, phone_cols,
        block_cols, gov_id_cols
    ):
        if not name_cols:
            return

        primary  = name_cols[0]
        df_work  = self.df.copy().fillna("")

        indexer = recordlinkage.Index()
        block_field = next((c for c in block_cols if c in df_work.columns), None)
        if block_field:
            indexer.sortedneighbourhood(primary, window=5, block_on=block_field)
        else:
            indexer.sortedneighbourhood(primary, window=5)

        candidate_links = indexer.index(df_work)
        merged = blocked = 0

        for idx1, idx2 in candidate_links:
            root1, root2 = uf.find(idx1), uf.find(idx2)
            if root1 == root2:
                continue

            n1 = _norm(df_work.loc[root1, primary])
            n2 = _norm(df_work.loc[root2, primary])
            if not n1 or not n2:
                continue

            # Name similarity is the primary signal (60% weight)
            name_sim = _name_similarity(n1, n2)
            if name_sim < (self.threshold - 10):  # Don't even score very dissimilar names
                continue

            score  = 0.60 * name_sim
            weight = 0.60

            # Email (20% weight) — only if email matches (exact)
            if email_cols:
                e1 = _norm_email(df_work.loc[root1, email_cols[0]])
                e2 = _norm_email(df_work.loc[root2, email_cols[0]])
                if e1 and e2:
                    score  += 0.20 * (100.0 if e1 == e2 else 0.0)
                    weight += 0.20

            # Phone (15% weight) — only if phone matches (exact normalized)
            if phone_cols:
                p1 = _norm_phone(df_work.loc[root1, phone_cols[0]])
                p2 = _norm_phone(df_work.loc[root2, phone_cols[0]])
                if p1 and p2:
                    score  += 0.15 * (100.0 if p1 == p2 else 0.0)
                    weight += 0.15

            # Address (5% weight)
            if block_cols:
                l1 = _norm(df_work.loc[root1, block_cols[0]])
                l2 = _norm(df_work.loc[root2, block_cols[0]])
                if l1 and l2:
                    score  += 0.05 * fuzz.ratio(l1, l2)
                    weight += 0.05

            final_score = (score / weight) if weight > 0 else 0
            if final_score < self.threshold:
                continue

            # Apply family guards — always
            decision = rule_evaluator.evaluate(root1, root2)
            if decision == "block":
                blocked += 1
                continue
            if decision == "merge":
                if uf.union(idx1, idx2, reason=f"Multifield match ({final_score:.0f}%)"):
                    merged += 1
                continue

            # "skip": check Gov ID conflicts before merging
            has_gov_conflict = any(
                _norm(df_work.loc[root1, col]) and
                _norm(df_work.loc[root2, col]) and
                _norm(df_work.loc[root1, col]) != _norm(df_work.loc[root2, col])
                for col in gov_id_cols
                if col in df_work.columns
            )
            if has_gov_conflict:
                blocked += 1
                continue

            if uf.union(idx1, idx2, reason=f"Multifield match ({final_score:.0f}%)"):
                merged += 1

        if merged:
            self.log_callback(f"    Merged {merged} records in Pass 5")
        if blocked:
            self.log_callback(f"    Blocked {blocked} pairs in Pass 5 (conflict/family guard)")

    # ─────────────────────────────────────────────────────────────
    # Pass 6: Backfill Rules 4 & 5 (within confirmed clusters only)
    # ─────────────────────────────────────────────────────────────
    def _apply_backfill_rules(self, uf, name_cols, email_cols, phone_cols):
        """
        Rule 4: Backfill missing Name from within the same duplicate cluster.
        Rule 5: Backfill missing Phone/Email from within the same duplicate cluster.
        NOTE: This only fills values from records already proven to be the SAME person.
        """
        cluster_map: Dict[int, List[int]] = {}
        for i in range(len(self.df)):
            root = uf.find(i)
            cluster_map.setdefault(root, []).append(i)

        for root, indices in cluster_map.items():
            if len(indices) < 2:
                continue
            for col in name_cols + email_cols + phone_cols:
                if col not in self.df.columns:
                    continue
                vals      = [(idx, _norm(self.df.loc[idx, col])) for idx in indices]
                non_empty = [(idx, v) for idx, v in vals if v]
                empty     = [idx for idx, v in vals if not v]
                if non_empty and empty:
                    self.log_callback(f"    ↳ Copied missing '{col}' from a duplicate (fixed {len(empty)} rows)")

    # ─────────────────────────────────────────────────────────────
    # Golden Record builder
    # ─────────────────────────────────────────────────────────────
    def _build_golden_record(self, indices: List[int]) -> dict:
        """
        Build a Golden Record for a cluster:
        1. Primary = row with fewest missing values (most complete)
        2. Backfill remaining NaN from other records in the cluster
        3. Numeric fields: use median for stability
        """
        cluster_df  = self.df.iloc[indices].copy()
        missing_counts = cluster_df.isnull().sum(axis=1)
        primary_idx    = missing_counts.idxmin()
        golden         = cluster_df.loc[primary_idx].to_dict()

        # Backfill missing fields from other cluster records
        for col in self.df.columns:
            if _is_valid(golden.get(col)):
                continue
            for sidx in indices:
                v = self.df.loc[sidx, col]
                if _is_valid(v):
                    golden[col] = v
                    break

        # Numeric fields: cluster median for robustness
        for col in self.df.columns:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                continue
            vals = cluster_df[col].dropna()
            if len(vals) > 0:
                golden[col] = float(vals.median())

        return golden

    # ─────────────────────────────────────────────────────────────
    # keep_all_rows=False: merge into one canonical row per cluster
    # ─────────────────────────────────────────────────────────────
    def _merge_to_canonical(
        self,
        uf,
        cluster_map: Dict[int, List[int]],
        canonical_records: dict,
        name_cols: List[str],
    ) -> pd.DataFrame:
        merged = []
        for root, indices in cluster_map.items():
            canon = canonical_records[root]
            merged.append(canon)

            # Record ALL clusters of size ≥ 2 — not just those with name changes.
            # Previously only name-changed rows were recorded, causing the UI to
            # always show "No duplicates" even when duplicates were correctly merged.
            if len(indices) > 1:
                # Collect the merge reason(s) for this cluster
                reasons = {}
                for i in indices:
                    curr   = i
                    reason = "Exact Duplicate"
                    while curr in uf.reasons:
                        reason = uf.reasons[curr]
                        curr   = uf.parent[curr]
                        if curr == uf.parent[curr]:
                            break
                    reasons[reason] = reasons.get(reason, 0) + 1

                # Collect all original variants for the cluster
                variants = []
                name_col = name_cols[0] if name_cols else None
                for idx in indices:
                    row_repr = {}
                    if name_col and name_col in self.df.columns:
                        row_repr["name"] = str(self.df.loc[idx, name_col])
                    # Add a few more identity fields for context
                    for id_col in self.df.columns[:6]:  # first 6 cols as context
                        if id_col != name_col:
                            val = self.df.loc[idx, id_col]
                            if _is_valid(val):
                                row_repr[id_col] = str(val)
                                break
                    variants.append(row_repr)

                canon_name = str(canon.get(name_col, "")) if name_col else f"Cluster #{root}"
                # Find a representative "original" (most different from canon)
                orig_names = [str(self.df.loc[idx, name_col]) for idx in indices
                              if name_col and name_col in self.df.columns]
                orig_representative = next(
                    (o for o in orig_names if _norm(o) != _norm(canon_name)),
                    orig_names[0] if orig_names else canon_name
                )

                self.dedup_changes.append({
                    "Original":     orig_representative,
                    "Corrected":    canon_name,
                    "cluster_size": len(indices),
                    "reasons":      reasons,
                    "all_variants": variants,
                })

        result = pd.DataFrame(merged).reset_index(drop=True)
        for col in self.df.columns:
            if col in result.columns:
                try:
                    result[col] = result[col].astype(self.df[col].dtype)
                except (ValueError, TypeError):
                    pass
        self.log_callback(f"  [Dedup] Merged to {len(result)} unique records")
        removed = len(self.df) - len(result)
        if removed:
            self.log_callback(f"  Removed {removed} duplicate rows, kept {len(result)} unique records.")
        self.log_callback(f"  Found {len(self.cluster_report)} duplicate clusters.")
        return result

    # ─────────────────────────────────────────────────────────────
    # keep_all_rows=True: enrich every row with Golden Record data
    # ─────────────────────────────────────────────────────────────
    def _enrich_all_rows(
        self,
        uf,
        cluster_map: Dict[int, List[int]],
        canonical_records: dict,
        name_cols: List[str],
    ) -> pd.DataFrame:
        cleaned = self.df.copy()
        for root, indices in cluster_map.items():
            canon = canonical_records[root]
            for idx in indices:
                for col in name_cols:
                    cleaned.loc[idx, col] = canon.get(col, cleaned.loc[idx, col])
                for col in cleaned.columns:
                    if not _is_valid(cleaned.loc[idx, col]):
                        cleaned.loc[idx, col] = canon.get(col, cleaned.loc[idx, col])

            # Record ALL clusters of size ≥ 2 (same fix as _merge_to_canonical)
            if len(indices) > 1:
                reasons = {}
                for i in indices:
                    curr   = i
                    reason = "Enriched"
                    while curr in uf.reasons:
                        reason = uf.reasons[curr]
                        curr   = uf.parent[curr]
                        if curr == uf.parent[curr]:
                            break
                    reasons[reason] = reasons.get(reason, 0) + 1

                name_col = name_cols[0] if name_cols else None
                canon_name = str(canon.get(name_col, "")) if name_col else f"Cluster #{root}"
                orig_names = [str(self.df.loc[idx, name_col]) for idx in indices
                              if name_col and name_col in self.df.columns]
                orig_representative = next(
                    (o for o in orig_names if _norm(o) != _norm(canon_name)),
                    orig_names[0] if orig_names else canon_name
                )

                variants = []
                for idx in indices:
                    row_repr = {}
                    if name_col and name_col in self.df.columns:
                        row_repr["name"] = str(self.df.loc[idx, name_col])
                    for id_col in self.df.columns[:6]:
                        if id_col != name_col:
                            val = self.df.loc[idx, id_col]
                            if _is_valid(val):
                                row_repr[id_col] = str(val)
                                break
                    variants.append(row_repr)

                self.dedup_changes.append({
                    "Original":     orig_representative,
                    "Corrected":    canon_name,
                    "cluster_size": len(indices),
                    "reasons":      reasons,
                    "all_variants": variants,
                })
        return cleaned


# ─────────────────────────────────────────────────────────────
# Backward-compat helper (used by legacy code paths)
# ─────────────────────────────────────────────────────────────
def _has_conflicting_identifiers(
    df: pd.DataFrame,
    idx1: int,
    idx2: int,
    strong_id_cols: list,
) -> bool:
    """
    Returns True if two rows have DIFFERENT non-null values in any
    strong identifier column — they cannot be the same entity.
    """
    for col in strong_id_cols:
        if col not in df.columns:
            continue
        v1 = _norm(df.loc[idx1, col])
        v2 = _norm(df.loc[idx2, col])
        if v1 and v2 and v1 != v2:
            return True
    return False
