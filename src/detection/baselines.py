from __future__ import annotations

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier


def model_factories(seed: int = 20261008) -> dict:
    return {
        "majority": lambda: DummyClassifier(strategy="most_frequent"),
        "stratified_dummy": lambda: DummyClassifier(strategy="stratified", random_state=seed),
        "logistic_regression": lambda: LogisticRegression(C=1.0, max_iter=100, solver="liblinear", random_state=seed),
        "random_forest": lambda: RandomForestClassifier(n_estimators=30, max_depth=10, min_samples_leaf=10, n_jobs=2, random_state=seed, class_weight="balanced_subsample"),
        "xgboost": lambda: XGBClassifier(
            n_estimators=80, max_depth=6, learning_rate=0.08, subsample=0.8,
            colsample_bytree=0.8, min_child_weight=5, reg_lambda=1.0,
            tree_method="hist", eval_metric="logloss", n_jobs=2, random_state=seed,
        ),
    }
