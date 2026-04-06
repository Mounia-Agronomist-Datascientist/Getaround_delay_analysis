# Getaround Delay Analysis

## Objective
Analyze the impact of cascading delays in consecutive rentals and recommend a minimum buffer threshold between rentals.

## Architecture
- `notebooks/` : Exploration (EDA, analysis)
- `src/metrics.py` : Reusable module
- `tests/` : Unit tests
- `app.py` : Interactive dashboard (Streamlit)

## Key Results
- Optimal threshold: **30 minutes**
- Impact: Resolves 50.37% of conflicts, blocks only 1.31% of rentals
- Efficiency ratio: 0.41 (best in class)

## How to Use
```python
from src.metrics import *

df = load_and_prepare_data("data.xlsx")
consecutive, first = separate_rental_groups(df)
df_risk = calculate_risk_level(consecutive)
results = simulate_thresholds(df_risk)
```

## Tests
```bash
pytest tests/test_metrics.py -v
```