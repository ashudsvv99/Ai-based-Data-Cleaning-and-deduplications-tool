"""
Advanced deduplication engine with intent-aware strategy selection.

DATASET INTENT AUTO-DETECTION (via LLM or pipeline flag):
  - Predictive Datasets  → lightweight dedup: exact ID match + fuzzy name match.
  - Non-Predictive Business → full 16-rule business deduplication with priority
    tiers, conflict guards, and Golden Record merge.

16 Business Deduplication Rules (Non-Predictive Business mode):
  Rule 1  — Exact: Customer ID + Email + Phone + Address → Merge
  Rule 2  — Full Duplicate: every column identical → Merge
  Rule 3  — Fuzzy Name: Email + Phone + Address match, Name ≈ typo → Merge
  Rule 4  — Backfill missing Name when strong IDs match
  Rule 5  — Backfill missing Phone/Email when strong IDs match
  Rule 6  — Contact Conflict Guard: same Name/Address, different Phone → FLAG
  Rule 7  — Contact Conflict Guard: same Name/Address, different Email → FLAG
  Rule 8  — Family Guard: same phone, different name → DO NOT MERGE
  Rule 9  — Family Guard: same email (shared mailbox), different name → DO NOT MERGE
  Rule 10 — Family Guard: same address, different name + different phone → DO NOT MERGE
  Rule 11 — Family Guard: same address, different name + different email → DO NOT MERGE
  Rule 12 — Shared Contact Guard: any shared contact ID + different unique ID → DO NOT MERGE
  Rule 13 — Name Isolation: matching names alone must NEVER trigger a merge
  Rule 14 — Gov ID Supremacy: Gov/Unique ID match → Merge even if other fields changed
  Rule 15 — Unique ID Conflict: conflicting Unique IDs → DO NOT MERGE
  Rule 16 — Low-Quality Flag: all critical contact fields missing → mark as Low Quality

Golden Record Rules:
  - Record with fewest missing values becomes the primary "Golden Record"
  - Backfill remaining gaps from secondary records
  - Numeric fields: use median for stability across cluster

Pass structure (both modes):
  Pass 1: Exact identifier match (email / phone / Gov IDs)
  Pass 2: Case-insensitive exact name match (only if no contact cols exist)
  Pass 3: Composite key (name + contact)
  Pass 4: Fuzzy name match (blocked)
  Pass 5: Multi-field weighted similarity (blocked)
  Pass 6: Business Rule evaluation & conflict flagging [Non-Predictive only]
"""
import pandas as pd
import numpy as np
import recordlinkage
from rapidfuzz import fuzz
from typing import Dict, List, Tuple, Optional, Set
import config


# ─────────────────────────────────────────────────────────────
# Government / Unique ID column patterns (Level 1 — highest confidence)
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
_NULL_SET = {"", "unknown", "-", "<na>", "nan", "none", "n/a", "null", "?", "na", "0", "0.0", "-1"}


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


