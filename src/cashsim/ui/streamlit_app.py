from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from cashsim.analytics.break_even import break_even_grid
from cashsim.analytics.snapshot import monthly_snapshot
from cashsim.io.config_io import load_config, save_config
from cashsim.io.gsheets import read_wishlist_by_url  # Google Sheets integration
from cashsim.models import Dials
from cashsim.planning.planner import (
    constant_target_from_schedule,
    plan_min_daily_earnings,
    plan_variable_daily_earnings,
)
from cashsim.sim.core import simulate_month
from cashsim.sim.types import SimMetrics
from cashsim.ui.components import (
    bills_editor,
    cc_editor,
    iou_editor,
    number_dials,
    oneoff_editor,
    strategy_toggles,
)
from cashsim.ui.formatters import stringify_events_columns
from cashsim.ui.state import dials_from_state, init_session_once
from cashsim.utils.date_utils import next_due_date_cached as next_due_date

# Pandas CoW: future-proof semantics and fewer hidden copies
pd.options.mode.copy_on_write = True

st.set_page_config(page_title="CashSim — Single Page", layout="wide")
init_session_once()


# ------------------
# Helpers & caching
# ------------------
def _fingerprint(dials: Dials) -> str:
    """
    Stable, JSON-serializable fingerprint for Streamlit caching.
    Use pydantic v2's mode='json' so dates become ISO strings.
    """
    payload = dials.model_dump(mode="json")
    return json.dumps(payload, sort_keys=True)


@st.cache_data(show_spinner=False)
def run_sim(dials_json: str, start: date, days: int) -> tuple[pd.DataFrame, SimMetrics]:
    d = Dials.model_validate_json(dials_json)
    return simulate_month(d, start=start, days=days)


@st.cache_data(show_spinner=False)
def run_break_even(dials_json: str, days: int = 31) -> pd.DataFrame:
    d = Dials.model_validate_json(dials_json)
    candidates = [float(i) for i in range(0, 201)]
    return break_even_grid(d, candidates, days=days)


@st.cache_data(show_spinner=False)
def _load_config_cached(path: str, mtime: float) -> Dials:
    # mtime participates in the cache key so reads are invalidated when the file changes
    return load_config(path)


# ------------------
# Title & Tabs
# ------------------
st.title("CashSim (single-page)")
st.caption(
    "Edit inputs, bills, debt, and one-offs — then simulate and analyze break-even, "
    "and plan a daily target — all here."
)

tab_inputs, tab_bills, tab_debt, tab_oneoffs, tab_sim, tab_analytics, tab_planner, tab_wishlist = (
    st.tabs(
        ["Inputs", "Bills", "Debt", "One-offs", "Simulation", "Analytics", "Planner", "Wishlist"]
    )
)

