Deployed app: https://used-car-price-ayesha.streamlit.app/

# Used Car Price Prediction

Predicts the price of a used car from brand, model, age, mileage, engine, transmission, colours, accident history and title status. Five regression algorithms - Extra Trees, Hist Gradient Boosting, AdaBoost, Ridge and SVR - were compared with 10-fold cross-validation, and the best one is served by a Streamlit app.

## Files
- FA24-BSE-028.ipynb - full experiment
- app.py - Streamlit app
- car_utils.py - data cleaning
- used_car_price_model.joblib - trained model
- used_cars.csv - dataset

## Run locally
```
pip install -r requirements.txt
streamlit run app.py
```