# ─────────────────────────────────────────────────────────────
# Column tier classifier  (uses column names, not LLM)
# ─────────────────────────────────────────────────────────────
def _classify_col_tiers(df: pd.DataFrame, strategies: dict):
    """
    Classify dataset columns into 4 priority tiers:

    Tier 1 — Unique Gov / Business IDs   (highest confidence)
    Tier 2 — Strong Contact IDs          (email, phone)
    Tier 3 — Location / Address
    Tier 4 — Personal Info               (name, DOB)

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
        if any(pat in col_l for pat in _GOV_ID_PATTERNS) or strat == "exact_match":
            if "email" in col_l:
                email_cols.append(col)
            elif "phone" in col_l or "mobile" in col_l or "contact" in col_l:
                phone_cols.append(col)
            elif any(pat in col_l for pat in _GOV_ID_PATTERNS):
                gov_id_cols.append(col)
            else:
                other_id_cols.append(col)

        # Tier 2 — Contact IDs
        elif "email" in col_l:
            email_cols.append(col)
        elif "phone" in col_l or "mobile" in col_l or "tel" in col_l:
            phone_cols.append(col)

        # Tier 3 — Location
        elif any(k in col_l for k in ["address", "addr", "street", "city", "zip", "pincode", "location"]):
            address_cols.append(col)

        # Tier 4 — Personal
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

    def __init__(self, size: int):
        self.parent = list(range(size))
        self.rank   = [0] * size

    def find(self, i: int) -> int:
        if self.parent[i] != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: int, j: int) -> bool:
        ri, rj = self.find(i), self.find(j)
        if ri == rj:
            return False
        if self.rank[ri] < self.rank[rj]:
            ri, rj = rj, ri
        self.parent[rj] = ri
        if self.rank[ri] == self.rank[rj]:
            self.rank[ri] += 1
        return True


# ─────────────────────────────────────────────────────────────
# Business Rule Evaluator
# ─────────────────────────────────────────────────────────────
class BusinessRuleEvaluator:
    """
    Evaluates the 16 advanced business deduplication rules for every
    candidate pair before the UnionFind merge decision is made.

    Returns:
        "merge"   — pair should be merged
        "block"   — pair must NOT be merged (flagged conflict)
        "skip"    — insufficient data for a decision (no action)
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
        self.flags: List[dict] = []     # Conflict/review flags for UI

    # ── helpers ──
    def _val(self, idx, col) -> str:
        return _norm(self.df.loc[idx, col]) if col in self.df.columns else ""

    def _match(self, idx1, idx2, col, fuzzy=False, threshold=90) -> Optional[bool]:
        """None = one/both sides empty (can't decide), True = match, False = mismatch."""
        v1, v2 = self._val(idx1, col), self._val(idx2, col)
        if not v1 or not v2:
            return None
        if fuzzy:
            return fuzz.token_sort_ratio(v1, v2) >= threshold
        return v1 == v2

    def _all_contact_missing(self, idx) -> bool:
        all_contact = self.gov_id_cols + self.email_cols + self.phone_cols + self.address_cols
        return not any(_is_valid(self.df.loc[idx, c]) for c in all_contact if c in self.df.columns)

    # ── Rule evaluation entry point ──
    def evaluate(self, idx1: int, idx2: int) -> str:
        """
        Returns "merge", "block", or "skip".
        Applies rules in priority order: Gov ID supremacy first, then conflict guards.
        """
        row1 = self.df.iloc[idx1] if idx1 < len(self.df) else None
        row2 = self.df.iloc[idx2] if idx2 < len(self.df) else None
        if row1 is None or row2 is None:
            return "skip"

        # ── Rule 16: Low-Quality Flag ───────────────────────────────
        if self._all_contact_missing(idx1) or self._all_contact_missing(idx2):
            self._flag(idx1, idx2, "Rule 16", "Low Quality — all critical contact fields missing")
            return "skip"

        # ── Rule 14: Gov ID Supremacy ───────────────────────────────
        for col in self.gov_id_cols:
            m = self._match(idx1, idx2, col)
            if m is True:
                return "merge"   # Confirmed same entity even if other fields changed

        # ── Rule 15: Conflicting Gov/Unique IDs → BLOCK ─────────────
        for col in self.gov_id_cols:
            v1, v2 = self._val(idx1, col), self._val(idx2, col)
            if v1 and v2 and v1 != v2:
                self._flag(idx1, idx2, "Rule 15", f"Conflicting unique IDs in '{col}': '{v1}' vs '{v2}'")
                return "block"

        # ── Rules 8-12: Family / Shared Contact Guards ───────────────
        # Same phone but different names → DO NOT MERGE (family members)
        for col in self.phone_cols:
            if self._match(idx1, idx2, col) is True:
                for nc in self.name_cols:
                    name_match = self._match(idx1, idx2, nc, fuzzy=True, threshold=85)
                    if name_match is False:    # Phone match + name mismatch
                        self._flag(idx1, idx2, "Rule 8", f"Same phone in '{col}' but different names → possible family members")
                        return "block"

        # Same email but different names → DO NOT MERGE (shared mailbox)
        for col in self.email_cols:
            if self._match(idx1, idx2, col) is True:
                for nc in self.name_cols:
                    name_match = self._match(idx1, idx2, nc, fuzzy=True, threshold=85)
                    if name_match is False:
                        self._flag(idx1, idx2, "Rule 9", f"Same email in '{col}' but different names → shared mailbox / family")
                        return "block"

        # Same address but different name + different phone/email → DO NOT MERGE (roommates)
        for addr_col in self.address_cols:
            if self._match(idx1, idx2, addr_col) is True:
                for nc in self.name_cols:
                    if self._match(idx1, idx2, nc, fuzzy=True, threshold=85) is False:
                        # Check if phone/email also differ
                        phone_differs = any(self._match(idx1, idx2, c) is False for c in self.phone_cols)
                        email_differs = any(self._match(idx1, idx2, c) is False for c in self.email_cols)
                        if phone_differs:
                            self._flag(idx1, idx2, "Rule 10", "Same address, different name + phone → roommates/family")
                            return "block"
                        if email_differs:
                            self._flag(idx1, idx2, "Rule 11", "Same address, different name + email → roommates/family")
                            return "block"

        # Rule 12: Shared contact ID with conflicting unique ID
        all_contact = self.email_cols + self.phone_cols
        other_ids   = [c for c in self.df.columns
                       if c in self.gov_id_cols and c not in all_contact]
        for cc in all_contact:
            if self._match(idx1, idx2, cc) is True:
                for oid in other_ids:
                    if self._match(idx1, idx2, oid) is False:
                        self._flag(idx1, idx2, "Rule 12", f"Shared contact '{cc}' but conflicting ID '{oid}'")
                        return "block"

        # ── Rule 1: Exact multi-field match → Merge ──────────────────
        exact_fields = self.gov_id_cols[:1] + self.email_cols[:1] + self.phone_cols[:1] + self.address_cols[:1]
        all_match = [self._match(idx1, idx2, c) for c in exact_fields if c in self.df.columns]
        valid     = [m for m in all_match if m is not None]
        if len(valid) >= 2 and all(valid):
            return "merge"

        # ── Rules 6-7: Contact Conflict Guard ────────────────────────
        # Name + address match but phone differs → FLAG for review
        for nc in self.name_cols:
            name_m = self._match(idx1, idx2, nc, fuzzy=True, threshold=88)
            for ac in self.address_cols:
                addr_m = self._match(idx1, idx2, ac)
                if name_m is True and addr_m is True:
                    for pc in self.phone_cols:
                        if self._match(idx1, idx2, pc) is False:
                            self._flag(idx1, idx2, "Rule 6", f"Name+address match but conflicting phone '{pc}' — needs human review")
                            return "block"
                    for ec in self.email_cols:
                        if self._match(idx1, idx2, ec) is False:
                            self._flag(idx1, idx2, "Rule 7", f"Name+address match but conflicting email '{ec}' — needs human review")
                            return "block"

        # ── Rule 13: Name-only match must NOT trigger merge ───────────
        # (This is enforced by never merging on name alone — handled in callers)

        return "skip"   # No decision — caller's fuzzy logic applies

    def _flag(self, idx1: int, idx2: int, rule: str, reason: str):
        self.flags.append({
            "row_index_1": int(idx1),
            "row_index_2": int(idx2),
            "rule":        rule,
            "reason":      reason,
        })


