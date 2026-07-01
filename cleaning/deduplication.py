"""
Advanced deduplication engine with 5-pass detection strategy:
    Pass 1: Exact match on unique identifiers (email, phone, ID)
    Pass 2: Normalised exact match (case-insensitive, strip whitespace)
    Pass 3: Composite key match (name + one other field)
    Pass 4: Transliterated fuzzy name match (multi-language)
    Pass 5: Multi-field fuzzy similarity (weighted scoring)

All duplicate clusters are consolidated into a single canonical
record using field-level consensus logic.
Tracks dedup_changes and cluster_report for full UI auditability.
"""
import pandas as pd
import numpy as np
import recordlinkage
from rapidfuzz import fuzz
from typing import Dict, List, Tuple, Optional
import config


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
            self.parent[i] = self.find(self.parent[i])   # path compression
        return self.parent[i]

    def union(self, i: int, j: int) -> bool:
        ri, rj = self.find(i), self.find(j)
        if ri == rj:
            return False
        # Union by rank
        if self.rank[ri] < self.rank[rj]:
            ri, rj = rj, ri
        self.parent[rj] = ri
        if self.rank[ri] == self.rank[rj]:
            self.rank[ri] += 1
        return True


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
_NULL_SET = {"", "unknown", "-", "<na>", "nan", "none", "n/a", "null", "?", "na", "0", "0.0", "-1"}
def _is_valid(x):
    if pd.isna(x):
        return False
    s = str(x).strip().lower()
    return bool(s) and s not in _NULL_SET


def _norm(x):
    if pd.isna(x):
        return ""
    s = str(x).strip().lower()
    if s in _NULL_SET:
        return ""
    return s