# ------------------
# Inputs
# ------------------
with tab_inputs:
    st.header("Inputs")
    st.subheader("Config I/O")

    cfg_path = st.text_input("path", value="config.json")
    c1, c2, _ = st.columns([1, 1, 1])

    if c1.button("Load file", width="stretch"):
        try:
            mtime = os.path.getmtime(cfg_path) if os.path.exists(cfg_path) else 0.0
            d = _load_config_cached(cfg_path, mtime)
            # Hydrate session state from config
            st.session_state.update(
                {
                    "current_cash": float(d.current_cash),
                    "safety_cushion": float(d.safety_cushion),
                    "weekday_earnings": float(d.weekday_earnings),
                    "gas_pct": float(d.gas_pct),
                    "gas_fill_size": float(d.gas_fill_size),
                    "bill_table": pd.DataFrame([b.model_dump() for b in d.bills]),
                    "cc_table": pd.DataFrame([c.model_dump() for c in d.credit_cards]),
                    "iou_table": pd.DataFrame([x.model_dump() for x in d.ious]),
                    "oneoff_table": pd.DataFrame([o.model_dump() for o in d.oneoffs]),
                    "interest_mode": d.interest_mode,
                    "extra_strategy": d.extra_strategy,
                    "invest": d.invest.model_dump(),
                    # Ensure datetime64[ns] dtype for blackouts editor
                    "blackouts_df": pd.DataFrame(
                        {"date": pd.to_datetime(getattr(d, "blackouts", []), errors="coerce")}
                    ),
                }
            )
            st.rerun()
        except Exception as e:
            st.error(str(e))

    uploaded = st.file_uploader("or upload json", type="json")
    if uploaded is not None:
        try:
            data = json.load(uploaded)
            d = Dials.model_validate(data)
            st.session_state.update(
                {
                    "current_cash": float(d.current_cash),
                    "safety_cushion": float(d.safety_cushion),
                    "weekday_earnings": float(d.weekday_earnings),
                    "gas_pct": float(d.gas_pct),
                    "gas_fill_size": float(d.gas_fill_size),
                    "bill_table": pd.DataFrame([b.model_dump() for b in d.bills]),
                    "cc_table": pd.DataFrame([c.model_dump() for c in d.credit_cards]),
                    "iou_table": pd.DataFrame([x.model_dump() for x in d.ious]),
                    "oneoff_table": pd.DataFrame([o.model_dump() for o in d.oneoffs]),
                    "interest_mode": d.interest_mode,
                    "extra_strategy": d.extra_strategy,
                    "invest": d.invest.model_dump(),
                    "blackouts_df": pd.DataFrame(
                        {"date": pd.to_datetime(getattr(d, "blackouts", []), errors="coerce")}
                    ),
                }
            )
            st.rerun()
        except Exception as e:
            st.error(str(e))

    # Prepare a Dials for download/save that includes blackouts even if
    # ui.state.dials_from_state() doesn't
    def _dials_with_blackouts() -> Dials:
        base = dials_from_state()
        # Pull editor dates and coerce to date objects
        bdf = st.session_state.get("blackouts_df", pd.DataFrame({"date": []})).copy()
        if "date" not in bdf.columns:
            bdf["date"] = pd.Series([], dtype="datetime64[ns]")
        dates: list[date] = []
        for v in pd.to_datetime(bdf["date"], errors="coerce"):
            if pd.notna(v):
                dates.append(pd.to_datetime(v).date())
        return base.model_copy(update={"blackouts": dates})

    st.download_button(
        "Download current config",
        data=_dials_with_blackouts().model_dump_json(indent=2),
        file_name="config.json",
        mime="application/json",
    )

    if c2.button("Save file", width="stretch"):
        try:
            save_config(_dials_with_blackouts(), cfg_path)
            st.success(f"Saved {cfg_path}")
        except Exception as e:
            st.error(str(e))

    st.divider()
    number_dials()
    strategy_toggles()

# ------------------
# Bills
# ------------------
with tab_bills:
    st.header("Bills")
    st.session_state["bill_table"] = bills_editor(st.session_state["bill_table"])

    today = date.today()
    dials_tmp = dials_from_state()
    bills_rows = []
    for b in dials_tmp.bills:
        nd = next_due_date(today, b.usual_day)
        bills_rows.append(
            {
                "type": "bill",
                "name": b.name,
                "next_due": nd,
                "days_remaining": (nd - today).days,
                "amount": round(b.amount, 2),
            }
        )

    cc_rows = []
    for c in dials_tmp.credit_cards:
        due = next_due_date(today, c.due_day)
        est_min = round(max(c.min_floor, c.balance * c.min_pct), 2)
        cc_rows.append(
            {
                "type": "cc_min",
                "name": f"{c.name} (min)",
                "next_due": due,
                "days_remaining": (due - today).days,
                "amount": est_min,
            }
        )

    rolled_df = pd.DataFrame(bills_rows + cc_rows).sort_values(
        ["next_due", "type", "name"], kind="mergesort"
    )
    st.subheader("Rolled-forward preview (bills + estimated CC mins)")
    st.dataframe(rolled_df, width="stretch", hide_index=True)
    st.caption(
        "CC minimums here are estimates from current balances; "
        "actual mins are locked from statement balances."
    )