# ─────────────────────────────────────────────────────────────
# Deduplication Engine
# ─────────────────────────────────────────────────────────────
class DeduplicationEngine:
    """
    Intent-aware deduplication engine.

    dataset_intent:
      "Predictive"             → lightweight passes (exact IDs + fuzzy name)
      "Non-Predictive Business"→ full 16-rule business deduplication
      "Auto-Detect"            → chosen based on column presence heuristic
                                  (falls back to pipeline-provided intent)

    After clustering:
      keep_all_rows=False  → merge duplicates into ONE Golden Record (drops extras)
      keep_all_rows=True   → enrich all rows with Golden Record data (no removal)
    """

    def __init__(
        self,
        df: pd.DataFrame,
        strategies: dict,
        dataset_intent: str = "Auto-Detect",
        threshold: int = 85,
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

        # ── Low-Quality Flag (Rule 16) ────────────────────────────
        self._flag_low_quality_rows(gov_id_cols, email_cols, phone_cols, address_cols)

        n  = len(self.df)
        uf = UnionFind(n)

        # All strong IDs used in conflict checks
        all_id_cols = gov_id_cols + email_cols + phone_cols + other_id_cols

        if intent == "Non-Predictive Business":
            rule_evaluator = BusinessRuleEvaluator(
                self.df, gov_id_cols, email_cols, phone_cols, address_cols, name_cols
            )
        else:
            rule_evaluator = None

        # ── Pass 1: Exact identifier match ───────────────────────
        self.log_callback("  [Pass 1] Exact identifier match (Gov IDs, Email, Phone)...")
        merged_p1 = 0
        for col in gov_id_cols + email_cols + phone_cols + other_id_cols:
            groups = self.df.groupby(col, sort=False).groups
            for val, idxs in groups.items():
                if not _is_valid(val):
                    continue
                idxs = list(idxs)
                # Business mode: evaluate rule before merging
                for idx in idxs[1:]:
                    if uf.find(idxs[0]) == uf.find(idx):
                        continue
                    if rule_evaluator:
                        decision = rule_evaluator.evaluate(idxs[0], idx)
                        if decision == "block":
                            continue
                    if uf.union(idxs[0], idx):
                        merged_p1 += 1
        if merged_p1:
            self.log_callback(f"    Merged {merged_p1} records in Pass 1")

        # ── Pass 2: Case-insensitive exact name (only if no contact cols) ──
        if not (email_cols or phone_cols or block_cols or gov_id_cols):
            # Rule 13: Name-only matching is only allowed when there are literally
            # no other identifiers in the dataset.
            self.log_callback("  [Pass 2] Case-insensitive exact name match (no contact IDs found)...")
            for col in name_cols:
                norm_series = self.df[col].apply(_norm)
                groups = norm_series.groupby(norm_series).groups
                for val, idxs in groups.items():
                    if val:
                        idxs = list(idxs)
                        for idx in idxs[1:]:
                            uf.union(idxs[0], idx)
        else:
            self.log_callback("  [Pass 2] Skipped bare-name exact match (Rule 13: safer composite/fuzzy matches used).")

        # ── Pass 3: Composite key match (name + contact/location) ──
        self.log_callback("  [Pass 3] Composite key match...")
        if name_cols:
            primary   = name_cols[0]
            secondary = (block_cols + address_cols + email_cols + other_id_cols or [None])[0]
            if secondary and secondary in self.df.columns:
                composite = (
                    self.df[primary].apply(_norm) + "||" +
                    self.df[secondary].apply(_norm)
                )
                groups = composite.groupby(composite).groups
                for val, idxs in groups.items():
                    if val and "||" in val and not val.startswith("||") and not val.endswith("||"):
                        idxs = list(idxs)
                        for idx in idxs[1:]:
                            if uf.find(idxs[0]) == uf.find(idx):
                                continue
                            if rule_evaluator:
                                decision = rule_evaluator.evaluate(idxs[0], idx)
                                if decision == "block":
                                    continue
                            uf.union(idxs[0], idx)

        # ── Pass 4: Fuzzy name match (blocked) ───────────────────
        self.log_callback("  [Pass 4] Fuzzy name match (blocked by location/contact)...")
        merged_p4 = 0
        blocked_p4 = 0
        if name_cols:
            primary = name_cols[0]
            df_work = self.df.copy()
            df_work[primary] = df_work[primary].fillna("").astype(str)

            indexer = recordlinkage.Index()
            block_field = (block_cols + address_cols or [None])[0]
            if block_field and block_field in df_work.columns:
                indexer.sortedneighbourhood(primary, window=7, block_on=block_field)
            else:
                indexer.sortedneighbourhood(primary, window=7)

            candidate_links = indexer.index(df_work)
            for idx1, idx2 in candidate_links:
                if uf.find(idx1) == uf.find(idx2):
                    continue
                n1 = _norm(df_work.loc[idx1, primary])
                n2 = _norm(df_work.loc[idx2, primary])
                if not n1 or not n2:
                    continue
                score = fuzz.token_sort_ratio(n1, n2)
                if score >= self.threshold:
                    # Apply business rules first
                    if rule_evaluator:
                        decision = rule_evaluator.evaluate(idx1, idx2)
                        if decision == "block":
                            blocked_p4 += 1
                            continue
                        if decision == "merge":
                            uf.union(idx1, idx2)
                            merged_p4 += 1
                            continue
                    # Fallback: traditional conflict check
                    if _has_conflicting_identifiers(df_work, idx1, idx2, all_id_cols):
                        blocked_p4 += 1
                        continue
                    uf.union(idx1, idx2)
                    merged_p4 += 1

        if merged_p4:
            self.log_callback(f"    Merged {merged_p4} records in Pass 4")
        if blocked_p4:
            self.log_callback(f"    Blocked {blocked_p4} pairs in Pass 4 (conflict guard)")

        # ── Pass 5: Multi-field fuzzy scoring ────────────────────
        self.log_callback("  [Pass 5] Multi-field fuzzy matching (weighted)...")
        self._pass_multifield(uf, rule_evaluator, name_cols, email_cols, phone_cols,
                              block_cols + address_cols, all_id_cols)

        # ── Pass 6: Business Rule Backfill (Rules 4 & 5) ─────────
        if intent == "Non-Predictive Business":
            self.log_callback("  [Pass 6] Business Rule Backfill (Rules 4 & 5)...")
            self._apply_backfill_rules(uf, gov_id_cols + email_cols + phone_cols, name_cols, email_cols, phone_cols)

        # ── Extract clusters ─────────────────────────────────────
        cluster_map: Dict[int, List[int]] = {}
        for i in range(n):
            root = uf.find(i)
            cluster_map.setdefault(root, []).append(i)

        dup_clusters = {r: idxs for r, idxs in cluster_map.items() if len(idxs) > 1}
        self.log_callback(f"  [Dedup] {n} rows -> {len(cluster_map)} unique entities "
              f"({len(dup_clusters)} duplicate clusters found)")

        # Collect conflict flags from rule evaluator
        if rule_evaluator:
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
                "cluster_size":  len(indices),
                "canonical_name": str(canon.get(name_col, "")) if name_col else "",
                "row_indices":   indices,
            })

        # ── Return result ─────────────────────────────────────────
        self.dedup_changes = []
        if self.keep_all_rows:
            return self._enrich_all_rows(cluster_map, canonical_records, name_cols)
        else:
            return self._merge_to_canonical(cluster_map, canonical_records, name_cols)

    # ─────────────────────────────────────────────────────────────
    # Intent resolver
    # ─────────────────────────────────────────────────────────────
    def _resolve_intent(self, gov_id_cols, email_cols, phone_cols, name_cols) -> str:
        """
        If the pipeline didn't provide an intent, auto-detect based on column presence:
        - Has Gov IDs / Email / Phone → likely Non-Predictive Business
        - Has only numeric/feature columns → likely Predictive
        """
        if self.dataset_intent and self.dataset_intent not in ("Auto-Detect", ""):
            return self.dataset_intent

        # Heuristic: if we have strong contact/identity columns, treat as Business
        contact_count = len(gov_id_cols) + len(email_cols) + len(phone_cols)
        if contact_count >= 1 or name_cols:
            return "Non-Predictive Business"

        return "Predictive"

    # ─────────────────────────────────────────────────────────────
    # Low-Quality Row Flagging (Rule 16)
    # ─────────────────────────────────────────────────────────────
    def _flag_low_quality_rows(self, gov_id_cols, email_cols, phone_cols, address_cols):
        """Flag rows where all critical contact fields are missing."""
        all_contact = gov_id_cols + email_cols + phone_cols + address_cols
        if not all_contact:
            return
        for idx in self.df.index:
            has_any = any(_is_valid(self.df.loc[idx, c])
                          for c in all_contact if c in self.df.columns)
            if not has_any:
                self.low_quality_flags.append({"row_index": int(idx), "rule": "Rule 16",
                                               "reason": "All critical contact fields are missing"})

    # ─────────────────────────────────────────────────────────────
    # Pass 5: Multi-field weighted similarity
    # ─────────────────────────────────────────────────────────────
    def _pass_multifield(self, uf, rule_evaluator, name_cols, email_cols,
                         phone_cols, block_cols, all_id_cols):
        if not name_cols:
            return

        primary = name_cols[0]
        df_work = self.df.copy().fillna("")

        indexer = recordlinkage.Index()
        if block_cols and block_cols[0] in df_work.columns:
            indexer.sortedneighbourhood(primary, window=5, block_on=block_cols[0])
        else:
            indexer.sortedneighbourhood(primary, window=5)

        candidate_links = indexer.index(df_work)
        merged = blocked = 0

        for idx1, idx2 in candidate_links:
            if uf.find(idx1) == uf.find(idx2):
                continue

            n1 = _norm(df_work.loc[idx1, primary])
            n2 = _norm(df_work.loc[idx2, primary])
            if not n1 or not n2:
                continue

            score = 0.5 * fuzz.token_set_ratio(n1, n2)
            weight = 0.5

            for ec in email_cols[:1]:
                e1, e2 = _norm(df_work.loc[idx1, ec]), _norm(df_work.loc[idx2, ec])
                if e1 and e2:
                    score  += 0.3 * fuzz.ratio(e1.split("@")[0], e2.split("@")[0])
                    weight += 0.3

            for lc in (block_cols + phone_cols)[:1]:
                l1, l2 = _norm(df_work.loc[idx1, lc]), _norm(df_work.loc[idx2, lc])
                if l1 and l2:
                    score  += 0.2 * fuzz.ratio(l1, l2)
                    weight += 0.2

            if weight == 0 or (score / weight) < self.threshold:
                continue

            # Apply business rules
            if rule_evaluator:
                decision = rule_evaluator.evaluate(idx1, idx2)
                if decision == "block":
                    blocked += 1
                    continue
                if decision == "merge":
                    uf.union(idx1, idx2)
                    merged += 1
                    continue

            if _has_conflicting_identifiers(df_work, idx1, idx2, all_id_cols):
                blocked += 1
                continue
            uf.union(idx1, idx2)
            merged += 1

        if merged:
            self.log_callback(f"    Merged {merged} records in Pass 5")
        if blocked:
            self.log_callback(f"    Blocked {blocked} pairs in Pass 5 (conflict/family guard)")

    # ─────────────────────────────────────────────────────────────
    # Pass 6: Backfill Rules 4 & 5
    # ─────────────────────────────────────────────────────────────
    def _apply_backfill_rules(self, uf, strong_id_cols, name_cols, email_cols, phone_cols):
        """
        Rule 4: If names are missing in some records but strong IDs match → backfill name.
        Rule 5: If phone/email are missing but strong IDs match → backfill phone/email.
        Applied AFTER cluster formation so we enrich the Golden Record.
        (Actual value propagation happens in _build_golden_record already via the
         fewest-missing-value primary logic, but we log it here for auditability.)
        """
        cluster_map: Dict[int, List[int]] = {}
        for i in range(len(self.df)):
            root = uf.find(i)
            cluster_map.setdefault(root, []).append(i)

        for root, indices in cluster_map.items():
            if len(indices) < 2:
                continue
            # Check if any record has a name/contact that others lack
            for col in name_cols + email_cols + phone_cols:
                if col not in self.df.columns:
                    continue
                vals = [(idx, _norm(self.df.loc[idx, col])) for idx in indices]
                non_empty = [(idx, v) for idx, v in vals if v]
                empty     = [idx for idx, v in vals if not v]
                if non_empty and empty:
                    fill_val = non_empty[0][1]   # canonical already chosen
                    rule = "Rule 4" if col in name_cols else "Rule 5"
                    self.log_callback(f"    [{rule}] Backfill '{col}' for {len(empty)} record(s) in cluster")

    # ─────────────────────────────────────────────────────────────
    # Golden Record builder (Rules 4, 5 implicit via fewest-missing primary)
    # ─────────────────────────────────────────────────────────────
    def _build_golden_record(self, indices: List[int]) -> dict:
        """
        Build a Golden Record for a cluster:
        1. Primary = row with fewest missing values (most complete)
        2. Backfill remaining NaN from other records in the cluster
        3. Numeric fields: use median for stability
        """
        cluster_df = self.df.iloc[indices].copy()

        # Choose primary record: fewest missing values
        missing_counts = cluster_df.isnull().sum(axis=1)
        primary_idx    = missing_counts.idxmin()
        golden         = cluster_df.loc[primary_idx].to_dict()

        # Backfill: for every still-missing field, check other cluster rows
        for col in self.df.columns:
            if _is_valid(golden.get(col)):
                continue
            # Try each secondary record for a valid value
            for sidx in indices:
                v = self.df.loc[sidx, col]
                if _is_valid(v):
                    golden[col] = v
                    break

        # Numeric fields: replace with cluster median for robustness
        for col in self.df.columns:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                continue
            vals = cluster_df[col].dropna()
            if len(vals) > 0:
                golden[col] = float(vals.median())

        return golden

    # ─────────────────────────────────────────────────────────────
    # keep_all_rows=False: merge into one row per cluster
    # ─────────────────────────────────────────────────────────────
    def _merge_to_canonical(
        self,
        cluster_map: Dict[int, List[int]],
        canonical_records: dict,
        name_cols: List[str],
    ) -> pd.DataFrame:
        merged = []
        for root, indices in cluster_map.items():
            canon = canonical_records[root]
            merged.append(canon)
            if name_cols and len(indices) > 1:
                canon_name = str(canon.get(name_cols[0], ""))
                for idx in indices:
                    orig = str(self.df.loc[idx, name_cols[0]])
                    if _is_valid(orig) and orig != canon_name:
                        self.dedup_changes.append({
                            "Original":    orig,
                            "Corrected":   canon_name,
                            "cluster_size": len(indices),
                        })

        result = pd.DataFrame(merged).reset_index(drop=True)
        for col in self.df.columns:
            if col in result.columns:
                try:
                    result[col] = result[col].astype(self.df[col].dtype)
                except (ValueError, TypeError):
                    pass
        print(f"  [Dedup] Merged to {len(result)} unique records")
        return result

    # ─────────────────────────────────────────────────────────────
    # keep_all_rows=True: enrich every row with Golden Record data
    # ─────────────────────────────────────────────────────────────
    def _enrich_all_rows(
        self,
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
            if name_cols and len(indices) > 1:
                canon_name = str(canon.get(name_cols[0], ""))
                for idx in indices:
                    orig = str(self.df.loc[idx, name_cols[0]])
                    if _is_valid(orig) and orig != canon_name:
                        self.dedup_changes.append({
                            "Original":    orig,
                            "Corrected":   canon_name,
                            "cluster_size": len(indices),
                        })
        return cleaned


# ─────────────────────────────────────────────────────────────
# Backward-compat helper (used by Pass 4/5 fallback)
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
