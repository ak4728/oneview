import pandas as pd
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import joblib


def tune_random_forest(X: pd.DataFrame, y: pd.Series, param_grid=None):
    if param_grid is None:
        param_grid = {
            'n_estimators': [100, 200],
            'max_depth': [5, 10, None],
            'min_samples_split': [2, 5]
        }
    tscv = TimeSeriesSplit(n_splits=3)
    rf = RandomForestRegressor(random_state=42, n_jobs=-1)
    g = GridSearchCV(rf, param_grid, cv=tscv, scoring='neg_mean_squared_error', n_jobs=-1)
    g.fit(X.fillna(0), y.fillna(0))
    joblib.dump(g.best_estimator_, 'rf_best.joblib')
    return g.best_params_, g.best_score_, 'rf_best.joblib'


def tune_xgboost(X: pd.DataFrame, y: pd.Series, param_grid=None):
    if param_grid is None:
        param_grid = {
            'n_estimators': [100, 200],
            'max_depth': [3, 6],
            'learning_rate': [0.01, 0.1]
        }
    tscv = TimeSeriesSplit(n_splits=3)
    model = xgb.XGBRegressor(objective='reg:squarederror', random_state=42, n_jobs=-1)
    g = GridSearchCV(model, param_grid, cv=tscv, scoring='neg_mean_squared_error', n_jobs=-1)
    g.fit(X.fillna(0), y.fillna(0))
    joblib.dump(g.best_estimator_, 'xgb_best.joblib')
    return g.best_params_, g.best_score_, 'xgb_best.joblib'