# ------------------
# Debt (CC + IOU) and upcoming events
# ------------------
with tab_debt:
    st.header("Credit cards & IOUs")
    st.session_state["cc_table"] = cc_editor(st.session_state["cc_table"])
    st.session_state["iou_table"] = iou_editor(st.session_state["iou_table"])

    st.subheader("Upcoming due-date events (interest postings, minimums, extras)")
    dials = dials_from_state()
    fingerprint = _fingerprint(dials)
    sim_df, _ = run_sim(fingerprint, date.today(), 60)
    ev = sim_df.explode("cc_events", ignore_index=True)
    if bool("cc_events" in ev.columns and ev["cc_events"].notna().any()):
        base = ev.loc[ev["cc_events"].notna(), ["date", "cc_events"]].reset_index(drop=True)
        events_df = pd.json_normalize(base["cc_events"].tolist()).reset_index(drop=True)
        if "date" in events_df.columns:
            events_df = events_df.rename(columns={"date": "event_date"})
        events_df.insert(0, "date", base["date"].reset_index(drop=True))
        events_df = events_df.loc[:, ~events_df.columns.duplicated()]
        pref = [
            "date",
            "account",
            "finance_charge",
            "minimum_paid",
            "extra_paid",
            "new_balance",
            "surplus_used",
            "reserve_needed",
            "reserve_7d_bills",
            "reserve_7d_mins",
            "reserve_7d_gas",
            "event_date",
        ]
        cols = [c for c in pref if c in events_df.columns]
        st.dataframe(events_df[cols], width="stretch", hide_index=True)
    else:
        st.write("No due-date events within 60 days.")

# ------------------
# One-offs (sinking)
# ------------------
with tab_oneoffs:
    st.header("One-off (sinking) expenses")
    st.session_state["oneoff_table"] = oneoff_editor(st.session_state["oneoff_table"])

    st.subheader("Contributions & payments (next 60 days)")
    dials = dials_from_state()
    fingerprint = _fingerprint(dials)
    sim_df, _ = run_sim(fingerprint, date.today(), 60)

    events: list[dict[str, Any]] = []
    for _, r in sim_df.iterrows():
        for item in r.get("oneoff_contribs") or []:
            try:
                name, amt = item
            except Exception:
                name, amt = str(item), float("nan")
            events.append({"date": r["date"], "event": "contrib", "name": name, "amount": amt})
        for item in r.get("oneoff_paid") or []:
            try:
                name, amt = item
            except Exception:
                name, amt = str(item), float("nan")
            events.append({"date": r["date"], "event": "paid", "name": name, "amount": amt})

    if events:
        oneoff_events_df = (
            pd.DataFrame(events).sort_values(["date", "event", "name"]).reset_index(drop=True)
        )
        st.dataframe(oneoff_events_df, width="stretch", hide_index=True)
    else:
        st.write("No one-off contributions or payments in the next 60 days.")

# ------------------
# Simulation
# ------------------
with tab_sim:
    st.header("Simulation")
    days = st.slider("days to simulate", min_value=28, max_value=186, value=31, step=1)
    dials = dials_from_state()
    fingerprint = _fingerprint(dials)
    sim_df, metrics = run_sim(fingerprint, date.today(), days)

    left, right = st.columns([1.2, 1.0])
    with left:
        st.subheader("Daily balance (projection)")
        st.line_chart(sim_df.set_index("date")[["balance"]], width="stretch")
        st.dataframe(stringify_events_columns(sim_df), width="stretch", hide_index=True)

    with right:
        st.subheader("Key results")
        st.metric("Min balance", f"${metrics.min_balance:,.2f}", help=str(metrics.min_balance_date))
        st.metric(
            "Overdraft date",
            "-" if metrics.first_negative_date is None else str(metrics.first_negative_date),
        )
        st.metric(
            "Cushion breach",
            "-" if metrics.cushion_breach_date is None else str(metrics.cushion_breach_date),
        )
        st.metric("Upcoming bills total (within horizon)", f"${metrics.total_upcoming_bills:,.2f}")
        st.metric("Est. unposted interest (cards)", f"${metrics.accrued_interest_estimate:,.2f}")

# ------------------
# Analytics
# ------------------
with tab_analytics:
    st.header("Analytics")
    dials = dials_from_state()

    st.subheader("Break-even daily earnings search (0–200)")
    fingerprint = _fingerprint(dials)
    be_df = run_break_even(fingerprint, days=31)
    st.dataframe(be_df, width="stretch", hide_index=True)

    st.subheader("Monthly snapshot (6 months)")
    snap = monthly_snapshot(dials, months=6)
    st.json(snap)

