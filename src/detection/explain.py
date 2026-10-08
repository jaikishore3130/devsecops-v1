from __future__ import annotations

import numpy as np


def feature_importance(model, preprocessor, top_n: int = 30) -> dict:
    names = list(preprocessor.get_feature_names_out())
    estimator = model.named_steps["model"] if hasattr(model, "named_steps") else model
    if not hasattr(estimator, "feature_importances_"):
        return {"method": "unavailable", "features": []}
    values = np.asarray(estimator.feature_importances_, dtype=float)
    order = np.argsort(values)[::-1][:top_n]
    return {
        "method": "gain_or_split_importance_from_final_tree_model",
        "features": [{"feature": names[index], "importance": float(values[index])} for index in order],
    }


def leakage_scan(importance: dict, forbidden_tokens: set[str]) -> dict:
    top_features = [item["feature"] for item in importance.get("features", [])]
    violations = [feature for feature in top_features if any(token in feature for token in forbidden_tokens)]
    return {"top_features": top_features, "forbidden_feature_tokens_found": violations, "passed": not violations}
