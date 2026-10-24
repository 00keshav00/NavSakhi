"""
NavSakhi - Phase 47: Robust OpenStreetMap Opening Hours Parser & Evaluator.

Evaluates whether a point of interest (POI) is OPEN, CLOSED, or UNKNOWN at an
estimated pass-through datetime.

Strict Guarantees:
- Never treats missing, invalid, or unsupported syntax as OPEN.
- Supports 24/7, weekday ranges, day lists, multiple daily shifts, and overnight intervals (e.g., 20:00-03:00).
- Properly accounts for previous-day overnight spillover into the early morning hours.
- Handles explicit 'closed' / 'off' rules and public holiday ('PH') tokens safely.
"""

from enum import Enum
import re
import datetime
from typing import Optional, List, Tuple, Dict

class OpeningStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"

DAYS_ORDER = ["mo", "tu", "we", "th", "fr", "sa", "su"]
DAY_INDEX = {d: i for i, d in enumerate(DAYS_ORDER)}

DAY_NAME_MAP = {
    "mo": "mo", "mon": "mo", "monday": "mo",
    "tu": "tu", "tue": "tu", "tuesday": "tu",
    "we": "we", "wed": "we", "wednesday": "we",
    "th": "th", "thu": "th", "thursday": "th",
    "fr": "fr", "fri": "fr", "friday": "fr",
    "sa": "sa", "sat": "sa", "saturday": "sa",
    "su": "su", "sun": "su", "sunday": "su",
}

def _parse_time_minutes(t_str: str) -> Optional[int]:
    """Parses 'HH:MM' or 'H:MM' or 'HH' into minutes from midnight (0-1440)."""
    t_str = t_str.strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", t_str)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        if 0 <= hh <= 24 and 0 <= mm < 60:
            return hh * 60 + mm
    m_hour_only = re.match(r"^(\d{1,2})$", t_str)
    if m_hour_only:
        hh = int(m_hour_only.group(1))
        if 0 <= hh <= 24:
            return hh * 60
    return None

def _expand_days(day_token: str) -> List[str]:
    """Expands day expressions like 'Mo-Fr', 'Sa,Su', 'Mo-Su', 'PH' into list of 2-letter day codes."""
    days = []
    tokens = [t.strip().lower() for t in day_token.split(",") if t.strip()]
    for token in tokens:
        if token in ["ph", "sh"]:
            # Public/school holidays handled safely
            continue
        if "-" in token:
            parts = token.split("-")
            if len(parts) == 2:
                d1 = DAY_NAME_MAP.get(parts[0].strip())
                d2 = DAY_NAME_MAP.get(parts[1].strip())
                if d1 and d2:
                    i1, i2 = DAY_INDEX[d1], DAY_INDEX[d2]
                    if i1 <= i2:
                        days.extend(DAYS_ORDER[i1 : i2 + 1])
                    else:
                        # Wrap around (e.g. Fr-Mo)
                        days.extend(DAYS_ORDER[i1:] + DAYS_ORDER[: i2 + 1])
                    continue
        canon = DAY_NAME_MAP.get(token)
        if canon:
            days.append(canon)
    return list(dict.fromkeys(days))

