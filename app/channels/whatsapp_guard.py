from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Protocol


# ---- Time source injection for testability ----------------------------------

class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        # Always use aware UTC timestamps internally
        return datetime.now(timezone.utc)


# ---- Storage abstraction -----------------------------------------------------

@dataclass
class SessionState:
    last_incoming_utc: Optional[datetime] = None
    has_opt_in: bool = False


class InMemoryStore:
    """Simple per-user state store. Replace with DB/cache in production."""
    def __init__(self) -> None:
        self._state: Dict[str, SessionState] = {}

    def get(self, user_id: str) -> SessionState:
        if user_id not in self._state:
            self._state[user_id] = SessionState()
        return self._state[user_id]

    def set_opt_in(self, user_id: str, value: bool) -> None:
        self.get(user_id).has_opt_in = value

    def set_last_incoming(self, user_id: str, ts: datetime) -> None:
        self.get(user_id).last_incoming_utc = ts


# ---- Guard policy ------------------------------------------------------------

@dataclass
class WhatsAppGuard:
    """
    Enforces WhatsApp Business policy:
      - Free-form messages allowed only within 24h of last *user* message.
      - Outside 24h: only approved templates, and only if user has opted in.
    """
    store: InMemoryStore = field(default_factory=InMemoryStore)
    clock: Clock = field(default_factory=SystemClock)
    session_window: timedelta = field(default=timedelta(hours=24))

    # -- event hooks -----------------------------------------------------------

    def record_incoming(self, user_id: str, ts_utc: Optional[datetime] = None) -> None:
        """Call when the user sends an inbound message (opens/refreshes window)."""
        ts = ts_utc or self.clock.now()
        if ts.tzinfo is None:
            raise ValueError("record_incoming requires timezone-aware UTC datetime")
        self.store.set_last_incoming(user_id, ts)

    def set_opt_in(self, user_id: str, value: bool) -> None:
        self.store.set_opt_in(user_id, value)

    # -- checks ----------------------------------------------------------------

    def _last_incoming(self, user_id: str) -> Optional[datetime]:
        return self.store.get(user_id).last_incoming_utc

    def _within_service_window(self, user_id: str, now: Optional[datetime] = None) -> bool:
        now_ = now or self.clock.now()
        last = self._last_incoming(user_id)
        if last is None:
            return False
        # Strictly less than 24h allowed; >=24h blocked for free-form.
        return (now_ - last) < self.session_window

    def has_opt_in(self, user_id: str) -> bool:
        return self.store.get(user_id).has_opt_in

    # -- policy API ------------------------------------------------------------

    def can_send_freeform(self, user_id: str, now: Optional[datetime] = None) -> bool:
        """True iff within 24h window."""
        return self._within_service_window(user_id, now=now)

    def can_send_template(self, user_id: str, now: Optional[datetime] = None) -> bool:
        """
        Outside 24h: need explicit opt-in to initiate with a template.
        Inside 24h: templates are also fine (but not necessary).
        """
        if self._within_service_window(user_id, now=now):
            return True
        return self.has_opt_in(user_id)

    def decision(self, user_id: str, is_template: bool, now: Optional[datetime] = None) -> Dict[str, object]:
        """
        Returns a structured decision object:
          { "allow": bool, "reason": str, "within_24h": bool, "has_opt_in": bool }
        """
        within = self._within_service_window(user_id, now=now)
        opted = self.has_opt_in(user_id)
        if is_template:
            allow = within or opted
            reason = "template_ok_within_window" if within else ("template_requires_opt_in" if opted else "no_opt_in")
        else:
            allow = within
            reason = "freeform_within_window" if within else "outside_24h_requires_template"
        return {
            "allow": allow,
            "reason": reason,
            "within_24h": within,
            "has_opt_in": opted,
        }
