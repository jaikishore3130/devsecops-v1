from __future__ import annotations

import numpy as np

INCIDENT_EFFECTS = {
    "D1": {
        "change": 1.2,
        "queue": 1.4,
        "build": 1.6,
        "retry": 1.8,
        "pipeline": 1.1,
    },
    "D2": {
        "resource": 1.5,
        "cpu": 1.2,
        "memory": 1.3,
        "queue": 1.1,
        "restart": 1.6,
    },
    "C1": {
        "auth": 2.0,
        "source": 1.4,
        "failure_rate": 1.9,
    },
    "C2": {
        "traffic": 2.4,
        "source": 1.8,
        "packet": 1.7,
        "connection": 1.6,
    },
    "C3": {
        "scan": 2.0,
        "port": 1.7,
        "host": 1.5,
        "short_flow": 1.6,
    },
    "C4": {
        "web": 1.8,
        "latency": 1.5,
        "error": 1.7,
        "request": 1.4,
    },
    "C5": {
        "anomaly": 1.8,
        "host": 1.4,
        "network": 1.7,
        "traffic": 1.3,
    },
}


def scenario_sample(rng: np.random.Generator, size: int, probs: dict[str, float]) -> np.ndarray:
    return rng.choice(list(probs.keys()), size=size, p=list(probs.values()))


def scenario_signal(name: str, rng: np.random.Generator, size: int) -> np.ndarray:
    return rng.normal(0.0, 1.0, size=size) * (1.0 + INCIDENCE_FACTOR(name))


def INCIDENCE_FACTOR(name: str) -> float:
    return {"D1": 0.8, "D2": 0.9, "C1": 0.9, "C2": 1.1, "C3": 0.7, "C4": 0.8, "C5": 0.8}.get(name, 0.0)
