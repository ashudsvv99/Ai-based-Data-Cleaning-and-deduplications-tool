"""
Entity resolution: links records that represent the same real-world entity
by building a fuzzy-match graph across transliterated names.
"""
import re
import pandas as pd
from typing import Dict
from rapidfuzz import fuzz
from cleaning.multilingual import MultilingualEngine
import config


class EntityResolver:
    """
    After name transliteration, this module builds a fuzzy match graph
    to identify name clusters that refer to the same person.
    """

    def __init__(self, threshold: int = None):
        self.threshold = threshold or config.FUZZY_MATCH_THRESHOLD
        self.clusters = {}

    def build_name_clusters(self, mapping: Dict[str, str]) -> Dict[str, str]:
        """
        Given a transliteration mapping {original -> transliterated},
        find clusters of transliterated names that fuzzy-match each other,
        and unify them to a single canonical name.

        Returns an updated mapping where all variants point to the same canonical name.
        """
        # Get unique transliterated names
        transliterated_names = list(set(mapping.values()))

        if len(transliterated_names) <= 1:
            return mapping

        # Build adjacency via fuzzy matching
        clusters = []  # list of sets
        assigned = set()

        for i, name_a in enumerate(transliterated_names):
            if name_a in assigned:
                continue
            cluster = {name_a}
            for j in range(i + 1, len(transliterated_names)):
                name_b = transliterated_names[j]
                if name_b in assigned:
                    continue
                score = fuzz.token_sort_ratio(name_a.lower(), name_b.lower())
                if score >= self.threshold:
                    cluster.add(name_b)
                    assigned.add(name_b)
            assigned.add(name_a)
            clusters.append(cluster)

        # For each cluster, pick canonical name (most common or longest)
        canonical_map = {}
        for cluster in clusters:
            # Count frequency of each name in the original mapping values
            freq = {}
            for orig, trans in mapping.items():
                if trans in cluster:
                    freq[trans] = freq.get(trans, 0) + 1

            # Pick the most frequent; ties broken by length then alphabetical
            canonical = max(
                cluster,
                key=lambda n: (freq.get(n, 0), len(n)),
            )
            for name in cluster:
                canonical_map[name] = canonical

        # Update the original mapping
        unified = {}
        for orig, trans in mapping.items():
            unified[orig] = canonical_map.get(trans, trans)

        self.clusters = {
            i: list(c) for i, c in enumerate(clusters) if len(c) > 1
        }

        if self.clusters:
            print(f"  [EntityResolver] Found {len(self.clusters)} name clusters:")
            for idx, members in self.clusters.items():
                print(f"    Cluster {idx + 1}: {members}")

        return unified
