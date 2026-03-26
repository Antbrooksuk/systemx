"""Session window timing — London 08:00-10:00, NY 14:30-16:30 UTC."""
from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional


@dataclass
class Session:
    name: str
    pairs: list[str]
    start_time: time
    end_time: time


SESSIONS = [
    Session("london", ["EURUSD", "GBPUSD"], time(8, 0), time(9, 30)),
    Session("ny", ["EURUSD", "GBPUSD", "USDJPY", "EURJPY"], time(14, 30), time(16, 0)),
]


def get_current_session() -> Optional[Session]:
    now = datetime.utcnow().time()
    for session in SESSIONS:
        if session.start_time <= now < session.end_time:
            return session
    return None


def get_current_pair(session: Session, utc_now: datetime) -> Optional[str]:
    london = SESSIONS[0]
    ny = SESSIONS[1]

    london_start = utc_now.replace(hour=8, minute=0, second=0, microsecond=0)
    london_end = utc_now.replace(hour=10, minute=0, second=0, microsecond=0)
    ny_start = utc_now.replace(hour=14, minute=30, second=0, microsecond=0)
    ny_end = utc_now.replace(hour=16, minute=30, second=0, microsecond=0)

    if utc_now >= london_start and utc_now < london_end:
        minutes_in = int((utc_now - london_start).total_seconds() / 60)
        pair_index = minutes_in // 5
        if pair_index < len(london.pairs):
            return london.pairs[pair_index]
        return None

    if utc_now >= ny_start and utc_now < ny_end:
        minutes_in = int((utc_now - ny_start).total_seconds() / 60)
        pair_index = minutes_in // 5
        if pair_index < len(ny.pairs):
            return ny.pairs[pair_index]
        return None

    return None


def session_seconds_remaining(session: Session, utc_now: datetime) -> int:
    if session.name == "london":
        end = utc_now.replace(hour=10, minute=0, second=0, microsecond=0)
    else:
        end = utc_now.replace(hour=16, minute=30, second=0, microsecond=0)
    return max(0, int((end - utc_now).total_seconds()))


def candle_countdown(utc_now: datetime) -> int:
    minute = utc_now.minute
    second = utc_now.second
    seconds_into_candle = (minute % 5) * 60 + second
    return 300 - seconds_into_candle


def get_session_start_dt(session: Session, utc_now: datetime) -> datetime:
    """Get today's session start datetime."""
    if session.name == "london":
        return utc_now.replace(hour=8, minute=0, second=0, microsecond=0)
    else:
        return utc_now.replace(hour=14, minute=30, second=0, microsecond=0)


def get_session_end_dt(session: Session, utc_now: datetime) -> datetime:
    """Get today's session end datetime."""
    if session.name == "london":
        return utc_now.replace(hour=10, minute=0, second=0, microsecond=0)
    else:
        return utc_now.replace(hour=16, minute=30, second=0, microsecond=0)