# ─────────────────────────────────────────────────────────────
# Deduplication Engine
# ─────────────────────────────────────────────────────────────
class DeduplicationEngine:
    """
    5-pass deduplication engine using Union-Find graph clustering.

    Passes (in order of strictness):
      1. Exact identifier match   — email / phone / ID columns
      2. Case-insensitive exact   — same value ignoring case/spaces
      3. Composite key match      — name + location or name + email prefix
      4. Transliterated fuzzy     — after multilingual normalisation
      5. Multi-field fuzzy score  — weighted average across multiple fields

    After clustering:
      - keep_all_rows=False  → merge duplicates into ONE canonical record (drops extras)
      - keep_all_rows=True   → enrich all rows with canonical data (no row removal)
    """

    def __init__(self, df: pd.DataFrame, strategies: dict, threshold: int = 85, keep_all_rows: bool = False, log_callback=print):
        self.df = df.copy()
        self.strategies = strategies
        self.threshold = threshold
        self.keep_all_rows = keep_all_rows
        self.log_callback = log_callback
        self.dedup_changes: List[dict] = []
        self.cluster_report: List[dict] = []

    # ─────────────────────────────────────────────────────────────
    def execute(self) -> pd.DataFrame:
        self.log_callback("─── Deduplication & Identity Resolution ───")

        self.df = self.df.reset_index(drop=True)
        if len(self.df) < 2:
            return self.df

        n  = len(self.df)
        uf = UnionFind(n)

        # Classify columns by dedup strategy
        id_cols    = [c for c, s in self.strategies.items()
                      if s == "exact_match" and c in self.df.columns]
        name_cols  = [c for c, s in self.strategies.items()
                      if s == "fuzzy_name" and c in self.df.columns]
        block_cols = [c for c, s in self.strategies.items()
                      if s == "blocking_key" and c in self.df.columns]
        email_cols = [c for c in id_cols if "email" in c.lower()]
        phone_cols = [c for c in id_cols
                      if "phone" in c.lower() or "mobile" in c.lower()]
        # other exact-match IDs (account_number, patient_id, etc.)
        other_id_cols = [c for c in id_cols
                         if c not in email_cols and c not in phone_cols]

        # ── Pass 1: Exact identifier match ──────────────────────
        self.log_callback("  [Pass 1] Exact identifier match...")
        for col in email_cols + phone_cols + other_id_cols:
            groups = self.df.groupby(col, sort=False).groups
            for val, idxs in groups.items():
                if _is_valid(val):
                    first = idxs[0]
                    for idx in idxs[1:]:
                        uf.union(first, idx)

        # ── Pass 2: Case-insensitive exact match on names ────────
        # Merging purely on name is dangerous if we have corroborating fields (email, city)
        # because we might merge two different users with the same common name.
        if not (email_cols or phone_cols or block_cols):
            self.log_callback("  [Pass 2] Case-insensitive exact match on name...")
            for col in name_cols:
                norm_series = self.df[col].apply(_norm)
                groups      = norm_series.groupby(norm_series).groups
                for val, idxs in groups.items():
                    if val:
                        idxs = list(idxs)
                        for idx in idxs[1:]:
                            uf.union(idxs[0], idx)
        else:
            self.log_callback("  [Pass 2] Skipped bare-name exact match (relying on safer composite/fuzzy matches).")

        # ── Pass 3: Composite key match (name + location/email) ──
        self.log_callback("  [Pass 3] Composite key match...")
        if name_cols:
            primary   = name_cols[0]
            secondary = (block_cols + email_cols + other_id_cols or [None])[0]
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
                            uf.union(idxs[0], idx)

        # ── Pass 4: Transliterated fuzzy name match ──────────────
        self.log_callback("  [Pass 4] Fuzzy name match (blocked)...")
        if name_cols:
            primary = name_cols[0]
            df_work = self.df.copy()
            df_work[primary] = df_work[primary].fillna("").astype(str)

            indexer = recordlinkage.Index()
            # CRITICAL OPTIMIZATION: Do NOT use .block() on large datasets (20k+ rows) 
            # if the block key has low cardinality. It causes an O(N^2) Cartesian explosion!
            # Using sortedneighbourhood scales perfectly at O(N * window).
            if block_cols:
                indexer.sortedneighbourhood(primary, window=7, block_on=block_cols[0])
            else:
                indexer.sortedneighbourhood(primary, window=7)

            candidate_links = indexer.index(df_work)
            merged_in_pass4 = 0
            for idx1, idx2 in candidate_links:
                if uf.find(idx1) == uf.find(idx2):
                    continue
                n1 = _norm(df_work.loc[idx1, primary])
                n2 = _norm(df_work.loc[idx2, primary])
                if not n1 or not n2:
                    continue
                score = fuzz.token_sort_ratio(n1, n2)
                if score >= self.threshold:
                    uf.union(idx1, idx2)
                    merged_in_pass4 += 1
            if merged_in_pass4 > 0:
                self.log_callback(f"    Merged {merged_in_pass4} records in Pass 4")

        # ── Pass 5: Multi-field fuzzy matching ───────────────────
        self.log_callback("  [Pass 5] Multi-field fuzzy matching (weighted)...")
        self._pass_multifield(uf, name_cols, email_cols, phone_cols, block_cols)

        # ── Extract clusters ─────────────────────────────────────
        cluster_map: Dict[int, List[int]] = {}
        for i in range(n):
            root = uf.find(i)
            cluster_map.setdefault(root, []).append(i)

        dup_clusters = {r: idxs for r, idxs in cluster_map.items() if len(idxs) > 1}
        self.log_callback(f"  [Dedup] {n} rows → {len(cluster_map)} unique entities "
              f"({len(dup_clusters)} duplicate clusters found)")

        # ── Build canonical records ───────────────────────────────
        canonical_records = {
            root: self._build_canonical(indices)
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

        # ── Return merged result ──────────────────────────────────
        self.dedup_changes = []
        if self.keep_all_rows:
            return self._enrich_all_rows(cluster_map, canonical_records, name_cols)
        else:
            return self._merge_to_canonical(cluster_map, canonical_records, name_cols)

    # ─────────────────────────────────────────────────────────────
    # Pass 5: Multi-field weighted similarity
    # ─────────────────────────────────────────────────────────────
    def _pass_multifield(
        self,
        uf: UnionFind,
        name_cols, email_cols, phone_cols, block_cols,
    ):
        """
        Score pairs of rows across multiple fields and merge those
        that exceed a composite threshold.
        Field weights: name=0.5, email=0.3, phone/location=0.2
        """
        if not name_cols:
            return

        primary  = name_cols[0]
        df_work  = self.df.copy().fillna("")

        # Build candidate pairs (blocked to avoid O(N^2))
        indexer = recordlinkage.Index()
        if block_cols:
            indexer.sortedneighbourhood(primary, window=5, block_on=block_cols[0])
        else:
            indexer.sortedneighbourhood(primary, window=5)

        candidate_links = indexer.index(df_work)
        merged = 0

        for idx1, idx2 in candidate_links:
            if uf.find(idx1) == uf.find(idx2):
                continue

            score = 0.0
            weight_total = 0.0

            # Name component (weight 0.5)
            # CRITICAL: We MUST have a valid name to perform fuzzy entity resolution.
            # Otherwise, two users with missing names from the same city will falsely merge.
            n1 = _norm(df_work.loc[idx1, primary])
            n2 = _norm(df_work.loc[idx2, primary])
            if not n1 or not n2:
                continue

            score        += 0.5 * fuzz.token_set_ratio(n1, n2)
            weight_total += 0.5

            # Email component (weight 0.3)
            for ec in email_cols[:1]:
                e1 = _norm(df_work.loc[idx1, ec])
                e2 = _norm(df_work.loc[idx2, ec])
                if e1 and e2:
                    # Compare email prefix (before @)
                    prefix1 = e1.split("@")[0]
                    prefix2 = e2.split("@")[0]
                    score        += 0.3 * fuzz.ratio(prefix1, prefix2)
                    weight_total += 0.3

            # Location / phone component (weight 0.2)
            for lc in (block_cols + phone_cols)[:1]:
                l1 = _norm(df_work.loc[idx1, lc])
                l2 = _norm(df_work.loc[idx2, lc])
                if l1 and l2:
                    score        += 0.2 * fuzz.ratio(l1, l2)
                    weight_total += 0.2

            if weight_total == 0:
                continue

            normalised_score = score / weight_total
            if normalised_score >= self.threshold:
                uf.union(idx1, idx2)
                merged += 1

        if merged > 0:
            self.log_callback(f"    Merged {merged} records in Pass 5")

    # ─────────────────────────────────────────────────────────────
    # Canonical record builder
    # ─────────────────────────────────────────────────────────────
    def _build_canonical(self, indices: List[int]) -> dict:
        """
        For a cluster of duplicate rows, build one canonical record:
        - Prefer the most frequent non-null value per field
        - Ties broken by longest string (more detailed)
        - Numeric fields: use median for stability
        """
        cluster_df = self.df.iloc[indices]
        canonical  = {}

        for col in self.df.columns:
            vals = cluster_df[col].dropna()
            vals = vals[~vals.astype(str).str.strip().str.lower().isin(_NULL_SET)]

            if len(vals) == 0:
                canonical[col] = np.nan
                continue

            if pd.api.types.is_numeric_dtype(vals):
                canonical[col] = float(vals.median())
            else:
                modes = vals.mode()
                if len(modes) == 1:
                    canonical[col] = modes.iloc[0]
                else:
                    # Most frequent; ties → longest string
                    freq = vals.value_counts()
                    top_freq = freq.iloc[0]
                    top_vals = freq[freq == top_freq].index.tolist()
                    canonical[col] = max(top_vals, key=lambda x: len(str(x)))

        return canonical

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
            # Log changes
            if name_cols and len(indices) > 1:
                canon_name = str(canon.get(name_cols[0], ""))
                for idx in indices:
                    orig = str(self.df.loc[idx, name_cols[0]])
                    if _is_valid(orig) and orig != canon_name:
                        self.dedup_changes.append({
                            "Original": orig,
                            "Corrected": canon_name,
                            "cluster_size": len(indices),
                        })

        result = pd.DataFrame(merged).reset_index(drop=True)
        
        # Restore dtypes from original dataframe to avoid type downcasting (e.g. float to object)
        for col in self.df.columns:
            if col in result.columns:
                try:
                    result[col] = result[col].astype(self.df[col].dtype)
                except (ValueError, TypeError):
                    pass
                    
        print(f"  [Dedup] Merged to {len(result)} unique records")
        return result

    # ─────────────────────────────────────────────────────────────
    # keep_all_rows=True: enrich every row with canonical data
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
                # Overwrite name columns with canonical name
                for col in name_cols:
                    cleaned.loc[idx, col] = canon.get(col, cleaned.loc[idx, col])
                # Fill missing values from canonical record
                for col in cleaned.columns:
                    val = cleaned.loc[idx, col]
                    if not _is_valid(val):
                        cleaned.loc[idx, col] = canon.get(col, val)

            # Log name changes
            if name_cols and len(indices) > 1:
                canon_name = str(canon.get(name_cols[0], ""))
                for idx in indices:
                    orig = str(self.df.loc[idx, name_cols[0]])
                    if _is_valid(orig) and orig != canon_name:
                        self.dedup_changes.append({
                            "Original": orig,
                            "Corrected": canon_name,
                            "cluster_size": len(indices),
                        })

        return cleaned
