from __future__ import annotations

from collections.abc import Iterable
from typing import cast

import pandas as pd


def stringify_events_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    def _fmt_pair_list(v: object) -> str:
        if isinstance(v, (list, tuple)) and len(v) > 0:
            try:
                pairs = cast(Iterable[tuple[str, float]], v)
                return "; ".join(f"{name}: ${float(amt):,.2f}" for (name, amt) in pairs)
            except Exception:
                return str(v)
        return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)

    for col in [
        "cc_extra_on_due",
        "cc_interest_posted",
        "cc_min_paid",
        "oneoff_contribs",
        "oneoff_paid",
    ]:
        if col in out.columns:
            out[col] = out[col].apply(_fmt_pair_list)
    return out
