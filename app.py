import joblib
import pandas as pd
import streamlit as st

from car_utils import FEATURES, REFERENCE_YEAR, clean_cars

st.set_page_config(page_title="Used Car Price Predictor", page_icon="🚗", layout="centered")

MODEL_FILE = "used_car_price_model.joblib"
DATA_FILE = "used_cars.csv"


@st.cache_data
def load_data():
    raw = pd.read_csv(DATA_FILE)
    X, y = clean_cars(raw)
    return raw, X, y


@st.cache_resource
def load_model():
    """Load the saved model; if the library versions differ, refit the same pipeline on the dataset."""
    try:
        return joblib.load(MODEL_FILE)
    except Exception:
        import numpy as np
        from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
        from sklearn.ensemble import HistGradientBoostingRegressor
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
        from car_utils import CAT_COLS, NUM_COLS
        _, X, y = load_data()
        pre = ColumnTransformer([
            ("num", Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)),
                              ("sc", StandardScaler())]), NUM_COLS),
            ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=5,
                                  sparse_output=False), CAT_COLS)])
        reg = TransformedTargetRegressor(
            regressor=HistGradientBoostingRegressor(learning_rate=0.05, max_iter=300, random_state=42),
            func=np.log1p, inverse_func=np.expm1)
        return Pipeline([("prep", pre), ("model", reg)]).fit(X, y)


raw, X, y = load_data()
model = load_model()

st.title("🚗 Used Car Price Predictor")
st.caption("Enter the details of a used car to get an estimated asking price in US dollars.")

brands = sorted(X["brand"].unique())
c1, c2 = st.columns(2)
brand = c1.selectbox("Brand", brands, index=brands.index("Toyota") if "Toyota" in brands else 0)
models = sorted(X.loc[X["brand"] == brand, "model"].unique())
car_model = c2.selectbox("Model", models)

row = X[(X["brand"] == brand) & (X["model"] == car_model)]


def pick(series):
    return series.mode().iloc[0]


c3, c4 = st.columns(2)
model_year = c3.number_input("Model year", min_value=1990, max_value=2025, value=2018, step=1)
mileage = c4.number_input("Mileage (miles)", min_value=0, max_value=500000, value=50000, step=1000)

c5, c6 = st.columns(2)
fuel_opts = sorted(X["fuel_type"].unique())
fuel = c5.selectbox("Fuel type", fuel_opts, index=fuel_opts.index(pick(row["fuel_type"])) if len(row) else 0)
trans_opts = sorted(X["transmission_type"].unique())
trans = c6.selectbox("Transmission", trans_opts, index=trans_opts.index(pick(row["transmission_type"])) if len(row) else 0)

st.subheader("Engine")
c7, c8, c9 = st.columns(3)
hp_default = float(row["hp"].median()) if row["hp"].notna().any() else 250.0
l_default = float(row["liters"].median()) if row["liters"].notna().any() else 3.0
cyl_default = int(row["cylinders"].median()) if row["cylinders"].notna().any() else 6
hp = c7.number_input("Horsepower", min_value=50.0, max_value=1100.0, value=hp_default, step=5.0)
liters = c8.number_input("Engine size (L)", min_value=0.6, max_value=8.5, value=l_default, step=0.1)
cylinders = c9.number_input("Cylinders", min_value=2, max_value=16, value=cyl_default, step=1)

st.subheader("Condition and appearance")
c10, c11 = st.columns(2)
accident = c10.selectbox("Accident history", ["None reported", "Reported"])
clean_title = c11.selectbox("Clean title", ["Yes", "No"])
c12, c13 = st.columns(2)
ext_opts = sorted(X["ext_col"].value_counts().head(30).index)
int_opts = sorted(X["int_col"].value_counts().head(30).index)
ext = c12.selectbox("Exterior colour", ext_opts, index=ext_opts.index("Black") if "Black" in ext_opts else 0)
inte = c13.selectbox("Interior colour", int_opts, index=int_opts.index("Black") if "Black" in int_opts else 0)

if st.button("Predict price", type="primary", use_container_width=True):
    sample = pd.DataFrame([{
        "brand": brand, "model": car_model, "fuel_type": fuel, "transmission_type": trans,
        "ext_col": ext, "int_col": inte, "accident": accident, "clean_title": clean_title,
        "car_age": REFERENCE_YEAR - int(model_year), "milage": float(mileage),
        "hp": float(hp), "liters": float(liters), "cylinders": float(cylinders),
        "speeds": float(row["speeds"].median()) if row["speeds"].notna().any() else float("nan"),
    }])[FEATURES]
    price = float(model.predict(sample)[0])
    st.success(f"Estimated price: **${price:,.0f}**")
    st.caption("This is a statistical estimate from listing data, typically within roughly ±15% for an average car; "
               "rare or exotic models can be off by more. It is not a valuation.")