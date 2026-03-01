import pandas as pd
from gplearn.genetic import SymbolicRegressor
from sklearn.model_selection import train_test_split
import joblib


def run_symbolic_regression(X: pd.DataFrame, y: pd.Series, max_depth: int = 3, population_size: int = 1000, generations: int = 20):
    # Select a small set of operators suitable for indicators
    est = SymbolicRegressor(population_size=population_size,
                            generations=generations,
                            tournament_size=20,
                            stopping_criteria=0.01,
                            const_range=(-1.0, 1.0),
                            init_depth=(2, max_depth),
                            function_set=('add', 'sub', 'mul', 'div', 'sin', 'cos', 'log', 'sqrt'),
                            parsimony_coefficient=0.001,
                            random_state=42, verbose=1)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    est.fit(X_train.fillna(0).values, y_train.fillna(0).values)

    # Save model
    joblib.dump(est, 'symbolic_est.joblib')

    program = est._program
    # human-readable formula
    formula = str(program)
    score = est.score(X_test.fillna(0).values, y_test.fillna(0).values)
    return {'formula': formula, 'score': score, 'estimator_path': 'symbolic_est.joblib'}