# ------------------
# Planner (with robust DateColumn handling for blackouts)
# ------------------
with tab_planner:
    st.header("Planner")

    dials = dials_from_state()
    mode = st.radio(
        "Mode",
        ["Constant daily target", "Day-by-day plan"],
        horizontal=True,
        key="planner_mode",
        help=(
            "Pick a single daily amount to avoid overdraft, "
            "or generate a daily schedule with caps/constraints."
        ),
    )

    if mode == "Constant daily target":
        st.subheader("Minimum constant daily earnings")
        days = st.slider(
            "days to satisfy (horizon)",
            min_value=28,
            max_value=186,
            value=60,
            step=1,
            key="planner_days_constant",
        )

        res_const = plan_min_daily_earnings(dials, days=days)
        if res_const.ok:
            st.success(
                f"Minimum constant daily earnings to avoid overdraft in {days} days: "
                f"${res_const.daily_target:,.2f}"
            )
            st.caption(
                f"Simulated min balance: ${res_const.min_balance:,.2f} "
                f"(first negative: {res_const.first_negative_date})"
            )
        else:
            st.error("Could not find a feasible daily target up to a very large upper bound.")

    else:
        st.subheader("Day-by-day earnings schedule")

        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        days = c1.slider(
            "Horizon (days)", min_value=28, max_value=186, value=60, step=1, key="planner_days_var"
        )
        safety_target = c2.selectbox(
            "Safety target",
            ["zero", "cushion"],
            index=0,
            key="planner_safety_target",
            help="Keep end-of-day ≥ 0 (zero) or ≥ your safety cushion (cushion).",
        )
        daily_cap_val = c3.number_input(
            "Daily cap (optional)",
            min_value=0.0,
            step=10.0,
            value=0.0,
            key="planner_cap",
            help="0 = no cap",
        )
        future_hint = c4.number_input(
            "Future daily earnings hint",
            min_value=0.0,
            step=10.0,
            value=float(dials.weekday_earnings),
            key="planner_future_hint",
            help="Used only to predict gas fill-ups in next-7-days reserve.",
        )
        cap = None if daily_cap_val <= 0 else float(daily_cap_val)

        # --- Blackouts editor (robust dtype handling) ---
        st.markdown("**No-drive dates** (add rows as needed)")
        st.session_state.setdefault(
            "blackouts_df", pd.DataFrame({"date": pd.Series([], dtype="datetime64[ns]")})
        )
        _blackouts = st.session_state["blackouts_df"].copy()
        if "date" not in _blackouts.columns:
            _blackouts["date"] = pd.Series([], dtype="datetime64[ns]")
        else:
            _blackouts["date"] = pd.to_datetime(_blackouts["date"], errors="coerce")

        st.session_state["blackouts_df"] = st.data_editor(
            _blackouts,
            num_rows="dynamic",
            column_config={"date": st.column_config.DateColumn("date", format="iso8601")},
            width="stretch",
            key="blackouts_editor",
        )

        planner_blackouts: list[date] = []
        for v in pd.to_datetime(st.session_state["blackouts_df"]["date"], errors="coerce"):
            if pd.notna(v):
                planner_blackouts.append(pd.to_datetime(v).date())

        res_var = plan_variable_daily_earnings(
            dials,
            days=days,
            safety_target="zero" if safety_target == "zero" else "cushion",
            daily_cap=cap,
            future_daily_hint=future_hint,
            blackout_dates=planner_blackouts,
        )
        df = pd.DataFrame([r.__dict__ for r in res_var.rows])
        st.metric(
            "Min projected balance",
            f"${res_var.min_balance:,.2f}",
            help=str(res_var.min_balance_date),
        )
        if not res_var.ok:
            st.warning("Plan hits the daily cap on at least one day ...")

        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])  # ensure datetime index for charts

            st.line_chart(
                df.set_index("date")[["earn_required", "earn_capped"]],
                width="stretch",
            )

            st.dataframe(
                df,
                width="stretch",
                hide_index=True,
                column_config={
                    "date": st.column_config.DateColumn("date", format="YYYY-MM-DD"),
                    "earn_required": st.column_config.NumberColumn("earn_required", format="$%.2f"),
                    "earn_capped": st.column_config.NumberColumn("earn_capped", format="$%.2f"),
                    "cap_exceeded": st.column_config.CheckboxColumn("cap_exceeded"),
                    "end_balance": st.column_config.NumberColumn("end_balance", format="$%.2f"),
                    "reserve_7d_total": st.column_config.NumberColumn(
                        "reserve_7d_total", format="$%.2f"
                    ),
                    "bills_today": st.column_config.NumberColumn("bills_today", format="$%.2f"),
                    "mins_today": st.column_config.NumberColumn("mins_today", format="$%.2f"),
                    "oneoffs_today": st.column_config.NumberColumn("oneoffs_today", format="$%.2f"),
                    "gas_fill_cost_today": st.column_config.NumberColumn(
                        "gas_fill_cost_today", format="$%.2f"
                    ),
                    "gas_bucket_end": st.column_config.NumberColumn(
                        "gas_bucket_end", format="$%.2f"
                    ),
                },
            )

            # constant target for working days
            const_target = constant_target_from_schedule(res_var.rows, planner_blackouts)
            st.metric(
                "Constant target on working days",
                f"${const_target:,.2f}",
                help=(
                    "Hit at least this number on each day you can drive to stay above your "
                    "chosen safety target."
                ),
            )
        else:
            st.info("No rows to display.")

