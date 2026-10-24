import re
import numpy as np
import pandas as pd

REFERENCE_YEAR = 2024  # newest model year present in the data

CAT_COLS = ["brand", "model", "fuel_type", "transmission_type", "ext_col", "int_col", "accident", "clean_title"]
NUM_COLS = ["car_age", "milage", "hp", "liters", "cylinders", "speeds"]
FEATURES = CAT_COLS + NUM_COLS


def _num(pattern, text):
    m = re.search(pattern, str(text), flags=re.I)
    return float(m.group(1)) if m else np.nan


def _cylinders(text):
    m = re.search(r"\b[VIH](\d{1,2})\b|(\d{1,2})\s*Cylinder", str(text), flags=re.I)
    if not m:
        return np.nan
    return float(m.group(1) or m.group(2))


def _transmission_type(text):
    t = str(text).upper()
    if "CVT" in t:
        return "CVT"
    if "M/T" in t or "MANUAL" in t:
        return "Manual"
    if "A/T" in t or "AUTOMATIC" in t or "DUAL SHIFT" in t or "DCT" in t:
        return "Automatic"
    return "Other"


def _fuel(text):
    if pd.isna(text) or str(text).strip() in ("–", "-", "not supported"):
        return "Unknown"
    return str(text).strip()


def _accident(text):
    if pd.isna(text):
        return "Unknown"
    return "None reported" if "none" in str(text).lower() else "Reported"


def clean_cars(df):
    """Turn the raw Kaggle table into model-ready columns. Returns (X, y)."""
    out = pd.DataFrame(index=df.index)
    out["brand"] = df["brand"].str.strip()
    out["model"] = df["model"].str.strip()
    out["car_age"] = REFERENCE_YEAR - df["model_year"]
    out["milage"] = (df["milage"].astype(str).str.replace(r"[^\d.]", "", regex=True)
                     .replace("", np.nan).astype(float))
    out["fuel_type"] = df["fuel_type"].map(_fuel)
    out["hp"] = df["engine"].map(lambda s: _num(r"(\d+(?:\.\d+)?)\s*HP", s))
    out["liters"] = df["engine"].map(lambda s: _num(r"(\d+(?:\.\d+)?)\s*(?:L\b|Liter)", s))
    out["cylinders"] = df["engine"].map(_cylinders)
    out["transmission_type"] = df["transmission"].map(_transmission_type)
    out["speeds"] = df["transmission"].map(lambda s: _num(r"(\d+)-Speed", s))
    out["ext_col"] = df["ext_col"].astype(str).str.strip()
    out["int_col"] = df["int_col"].astype(str).str.strip()
    out["accident"] = df["accident"].map(_accident)
    out["clean_title"] = df["clean_title"].fillna("No")
    y = None
    if "price" in df.columns:
        y = (df["price"].astype(str).str.replace(r"[^\d.]", "", regex=True).astype(float))
    return out[FEATURES], y
