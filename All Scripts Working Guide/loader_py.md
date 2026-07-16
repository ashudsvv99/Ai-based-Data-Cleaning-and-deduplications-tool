# `backend/loader.py` - The Universal Data Ingestor

Before any algorithmic cleaning can occur, we must load the raw file from the hard drive into RAM. The `UniversalLoader` class is built to aggressively handle the common pitfalls of messy business files (encoding errors, hidden empty strings, massive file sizes).

## Full Working Process & Logic

### 1. PyArrow Backend Optimization
- **Problem**: Reading a 100,000-row CSV file using standard Pandas (`engine="c"`) is single-threaded and notoriously slow, often causing UI freezing.
- **Solution**: We explicitly call `pd.read_csv(self.filepath, engine="pyarrow")`. 
- **Why**: PyArrow is written in C++ and uses multi-threading out of the box. It bypasses Pandas' inefficient object allocation and loads massive files exponentially faster.

### 2. Encoding Fallbacks
- **Logic**: We wrap the initial PyArrow read in a `try-except` block.
- **Why**: PyArrow is incredibly fast, but strict. If a user uploads a CSV saved from an old Windows machine using ANSI encoding (instead of standard UTF-8), PyArrow will crash. The `except` block catches this and safely falls back to standard Pandas using `encoding="utf-8-sig"`.

### 3. Global Missing Value Coercion
- **Logic**: We import `config.MISSING_VALUE_MARKERS`. We run `df.replace(config.MISSING_VALUE_MARKERS, pd.NA)`.
- **Secondary Logic**: We also run `df.replace(r'^\s*$', pd.NA, regex=True)`.
- **Why**: Users often hit the spacebar in Excel and leave a cell "blank". To Python, a string containing `"   "` is not empty—it's a valid string. The Regex replacement targets any string that consists entirely of whitespace and forcefully converts it to `pd.NA`. This guarantees that downstream scripts (like the `QualityFilter`) correctly register the cell as a missing value.

### 4. Memory Footprint Auditing
- **Logic**: It calls `df.memory_usage(deep=True).sum()` and logs the Megabytes. It also explicitly strips leading and trailing whitespaces from the column headers (`df.columns = [str(c).strip() for c in df.columns]`) to prevent downstream KeyErrors when agents try to reference `df["Price"]` but the column is actually named `df["Price "]`.