# ------------------
# Wishlist (Google Sheets)
# ------------------
with tab_wishlist:
    st.header("Wishlist (Google Sheets)")

    st.markdown(
        "Store your **service account JSON** under `st.secrets['gcp_service_account']`.\n"
        "Share the Google Sheet with that service account’s **client_email**."
    )
    sheet_url = st.text_input("Sheet URL")
    ws_name = st.text_input("Worksheet name", value="Sheet1")
    horizon = st.slider("Planning horizon (days)", 30, 180, 120, 1)

    if st.button("Fetch & Predict"):
        try:
            sa = st.secrets["gcp_service_account"]
            wish = read_wishlist_by_url(sheet_url, ws_name, sa)
            st.subheader("Wishlist data")
            st.dataframe(wish, width="stretch", hide_index=True)

            # Build a day-by-day plan first (respecting blackouts)
            dials = dials_from_state()

            # Coerce blackouts dtype then extract
            bdf = st.session_state.get("blackouts_df", pd.DataFrame({"date": []})).copy()
            if "date" not in bdf.columns:
                bdf["date"] = pd.Series([], dtype="datetime64[ns]")
            else:
                bdf["date"] = pd.to_datetime(bdf["date"], errors="coerce")

            wishlist_blackouts: list[date] = []
            for v in bdf["date"]:
                if pd.notna(v):
                    wishlist_blackouts.append(pd.to_datetime(v).date())

            plan_for_wishlist = plan_variable_daily_earnings(
                dials,
                days=horizon,
                safety_target="zero",
                daily_cap=None,
                future_daily_hint=float(dials.weekday_earnings),
                blackout_dates=wishlist_blackouts,
            )
            plan_df = pd.DataFrame([r.__dict__ for r in plan_for_wishlist.rows])
            plan_df["date"] = pd.to_datetime(plan_df["date"])
            base = (
                0.0  # change to float(dials.safety_cushion) if you want cushion as the hard floor
            )
            plan_df["safe_surplus"] = (
                plan_df["end_balance"] - (base + plan_df["reserve_7d_total"])  # type: ignore[operator]
            ).round(2)

            # Greedy fund by Priority (higher first)
            items = wish.sort_values(["Priority", "Item"], ascending=[False, True]).to_dict(
                "records"
            )
            remaining = {it["Item"]: float(it["Price"]) for it in items}
            first_date = {it["Item"]: None for it in items}

            for _, r in plan_df.iterrows():
                avail = max(0.0, float(r["safe_surplus"]))
                if avail <= 0:
                    continue
                for it in items:
                    name = it["Item"]
                    if remaining[name] <= 0:
                        continue
                    take = min(avail, remaining[name])
                    remaining[name] = round(remaining[name] - take, 2)
                    avail = round(avail - take, 2)
                    if remaining[name] <= 0 and first_date[name] is None:
                        first_date[name] = r["date"].date()
                    if avail <= 0:
                        break

            out_rows = []
            today = date.today()
            for it in items:
                nm = it["Item"]
                when = first_date[nm]
                out_rows.append(
                    {
                        "Item": nm,
                        "Price": it["Price"],
                        "Priority": it["Priority"],
                        "Earliest fully-funded": when,
                        "Days until": None if when is None else (when - today).days,
                    }
                )
            out = pd.DataFrame(out_rows).sort_values(
                ["Earliest fully-funded", "Priority"], na_position="last", ascending=[True, False]
            )
            st.subheader("Earliest good buy dates (by priority)")
            st.dataframe(out, width="stretch", hide_index=True)
        except KeyError:
            st.error("Missing st.secrets['gcp_service_account']. See instructions below.")
        except Exception as e:
            st.error(str(e))
