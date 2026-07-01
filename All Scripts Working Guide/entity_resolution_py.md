# `cleaning/entity_resolution.py` - The Cluster Merger

The `DeduplicationEngine` finds the duplicate rows (e.g., Row 5, Row 10, and Row 12 are all "John Doe"). It groups them into a `cluster`. But now what? We can't just delete Row 10 and 12, because Row 10 might have John's Phone Number, while Row 5 is missing it. 

The `EntityResolution` class mathematically collapses (merges) these clusters into a single, highly-complete "Golden Record".

## Full Working Process & Logic

### 1. Iterating the Clusters
- **Logic**: The engine receives `duplicate_clusters`, which is a list of Pandas DataFrames (each DataFrame represents one group of matched rows).
- It iterates through each cluster. If a cluster has only 1 row, it ignores it.

### 2. Determining the "Primary Row"
- **Problem**: Which row do we keep as the foundation?
- **Solution**: We calculate the "Sparsity" (how many empty cells exist) of every row in the cluster.
- **Logic**: `null_counts = cluster.isna().sum(axis=1)`. This counts the exact number of `pd.NA` gaps in each row.
- **Action**: It sorts the cluster using `.sort_values()` based on this null count. The row with the *lowest* number of missing values is crowned the `canonical_row` (Primary Row). The other rows become `secondary_rows`.

### 3. The Backfill Cascade (Data Preservation)
- **Logic**: We iterate through every column in the dataset.
- **Action**: If the `canonical_row` is missing data for a specific column (e.g., `pd.isna(canonical_row["Phone"])`), it loops through the `secondary_rows`.
- As soon as it finds a secondary row that *does* have a Phone Number, it copies that number into the `canonical_row` and breaks the loop.
- **Why**: This ensures that absolutely zero usable data is lost during the deletion of the duplicates. We extract every piece of value from the duplicates before we delete them!

### 4. Reassembly
- Once the `canonical_row` is perfectly assembled, it is added to a `resolved_rows` list.
- All the original rows that made up the cluster are dropped from the main DataFrame, and the new, single, super-charged `canonical_row` is appended in their place.
