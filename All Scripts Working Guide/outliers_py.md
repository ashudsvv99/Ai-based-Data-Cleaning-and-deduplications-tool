# `cleaning/outliers.py` - The Anomaly Handler

What happens if someone accidentally types `999999` for an employee's age? It ruins every chart and average calculation you try to make. The `OutlierHandler` class finds these extreme anomalies and normalizes them.

## Full Working Process & Logic

### 1. The Interquartile Range (IQR) Method
We don't use ML libraries (like Scikit-Learn Isolation Forests) because they are too slow and opaque for simple business tabular data. We use raw statistics.
- **Logic**: We calculate `Q1` (the 25th percentile of the data) and `Q3` (the 75th percentile) using Pandas `.quantile(0.25)`.
- **The IQR**: `IQR = Q3 - Q1`. This represents the "middle 50%" of all data, immune to the extreme edges.
- **The Bounds**: We establish a mathematical ceiling and floor.
  - `lower_bound = Q1 - (IQR_MULTIPLIER * IQR)`
  - `upper_bound = Q3 + (IQR_MULTIPLIER * IQR)`
- `IQR_MULTIPLIER` is imported from `config.py` (default `1.5`). Anything falling outside these bounds is mathematically defined as an outlier.

### 2. Clipping vs. Dropping (`np.where`)
- **The Novice Mistake**: A junior developer will write `df = df[df['Age'] < upper_bound]`. This *drops* the entire row. This is catastrophic. You just lost that employee's Name, Email, and Phone Number just because their Age had a typo.
- **The Professional Solution (Clipping)**: We import Numpy.
- **Logic**: `df[col] = np.where(df[col] > upper_bound, upper_bound, df[col])`.
- **Action**: `np.where` acts like a vectorized IF-THEN statement. IF the Age is greater than `85` (the upper bound), replace it with exactly `85`. Otherwise, leave it alone.
- **Why**: This technique is called **Winsorizing**. It removes the extreme statistical distortion (the `999999` average destroyer) while perfectly preserving the rest of the row's valuable data.
