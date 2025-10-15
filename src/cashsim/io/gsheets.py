from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import google.auth
import gspread
import pandas as pd
import streamlit as st
from google.auth.credentials import Credentials  # Application Default Credentials (ADC)
from google.oauth2 import service_account
from gspread_dataframe import (  # type: ignore[reportMissingTypeStubs]
    get_as_dataframe,
    set_with_dataframe,
)

from cashsim._typing_shims import cache_data, cache_resource

SHEETS_READONLY = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SHEETS_RW = ["https://www.googleapis.com/auth/spreadsheets"]


def _choose_creds(*, readonly: bool, sa_info: Mapping[str, Any] | None) -> Credentials:
    """Prefer st.secrets if provided; otherwise fall back to ADC (keyless on GCP)."""
    scopes = SHEETS_READONLY if readonly else SHEETS_RW
    if sa_info:
        return service_account.Credentials.from_service_account_info(dict(sa_info), scopes=scopes)
    if "gcp_service_account" in st.secrets:
        return service_account.Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
    creds, _ = google.auth.default(scopes=scopes)  # uses attached service account on GCP
    return creds


@cache_resource(show_spinner=False)
def gs_client(sa_info: Mapping[str, Any] | None = None, *, readonly: bool = True) -> gspread.Client:
    """Singleton gspread client; cached across reruns & sessions."""
    creds = _choose_creds(readonly=readonly, sa_info=sa_info)
    return gspread.authorize(creds)


# ---------- FAST READ: batch ranges in one HTTP call ----------
@cache_data(show_spinner=False)
def batch_read_values(
    sheet_url: str, ranges: list[str], sa_info: Mapping[str, Any] | None = None
) -> dict[str, list[list[Any]]]:
    """
    Read multiple A1 ranges across sheets in one call via values:batchGet.
    Returns {range: values}. Missing ranges return [].
    """
    sh: gspread.Spreadsheet = gs_client(sa_info, readonly=True).open_by_url(sheet_url)
    resp: dict[str, Any] = sh.values_batch_get(ranges)
    out: dict[str, list[list[Any]]] = {}
    for vr in resp.get("valueRanges", []):
        out[vr.get("range", "")] = vr.get("values", [])
    # ensure all requested ranges are present (possibly empty)
    for r in ranges:
        out.setdefault(r, [])
    return out


# ---------- FAST WRITE: batch updates in one HTTP call ----------
def batch_write_values(
    sheet_url: str,
    value_ranges: list[dict[str, Any]],
    *,
    value_input_option: str = "USER_ENTERED",
    sa_info: Mapping[str, Any] | None = None,
) -> dict:
    """
    Write multiple ranges in one call via values:batchUpdate.
    value_ranges = [{"range": "Sheet1!A1:B3", "values": [[...], ...]}, ...]
    """
    sh: gspread.Spreadsheet = gs_client(sa_info, readonly=False).open_by_url(sheet_url)
    body = {"valueInputOption": value_input_option, "data": value_ranges}
    return sh.values_batch_update(body)


# ---------- Convenience: read a wishlist tab the old way (kept for UI call site) ----------
@cache_data(show_spinner=False)
def read_wishlist_by_url(
    sheet_url: str, worksheet_name: str, sa_info: Mapping[str, Any] | None = None
) -> pd.DataFrame:
    """
    Read a wishlist sheet into a DataFrame using batched client.
    Expected columns:
      - Item, Category, Price, Name, Days I have to Buy Again, Priority
    """
    client = gs_client(sa_info, readonly=True)
    ws = client.open_by_url(sheet_url).worksheet(worksheet_name)
    df_any = get_as_dataframe(ws, evaluate_formulas=True, header=0).dropna(how="all")
    df: pd.DataFrame = cast(pd.DataFrame, df_any)

    wanted = ["Item", "Category", "Price", "Name", "Days I have to Buy Again", "Priority"]
    missing = [c for c in wanted if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["Price"] = pd.to_numeric(df["Price"], errors="coerce").fillna(0.0)
    df["Priority"] = (
        pd.to_numeric(df["Priority"], downcast="integer", errors="coerce").fillna(0).astype(int)
    )
    df["Days I have to Buy Again"] = (
        pd.to_numeric(df["Days I have to Buy Again"], errors="coerce").fillna(0).astype(int)
    )
    return df[wanted]


# ---------- Convenience: write a DataFrame in (usually) a single update ----------
def write_dataframe(
    sheet_url: str,
    worksheet_name: str,
    df: pd.DataFrame,
    *,
    clear_first: bool = True,
    sa_info: Mapping[str, Any] | None = None,
) -> None:
    """Clear+set a DataFrame using one or two value-range calls (fast)."""
    client: gspread.Client = gs_client(sa_info, readonly=False)
    ws: gspread.Worksheet = client.open_by_url(sheet_url).worksheet(worksheet_name)
    if clear_first:
        ws.clear()
    set_with_dataframe(ws, df, include_index=False, include_column_header=True, resize=True)


@cache_data(show_spinner=False)  # cache raw transaction pull
def load_transactions(sheet_url: str) -> pd.DataFrame:
    gc = gs_client(sa_info=None, readonly=True)
    ws = gc.open_by_url(sheet_url).worksheet("Sheet1")
    values = ws.get_all_records()
    return pd.DataFrame(values)
