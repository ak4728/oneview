import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import shap
import joblib

def prepare_features(data: pd.DataFrame):
    features = data.drop(columns=['open','high','low','close','adjclose','volume'], errors='ignore')
    return features

def prepare_target(data: pd.DataFrame, horizon: int = 1):
    # Predict forward horizon log return
    target = (data['close'].shift(-horizon) / data['close'] - 1).shift(0)
    return target

def train_model(df: pd.DataFrame, horizon: int = 1, test_size: float = 0.2):
    df = df.copy()
    y = prepare_target(df, horizon).dropna()
    X = prepare_features(df).loc[y.index]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, shuffle=False)

    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    explainer = shap.Explainer(model, X_train)
    shap_values = explainer(X_test)

    # Save model and explainer
    joblib.dump(model, 'rf_model.joblib')
    joblib.dump(explainer, 'shap_explainer.joblib')

    importance = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)

    return model, importance, shap_values
