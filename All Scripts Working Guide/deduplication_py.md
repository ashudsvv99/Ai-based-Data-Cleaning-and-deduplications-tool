# `cleaning/deduplication.py` - The Identity Resolver

Finding duplicate rows in a dataset is computationally terrifying. If you have 50,000 rows, comparing every row to every other row to find duplicates requires $50,000^2$ (2.5 Billion) comparisons. A normal Python script will freeze and crash. 

The `DeduplicationEngine` solves this using advanced Record Linkage algorithms.

## Full Working Process & Logic

### 1. The Exact Match Pass (Pandas)
- Before doing expensive fuzzy matching, it simply runs `df.duplicated(keep=False)`. If two rows are 100% identical byte-for-byte, they are instantly grouped.

### 2. Sorted Neighbourhood Indexing (The $O(N)$ Solution)
- **Library used**: `recordlinkage`
- It picks a main identifier column (like `Email` or `First Name`). It sorts the entire dataset alphabetically by this column.
- Now, it only compares a row to the 7 rows directly above and below it (`window=7`). Because the data is sorted alphabetically, duplicates (e.g., "Jon Doe" and "John Doe") will naturally sit right next to each other in the array! This reduces billions of comparisons to just a few thousand.

### 3. Multi-Field Weighted Fuzzy Matching
- **Library used**: `RapidFuzz` (which is written in C++ and is 10x faster than standard `FuzzyWuzzy`).
- **Logic**: Once the index gives us a pair of rows (e.g., Row 5 and Row 6), the engine calculates the Levenshtein Distance (how many character edits it takes to turn string A into string B).
- It doesn't just check one column. It checks `Names`, `Emails`, `Phones`, and `Cities`. It applies weights: Name match = 40%, Email match = 40%, City match = 20%. 
- If the final weighted `similarity_score >= config.FUZZY_MATCH_THRESHOLD` (e.g., 85%), it flags the pair as a duplicate cluster!

### 4. Cluster Formation (`networkx`)
- What if Row A is a duplicate of Row B, and Row B is a duplicate of Row C? 
- We use the mathematical Graph Theory library `networkx`. We treat every row as a "Node" and every duplicate match as an "Edge". 
- We call `nx.connected_components(G)`, which instantly groups A, B, and C into a single massive cluster, ready to be merged by the `EntityResolution` script!
