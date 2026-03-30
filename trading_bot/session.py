"""Session window timing — DST-aware local time conversion to UTC."""
from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Optional
from zoneinfo import ZoneInfo


@dataclass
class Session:
    name: str
    pairs: list[str]
    start_time: time
    end_time: time
    tz: ZoneInfo


SESSIONS = [
    Session("london", ["EURUSD", "GBPUSD"], time(8, 0), time(9, 30), ZoneInfo("Europe/London")),
    Session("ny", ["EURUSD", "GBPUSD", "USDJPY", "EURJPY"], time(9, 30), time(11, 0), ZoneInfo("America/New_York")),
]


def _session_utc_times(session: Session, utc_now: datetime):
    utc_aware = utc_now.replace(tzinfo=timezone.utc) if utc_now.tzinfo is None else utc_now
    local_date = utc_aware.astimezone(session.tz).date()
    start_utc = datetime.combine(local_date, session.start_time, tzinfo=session.tz).astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = datetime.combine(local_date, session.end_time, tzinfo=session.tz).astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def get_current_session() -> Optional[Session]:
    now = datetime.utcnow()
    for session in SESSIONS:
        start_utc, end_utc = _session_utc_times(session, now)
        if start_utc <= now < end_utc:
            return session
    return None


def get_current_pair(session: Session, utc_now: datetime) -> Optional[str]:
    start_utc, end_utc = _session_utc_times(session, utc_now)
    if start_utc <= utc_now < end_utc:
        minutes_in = int((utc_now - start_utc).total_seconds() / 60)
        pair_index = minutes_in // 5
        if pair_index < len(session.pairs):
            return session.pairs[pair_index]
    return None


def session_seconds_remaining(session: Session, utc_now: datetime) -> int:
    _, end_utc = _session_utc_times(session, utc_now)
    return max(0, int((end_utc - utc_now).total_seconds()))


def candle_countdown(utc_now: datetime) -> int:
    minute = utc_now.minute
    second = utc_now.second
    seconds_into_candle = (minute % 5) * 60 + second
    return 300 - seconds_into_candle


def get_session_start_dt(session: Session, utc_now: datetime) -> datetime:
    start_utc, _ = _session_utc_times(session, utc_now)
    return start_utc


def get_session_end_dt(session: Session, utc_now: datetime) -> datetime:
    _, end_utc = _session_utc_times(session, utc_now)
    return end_utc
