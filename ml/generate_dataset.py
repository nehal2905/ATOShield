"""Synthetic dataset generator for ATOShield.

Produces two parquet files under ``ml/data/``:

* ``normal.parquet``       — ONLY benign events, used to train the unsupervised
                             Isolation Forest. The model never sees an attack
                             label; it learns "what normal looks like".
* ``labeled_test.parquet`` — benign + attack events with an ``is_attack`` label,
                             used by ``evaluate.py`` for an HONEST evaluation.

Each row contains the canonical raw signals consumed by ``features.py``:
    login_hour, ip_change, device_change, frequency, geo_velocity, failed_attempts
plus bookkeeping columns (user, attack_type).

The attack mix deliberately includes a "slow-burn" class that flips a single
signal at a time. Those are genuinely hard for an anomaly detector to catch, so
recall will NOT be 100%. That is the point — honest metrics over fabricated ones.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

RAW_COLUMNS = [
    "login_hour",
    "ip_change",
    "device_change",
    "frequency",
    "geo_velocity",
    "failed_attempts",
]


@dataclass
class UserProfile:
    user_id: str
    home_hour: float       # center of their usual login hour band
    hour_spread: float     # std dev of login hour


def _make_users(rng: np.random.Generator, n_users: int) -> List[UserProfile]:
    users = []
    for i in range(n_users):
        home_hour = float(rng.integers(6, 23))      # most people: daytime/evening
        spread = float(rng.uniform(1.0, 2.5))
        users.append(UserProfile(user_id=f"user_{i:04d}", home_hour=home_hour, hour_spread=spread))
    return users


def _normal_event(rng: np.random.Generator, u: UserProfile) -> dict:
    hour = float(np.clip(rng.normal(u.home_hour, u.hour_spread), 0, 23.999)) % 24.0
    ip_change = 1.0 if rng.random() < 0.05 else 0.0        # occasional new network
    device_change = 1.0 if rng.random() < 0.03 else 0.0     # rarely a new device
    frequency = float(rng.poisson(1.0) + 1)                 # 1..~4 logins/hour

    # Geo movement: usually stationary; sometimes modest travel; rarely a flight
    roll = rng.random()
    if roll < 0.80:
        geo_velocity = float(abs(rng.normal(0, 5)))         # ~stationary jitter
    elif roll < 0.97:
        geo_velocity = float(rng.uniform(5, 120))           # commuting/driving
    else:
        geo_velocity = float(rng.uniform(300, 850))         # legit flight (< 900)

    failed_attempts = float(rng.poisson(0.2))               # mostly 0
    return {
        "login_hour": hour,
        "ip_change": ip_change,
        "device_change": device_change,
        "frequency": frequency,
        "geo_velocity": geo_velocity,
        "failed_attempts": failed_attempts,
        "user": u.user_id,
        "attack_type": "none",
        "is_attack": 0,
    }


def _attack_event(rng: np.random.Generator, u: UserProfile) -> dict:
    kind = rng.choice(
        ["credential_stuffing", "impossible_travel", "new_device_ip_odd_hour", "slow_burn"],
        p=[0.30, 0.25, 0.25, 0.20],
    )
    base = {
        "login_hour": float(rng.uniform(0, 24)),
        "ip_change": 0.0,
        "device_change": 0.0,
        "frequency": float(rng.poisson(1.0) + 1),
        "geo_velocity": float(abs(rng.normal(0, 5))),
        "failed_attempts": 0.0,
        "user": u.user_id,
        "attack_type": kind,
        "is_attack": 1,
    }

    if kind == "credential_stuffing":
        base["frequency"] = float(rng.uniform(8, 40))
        base["failed_attempts"] = float(rng.uniform(4, 25))
        base["ip_change"] = 1.0
        base["device_change"] = 1.0 if rng.random() < 0.5 else 0.0

    elif kind == "impossible_travel":
        base["geo_velocity"] = float(rng.uniform(950, 5000))
        base["ip_change"] = 1.0
        base["device_change"] = 1.0 if rng.random() < 0.7 else 0.0

    elif kind == "new_device_ip_odd_hour":
        base["device_change"] = 1.0
        base["ip_change"] = 1.0
        base["login_hour"] = float(rng.uniform(1, 5))       # 1am–5am
        base["failed_attempts"] = float(rng.poisson(0.5))

    else:  # slow_burn — flip exactly ONE signal, subtly. Hard to catch.
        signal = rng.choice(["ip", "device", "freq", "fail", "fast_travel"])
        if signal == "ip":
            base["ip_change"] = 1.0
        elif signal == "device":
            base["device_change"] = 1.0
        elif signal == "freq":
            base["frequency"] = float(rng.uniform(4, 7))
        elif signal == "fail":
            base["failed_attempts"] = float(rng.uniform(2, 4))
        else:  # fast but technically possible travel (600–880 km/h)
            base["geo_velocity"] = float(rng.uniform(600, 880))
            base["ip_change"] = 1.0
    return base


def generate(n_normal: int, n_users: int, n_attacks: int, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    users = _make_users(rng, n_users)
    os.makedirs(DATA_DIR, exist_ok=True)

    normal_rows = [_normal_event(rng, users[rng.integers(0, n_users)]) for _ in range(n_normal)]
    normal_df = pd.DataFrame(normal_rows)

    # Held-out benign rows for the test set (separate draw, so eval isn't on train rows)
    n_test_normal = max(int(n_normal * 0.2), n_attacks)
    test_normal_rows = [_normal_event(rng, users[rng.integers(0, n_users)]) for _ in range(n_test_normal)]
    attack_rows = [_attack_event(rng, users[rng.integers(0, n_users)]) for _ in range(n_attacks)]
    test_df = pd.DataFrame(test_normal_rows + attack_rows).sample(frac=1.0, random_state=seed).reset_index(drop=True)

    normal_path = os.path.join(DATA_DIR, "normal.parquet")
    test_path = os.path.join(DATA_DIR, "labeled_test.parquet")
    normal_df.to_parquet(normal_path, index=False)
    test_df.to_parquet(test_path, index=False)

    print(f"[generate_dataset] wrote {len(normal_df):,} normal rows -> {normal_path}")
    print(
        f"[generate_dataset] wrote {len(test_df):,} test rows "
        f"({n_attacks:,} attacks, {len(test_normal_rows):,} benign) -> {test_path}"
    )
    print("[generate_dataset] attack mix:")
    print(test_df[test_df.is_attack == 1]["attack_type"].value_counts().to_string())


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic ATOShield datasets")
    ap.add_argument("--normal", type=int, default=10000, help="number of normal (training) events")
    ap.add_argument("--users", type=int, default=200, help="number of synthetic users")
    ap.add_argument("--attacks", type=int, default=1000, help="number of labeled attack events")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    generate(args.normal, args.users, args.attacks, args.seed)


if __name__ == "__main__":
    main()
