from __future__ import annotations

import numpy as np


def sample_environment(rng: np.random.Generator, size: int) -> np.ndarray:
    return rng.choice(["development", "staging", "production", "test"], size=size)


def sample_region(rng: np.random.Generator, size: int) -> np.ndarray:
    return rng.choice(["region-a", "region-b", "region-c", "region-d"], size=size)


def sample_protocol(rng: np.random.Generator, size: int) -> np.ndarray:
    return rng.choice(["tcp", "udp", "icmp", "other"], size=size)


def sample_service(rng: np.random.Generator, size: int) -> np.ndarray:
    return rng.choice(["web", "api", "dns", "ssh", "database", "other"], size=size)


def default_numeric_noise(rng: np.random.Generator, size: int, mean: float, std: float) -> np.ndarray:
    return rng.normal(mean, std, size=size)
