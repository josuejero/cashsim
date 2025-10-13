from __future__ import annotations

import pandas as pd
import streamlit as st


def number_dials():
    col1, col2 = st.columns(2)
    col1.number_input("current cash", min_value=0.0, step=50.0, key="current_cash")
    col2.number_input("safety cushion", min_value=0.0, step=25.0, key="safety_cushion")
    col3, col4 = st.columns(2)
    col3.number_input("daily earnings", min_value=0.0, step=10.0, key="weekday_earnings")
    col4.number_input(
        "gas % of earnings (0-1)", min_value=0.0, max_value=1.0, step=0.05, key="gas_pct"
    )
    st.number_input("gas fill-up size", min_value=1.0, step=1.0, key="gas_fill_size")


def strategy_toggles():
    st.selectbox(
        "Interest calculation",
        ["statement_adb", "due_simple"],
        key="interest_mode",
        help="ADB posts at statement close; 'due_simple' posts on due date.",
    )
    st.selectbox(
        "Extra payment strategy",
        ["avalanche", "snowball"],
        key="extra_strategy",
        help="Avalanche = highest APR first; Snowball = smallest balance first.",
    )


def bills_editor(df: pd.DataFrame, key="bill_editor") -> pd.DataFrame:
    return st.data_editor(
        df,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "name": st.column_config.TextColumn("name"),
            "usual_day": st.column_config.NumberColumn(
                "usual day (1-31)", min_value=1, max_value=31
            ),
            "amount": st.column_config.NumberColumn("amount", min_value=0.0, step=1.0),
        },
        key=key,
    )


def cc_editor(df: pd.DataFrame, key="cc_editor") -> pd.DataFrame:
    return st.data_editor(
        df,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "name": st.column_config.TextColumn("name"),
            "apr": st.column_config.NumberColumn(
                "APR (decimal)", min_value=0.0, max_value=1.0, step=0.0001
            ),
            "balance": st.column_config.NumberColumn("balance", min_value=0.0, step=1.0),
            "due_day": st.column_config.NumberColumn("due day (1-31)", min_value=1, max_value=31),
            "min_pct": st.column_config.NumberColumn(
                "min % (0-1)", min_value=0.0, max_value=1.0, step=0.001
            ),
            "min_floor": st.column_config.NumberColumn("min floor", min_value=0.0, step=1.0),
            "statement_day": st.column_config.NumberColumn(
                "statement day (opt)", min_value=1, max_value=31
            ),
        },
        key=key,
    )


def iou_editor(df: pd.DataFrame, key="iou_editor") -> pd.DataFrame:
    return st.data_editor(
        df,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "name": st.column_config.TextColumn("name"),
            "balance": st.column_config.NumberColumn("balance", min_value=0.0, step=1.0),
            "apr": st.column_config.NumberColumn(
                "APR (decimal)", min_value=0.0, max_value=1.0, step=0.0001
            ),
            "due_day": st.column_config.NumberColumn("due day (opt)", min_value=1, max_value=31),
            "min_pct": st.column_config.NumberColumn(
                "min % (0-1)", min_value=0.0, max_value=1.0, step=0.001
            ),
            "min_floor": st.column_config.NumberColumn("min floor", min_value=0.0, step=1.0),
        },
        key=key,
    )


def oneoff_editor(df: pd.DataFrame, key="oneoff_editor") -> pd.DataFrame:
    return st.data_editor(
        df,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "name": st.column_config.TextColumn("name"),
            "due_date": st.column_config.DateColumn("due date"),
            "amount": st.column_config.NumberColumn("amount", min_value=0.0, step=1.0),
            "priority": st.column_config.NumberColumn(
                "priority (higher=faster)", min_value=0, max_value=99, step=1
            ),
            "must_pay": st.column_config.CheckboxColumn("must pay?"),
        },
        key=key,
    )
