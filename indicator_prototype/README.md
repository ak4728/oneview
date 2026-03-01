# Indicator Prototype

Prototype pipeline to compute technical indicators, train a baseline model, and propose indicator combinations with SHAP importance. Run in a Python 3.10+ environment.

Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Quick run

```powershell
python run_prototype.py --symbol SPY --interval 1d --years 5
```

Run the Streamlit UI

```powershell
streamlit run app.py
```
