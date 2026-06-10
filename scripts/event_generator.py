"""Live event generator — makes the dashboard demo-able without a real IdP.

Logs in to obtain a JWT, then POSTs a stream of synthetic login events to
``/api/events``: mostly normal traffic that builds each user's baseline, with an
occasional attack (credential stuffing, impossible travel, new device at an odd
hour). The backend's REAL model scores every event; this script never computes
risk itself.

Usage:
    python scripts/event_generator.py --url http://localhost --rate 1.5 \
        --user admin --password <ADMIN_PASSWORD>
"""

from __future__ import annotations

import argparse
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


@dataclass
class Persona:
    user: str
    ip: str
    device: str
    lat: float
    lon: float
    home_hour: int


CITIES = [
    (40.71, -74.01), (51.51, -0.13), (35.68, 139.69), (48.85, 2.35),
    (-33.87, 151.21), (19.08, 72.88), (37.77, -122.42), (52.52, 13.40),
]


def make_personas(n: int, rng: random.Random) -> list[Persona]:
    out = []
    for i in range(n):
        lat, lon = rng.choice(CITIES)
        out.append(Persona(
            user=f"user_{i:03d}",
            ip=f"{rng.randint(11,223)}.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}",
            device=f"dev-{rng.randint(1000,9999)}",
            lat=lat + rng.uniform(-0.05, 0.05),
            lon=lon + rng.uniform(-0.05, 0.05),
            home_hour=rng.randint(7, 22),
        ))
    return out


def normal_event(p: Persona, rng: random.Random) -> dict:
    return {
        "user": p.user,
        "ip": p.ip,
        "device_fp": p.device,
        "geo_lat": p.lat + rng.uniform(-0.01, 0.01),
        "geo_lon": p.lon + rng.uniform(-0.01, 0.01),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": True,
        "failed_attempts": 0 if rng.random() > 0.1 else 1,
    }


def attack_event(p: Persona, rng: random.Random) -> dict:
    kind = rng.choice(["stuffing", "travel", "newdev"])
    base = {
        "user": p.user,
        "ip": f"45.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}",  # new IP
        "device_fp": f"attacker-{rng.randint(1000,9999)}",
        "geo_lat": p.lat,
        "geo_lon": p.lon,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": True,
        "failed_attempts": 0,
    }
    if kind == "stuffing":
        base["failed_attempts"] = rng.randint(6, 25)
    elif kind == "travel":
        far = rng.choice(CITIES)
        base["geo_lat"], base["geo_lon"] = far[0], far[1]  # huge jump -> high geo-velocity
    else:  # new device at odd hour is naturally captured by new ip+device
        base["device_fp"] = f"odd-{rng.randint(1000,9999)}"
    return base


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost", help="base URL (NGINX or backend)")
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", required=True)
    ap.add_argument("--rate", type=float, default=1.0, help="events per second")
    ap.add_argument("--personas", type=int, default=25)
    ap.add_argument("--attack-prob", type=float, default=0.08)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    personas = make_personas(args.personas, rng)

    with httpx.Client(base_url=args.url, timeout=10.0) as client:
        login = client.post("/api/auth/login", json={"username": args.user, "password": args.password})
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[generator] authenticated as {args.user}; streaming to {args.url}")

        sleep = 1.0 / max(args.rate, 0.01)
        sent = 0
        while True:
            p = rng.choice(personas)
            payload = attack_event(p, rng) if rng.random() < args.attack_prob else normal_event(p, rng)
            try:
                resp = client.post("/api/events", json=payload, headers=headers)
                if resp.status_code == 200:
                    d = resp.json()
                    flag = "  <-- ALERT" if d.get("alert_id") else ""
                    print(f"[{sent:05d}] {d['user']:>10} risk={d['risk']:>3} {d['tier']:<8}{flag}")
                elif resp.status_code == 429:
                    print("[generator] rate-limited by server; backing off")
                    time.sleep(1.0)
                else:
                    print(f"[generator] {resp.status_code}: {resp.text[:120]}")
            except httpx.HTTPError as exc:
                print(f"[generator] request failed: {exc}")
                time.sleep(1.0)
            sent += 1
            time.sleep(sleep)


if __name__ == "__main__":
    main()
