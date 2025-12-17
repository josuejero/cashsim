from importlib import import_module

from .analytics.break_even import break_even_grid
from .analytics.snapshot import monthly_snapshot
from .models import IOU, Bill, CreditCard, Dials, InvestmentSettings, OneOff
from .sim.core import simulate_month
from .sim.types import SimMetrics

__all__ = [
    "Bill",
    "CreditCard",
    "IOU",
    "OneOff",
    "InvestmentSettings",
    "Dials",
    "simulate_month",
    "SimMetrics",
    "break_even_grid",
    "monthly_snapshot",
]


def __getattr__(
    name: str,
) -> Bill | CreditCard | IOU | OneOff | InvestmentSettings | Dials | SimMetrics | type:
    if name in {"Bill", "CreditCard", "IOU", "OneOff", "InvestmentSettings", "Dials"}:
        m = import_module(".models", __name__)
        return getattr(m, name)

    if name == "simulate_month":
        return import_module(".sim.core", __name__).simulate_month
    if name == "SimMetrics":
        return import_module(".sim.types", __name__).SimMetrics

    if name == "break_even_grid":
        return import_module(".analytics.break_even", __name__).break_even_grid
    if name == "monthly_snapshot":
        return import_module(".analytics.snapshot", __name__).monthly_snapshot
    raise AttributeError(name)
