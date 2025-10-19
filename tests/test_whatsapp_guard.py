from datetime import datetime, timedelta, timezone

from app.channels.whatsapp_guard import WhatsAppGuard, InMemoryStore, Clock


class FrozenClock(Clock):
    def __init__(self, t0: datetime):
        self._now = t0

    def now(self) -> datetime:
        return self._now

    def travel(self, delta: timedelta):
        self._now = self._now + delta


def _t0():
    # Use a fixed, timezone-aware start time for deterministic tests
    return datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_freeform_allowed_strictly_within_24h():
    clk = FrozenClock(_t0())
    guard = WhatsAppGuard(store=InMemoryStore(), clock=clk)
    user = "u1"

    # No window yet
    assert guard.can_send_freeform(user) is False

    # User messages -> open window
    guard.record_incoming(user, ts_utc=clk.now())
    assert guard.can_send_freeform(user) is True

    # 23h59m59s still allowed
    clk.travel(timedelta(hours=23, minutes=59, seconds=59))
    assert guard.can_send_freeform(user) is True

    # exactly 24h -> blocked
    clk.travel(timedelta(seconds=1))
    assert guard.can_send_freeform(user) is False


def test_template_requires_opt_in_outside_window():
    clk = FrozenClock(_t0())
    guard = WhatsAppGuard(store=InMemoryStore(), clock=clk)
    user = "u2"

    # outside window, no opt-in: template blocked
    d1 = guard.decision(user, is_template=True)
    assert d1["allow"] is False
    assert d1["reason"] == "no_opt_in"

    # add opt-in -> allowed
    guard.set_opt_in(user, True)
    d2 = guard.decision(user, is_template=True)
    assert d2["allow"] is True
    assert d2["reason"] == "template_requires_opt_in"
    assert d2["has_opt_in"] is True


def test_template_and_freeform_inside_window():
    clk = FrozenClock(_t0())
    guard = WhatsAppGuard(store=InMemoryStore(), clock=clk)
    user = "u3"

    guard.record_incoming(user, ts_utc=clk.now())
    # Inside 24h: both freeform and template are okay
    assert guard.can_send_freeform(user) is True
    assert guard.can_send_template(user) is True
    d = guard.decision(user, is_template=False)
    assert d["allow"] is True and d["reason"] == "freeform_within_window"


def test_reopen_window_on_new_incoming():
    clk = FrozenClock(_t0())
    guard = WhatsAppGuard(store=InMemoryStore(), clock=clk)
    user = "u4"

    guard.record_incoming(user, ts_utc=clk.now())
    clk.travel(timedelta(hours=24, seconds=1))
    assert guard.can_send_freeform(user) is False

    # New inbound from user -> window reopens
    guard.record_incoming(user, ts_utc=clk.now())
    assert guard.can_send_freeform(user) is True


def test_opt_in_toggle_and_boundaries():
    clk = FrozenClock(_t0())
    guard = WhatsAppGuard(store=InMemoryStore(), clock=clk)
    user = "u5"

    # Toggle opt-in
    guard.set_opt_in(user, True)
    assert guard.has_opt_in(user) is True
    guard.set_opt_in(user, False)
    assert guard.has_opt_in(user) is False

    # With no window and no opt-in, freeform and template are blocked
    assert guard.can_send_freeform(user) is False
    assert guard.can_send_template(user) is False

    # With opt-in, template allowed outside window; freeform still blocked
    guard.set_opt_in(user, True)
    assert guard.can_send_template(user) is True
    assert guard.can_send_freeform(user) is False