class ParsedSchedule:
    def __init__(self, raw: str):
        self.raw = raw
        self.is_24_7 = False
        self.is_permanently_closed = False
        # Map: day_code -> list of (start_min, end_min, is_closed_interval)
        self.day_rules: Dict[str, List[Tuple[int, int, bool]]] = {d: [] for d in DAYS_ORDER}
        self.has_valid_rules = False
        self._parse(raw)

    def _parse(self, raw: str):
        cleaned = raw.strip()
        if not cleaned:
            return

        norm = cleaned.lower()
        if norm in ["24/7", "open 24/7", "24 hours", "00:00-24:00", "mo-su 00:00-24:00"]:
            self.is_24_7 = True
            self.has_valid_rules = True
            return

        if norm in ["closed", "off"]:
            self.is_permanently_closed = True
            self.has_valid_rules = True
            return

        # Split semi-colon separated rules
        sections = [s.strip() for s in cleaned.split(";") if s.strip()]
        any_section_parsed = False

        for section in sections:
            # Check for off / closed rules, e.g. "Su off", "Su closed"
            off_match = re.search(r"^(.*?)\s*(?:off|closed)$", section, re.IGNORECASE)
            if off_match:
                day_part = off_match.group(1).strip()
                target_days = _expand_days(day_part) if day_part else DAYS_ORDER
                for d in target_days:
                    self.day_rules[d].append((0, 1440, True))
                any_section_parsed = True
                continue

            m = re.match(r"^([A-Za-z\s,\-]+?)?\s*(\d{1,2}(?::\d{2})?\s*-\s*\d{1,2}(?::\d{2})?(?:.*))?$", section)
            if not m:
                continue

            day_part = (m.group(1) or "").strip()
            time_part = (m.group(2) or "").strip()

            if day_part:
                target_days = _expand_days(day_part)
                if not target_days and not time_part:
                    continue
                if not target_days and time_part:
                    continue
            else:
                target_days = DAYS_ORDER

            if not time_part:
                continue

            range_tokens = [rt.strip() for rt in time_part.split(",") if rt.strip()]
            for r_token in range_tokens:
                rm = re.match(r"^(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)(?:\s*(off|closed))?$", r_token, re.IGNORECASE)
                if not rm:
                    continue
                t_start = _parse_time_minutes(rm.group(1))
                t_end = _parse_time_minutes(rm.group(2))
                is_off = bool(rm.group(3))

                if t_start is None or t_end is None:
                    continue

                if t_end <= t_start:
                    t_end += 1440

                for d in target_days:
                    self.day_rules[d].append((t_start, t_end, is_off))
                any_section_parsed = True

        self.has_valid_rules = any_section_parsed

    def evaluate(self, dt: datetime.datetime) -> OpeningStatus:
        if not self.has_valid_rules:
            return OpeningStatus.UNKNOWN

        if self.is_24_7:
            return OpeningStatus.OPEN

        if self.is_permanently_closed:
            return OpeningStatus.CLOSED

        weekday = dt.weekday()
        cur_day = DAYS_ORDER[weekday]
        prev_day = DAYS_ORDER[(weekday - 1) % 7]
        cur_minute = dt.hour * 60 + dt.minute

        # 1. Check overnight spillover from previous day
        for start_m, end_m, is_off in self.day_rules[prev_day]:
            if end_m > 1440:
                spillover_end = end_m - 1440
                if 0 <= cur_minute < spillover_end:
                    return OpeningStatus.CLOSED if is_off else OpeningStatus.OPEN

        # 2. Check current day's rules
        rules = self.day_rules[cur_day]
        if not rules:
            has_any_day_rules = any(len(r) > 0 for r in self.day_rules.values())
            return OpeningStatus.CLOSED if has_any_day_rules else OpeningStatus.UNKNOWN

        matched_open = False
        matched_closed = False

        for start_m, end_m, is_off in rules:
            if start_m <= cur_minute < end_m:
                if is_off:
                    matched_closed = True
                else:
                    matched_open = True

        if matched_open and not matched_closed:
            return OpeningStatus.OPEN
        elif matched_closed:
            return OpeningStatus.CLOSED
        else:
            return OpeningStatus.CLOSED

def evaluate_opening_hours(raw_hours: Optional[str], check_time: Optional[datetime.datetime] = None) -> OpeningStatus:
    """
    Evaluates whether raw OSM opening_hours is OPEN, CLOSED, or UNKNOWN at check_time.
    If check_time is omitted, defaults to UTC now.
    """
    if not raw_hours or not isinstance(raw_hours, str) or not raw_hours.strip():
        return OpeningStatus.UNKNOWN

    if check_time is None:
        check_time = datetime.datetime.now(datetime.timezone.utc)

    try:
        schedule = ParsedSchedule(raw_hours)
        return schedule.evaluate(check_time)
    except Exception:
        return OpeningStatus.UNKNOWN
