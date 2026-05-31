"""
SLO Calculator - Computes error budgets and burn rates
following Google SRE Book multi-window methodology.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SLOConfig:
    name: str
    target: float   # e.g. 0.999 for 99.9%
    window_days: int = 30


@dataclass
class ErrorBudget:
    total_minutes: float
    consumed_minutes: float
    remaining_minutes: float
    remaining_percent: float
    burn_rate: float
    is_exhausted: bool


class SLOCalculator:
    """Calculate SLO compliance and error budget metrics."""

    def __init__(self, config: SLOConfig):
        self.config = config

    def calculate_error_budget(self, good_events: int, total_events: int) -> ErrorBudget:
        """
        Calculate error budget from event counts.

        Args:
            good_events: Count of successful/good events
            total_events: Total event count

        Returns:
            ErrorBudget with current consumption and burn rate
        """
        if total_events == 0:
            raise ValueError("total_events cannot be zero")

        window_minutes = self.config.window_days * 24 * 60
        allowed_downtime = (1 - self.config.target) * window_minutes
        current_error_rate = (total_events - good_events) / total_events
        consumed = current_error_rate * window_minutes
        remaining = allowed_downtime - consumed
        remaining_pct = (remaining / allowed_downtime) * 100 if allowed_downtime > 0 else 0
        allowed_rate = 1 - self.config.target
        burn_rate = current_error_rate / allowed_rate if allowed_rate > 0 else 0

        return ErrorBudget(
            total_minutes=allowed_downtime,
            consumed_minutes=consumed,
            remaining_minutes=remaining,
            remaining_percent=remaining_pct,
            burn_rate=burn_rate,
            is_exhausted=remaining <= 0,
        )

    def multi_window_alert(
        self,
        short_burn: float,
        long_burn: float,
        page_threshold: float = 14.4,
        ticket_threshold: float = 1.0,
    ) -> dict:
        """
        Google SRE multi-window burn rate alerting.
        Short window catches fast burns; long window catches slow burns.
        """
        if short_burn > page_threshold and long_burn > page_threshold:
            severity = "page"
            message = f"Critical: burning error budget at {short_burn:.1f}x rate"
        elif short_burn > ticket_threshold:
            severity = "ticket"
            message = f"Warning: elevated burn rate {short_burn:.1f}x"
        else:
            severity = "none"
            message = "SLO healthy"

        return {
            "severity": severity,
            "message": message,
            "short_burn": short_burn,
            "long_burn": long_burn,
        }


if __name__ == "__main__":
    config = SLOConfig(name="api-availability", target=0.999, window_days=30)
    calc = SLOCalculator(config)
    budget = calc.calculate_error_budget(good_events=99850, total_events=100000)
    print(f"Error budget remaining: {budget.remaining_percent:.1f}%")
    print(f"Burn rate: {budget.burn_rate:.2f}x")
    print(f"Budget exhausted: {budget.is_exhausted}")

    alert = calc.multi_window_alert(short_burn=2.3, long_burn=1.8)
    print(f"Alert: [{alert['severity']}] {alert['message']}")
