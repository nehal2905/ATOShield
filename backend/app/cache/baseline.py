"""Per-user behavioral baseline in Redis.

This is the part that turns crude flags into meaningful signals: "new IP",
"new device", "login frequency" and "geo-velocity" only mean something relative
to *this user's* history.

CRITICAL ordering rule: on every event we (1) READ the prior baseline, (2)
COMPUTE features against that prior state, and only THEN (3) UPDATE the baseline
with the new event. If you update first, every login looks "known" and the
detector goes blind.

Redis layout (per user ``u``):
  hash  baseline:{u}     -> last_geo="lat,lon", last_login_ts=<epoch>
  set   ips:{u}          -> known IP fingerprints
  set   devices:{u}      -> known device fingerprints
  zset  freq:{u}         -> login epochs (trimmed to trailing 60 min)
  str   fail:{u}         -> running failed-attempt counter (reset on success)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings
from app.core._ml_bridge import features as F

WINDOW_SECONDS = 3600  # trailing 60-minute frequency window
MAX_SET_SIZE = 50      # bound memory: cap known-ip / known-device sets


@dataclass
class ComputedSignals:
    """RawSignals plus a couple of fields handy for alerting/UI."""

    login_hour: float
    ip_change: float
    device_change: float
    frequency: float
    geo_velocity: float
    failed_attempts: float
    impossible_travel: bool
    is_new_user: bool

    def to_raw(self) -> dict:
        return {
            "login_hour": self.login_hour,
            "ip_change": self.ip_change,
            "device_change": self.device_change,
            "frequency": self.frequency,
            "geo_velocity": self.geo_velocity,
            "failed_attempts": self.failed_attempts,
        }


_redis: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def _hour_from_epoch(ts: float) -> float:
    lt = time.gmtime(ts)
    return lt.tm_hour + lt.tm_min / 60.0


async def compute_and_update(
    user: str,
    ip: str,
    device_fp: str,
    geo_lat: float,
    geo_lon: float,
    ts: Optional[float] = None,
    success: bool = True,
    failed_attempts: Optional[int] = None,
) -> ComputedSignals:
    """Read prior baseline, compute signals, then update baseline. Atomic-ish.

    Reads use a pipeline; the update uses a second pipeline after computation so
    the score reflects the PRIOR state only.
    """
    r = get_redis()
    ts = float(ts if ts is not None else time.time())

    base_key = f"baseline:{user}"
    ips_key = f"ips:{user}"
    dev_key = f"devices:{user}"
    freq_key = f"freq:{user}"
    fail_key = f"fail:{user}"

    # ---- (1) READ prior state ----
    pipe = r.pipeline()
    pipe.hgetall(base_key)
    pipe.sismember(ips_key, ip)
    pipe.sismember(dev_key, device_fp)
    pipe.zcount(freq_key, ts - WINDOW_SECONDS, ts)
    pipe.exists(ips_key)
    pipe.get(fail_key)
    base, ip_known, dev_known, prior_count, ip_set_exists, fail_counter = await pipe.execute()

    is_new_user = not bool(base) and not bool(ip_set_exists)

    # ---- (2) COMPUTE features against prior state ----
    login_hour = _hour_from_epoch(ts)
    ip_change = 0.0 if ip_known else 1.0
    device_change = 0.0 if dev_known else 1.0
    frequency = float(prior_count) + 1.0  # include this login

    prev_geo = base.get("last_geo") if base else None
    prev_ts = base.get("last_login_ts") if base else None
    if prev_geo and prev_ts:
        try:
            plat, plon = (float(x) for x in prev_geo.split(","))
            geo_velocity = F.geo_velocity_kmh(plat, plon, geo_lat, geo_lon, ts - float(prev_ts))
        except (ValueError, TypeError):
            geo_velocity = 0.0
    else:
        geo_velocity = 0.0

    # failed_attempts: explicit override wins, else use the running counter
    if failed_attempts is not None:
        failed_val = float(failed_attempts)
    else:
        failed_val = float(int(fail_counter)) if fail_counter else 0.0

    signals = ComputedSignals(
        login_hour=login_hour,
        ip_change=ip_change,
        device_change=device_change,
        frequency=frequency,
        geo_velocity=geo_velocity,
        failed_attempts=failed_val,
        impossible_travel=F.is_impossible_travel(geo_velocity),
        is_new_user=is_new_user,
    )

    # ---- (3) UPDATE baseline with the new event ----
    upd = r.pipeline()
    upd.sadd(ips_key, ip)
    upd.sadd(dev_key, device_fp)
    upd.hset(base_key, mapping={"last_geo": f"{geo_lat},{geo_lon}", "last_login_ts": ts})
    upd.zadd(freq_key, {f"{ts}:{ip}": ts})
    upd.zremrangebyscore(freq_key, 0, ts - WINDOW_SECONDS)
    if success:
        upd.set(fail_key, 0)
    else:
        upd.incr(fail_key)
    # expire idle baselines after 30 days to avoid unbounded growth
    for k in (base_key, ips_key, dev_key, freq_key, fail_key):
        upd.expire(k, 60 * 60 * 24 * 30)
    await upd.execute()

    # Opportunistic trim of oversized sets (rare path)
    if ip_change:
        card = await r.scard(ips_key)
        if card > MAX_SET_SIZE:
            await r.spop(ips_key, card - MAX_SET_SIZE)

    return signals


async def get_snapshot(user: str) -> dict:
    """Read-only baseline view for the dashboard/debugging."""
    r = get_redis()
    pipe = r.pipeline()
    pipe.hgetall(f"baseline:{user}")
    pipe.smembers(f"ips:{user}")
    pipe.smembers(f"devices:{user}")
    pipe.zcard(f"freq:{user}")
    pipe.get(f"fail:{user}")
    base, ips, devices, freq, fail = await pipe.execute()
    return {
        "user": user,
        "last_geo": base.get("last_geo") if base else None,
        "last_login_ts": base.get("last_login_ts") if base else None,
        "known_ips": sorted(ips),
        "known_devices": sorted(devices),
        "logins_in_window": freq,
        "fail_counter": int(fail) if fail else 0,
    }
