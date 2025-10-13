from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import gspread
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from gspread_dataframe import get_as_dataframe  # type: ignore[reportMissingTypeStubs]

SHEETS_READONLY = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


@st.cache_data(show_spinner=False)
def read_wishlist_by_url(
    sheet_url: str, worksheet_name: str, sa_info: Mapping[str, Any]
) -> pd.DataFrame:
    """
    Read a wishlist sheet into a DataFrame using a Service Account.

    Expected columns:
      - Item, Category, Price, Name, Days I have to Buy Again, Priority
    """
    client = gs_client(sa_info)
    sh = client.open_by_url(sheet_url)  # Share the sheet with the service account's client_email!
    ws = sh.worksheet(worksheet_name)
    df: pd.DataFrame = get_as_dataframe(ws, evaluate_formulas=True, header=0)
    df = df.dropna(how="all")

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


@st.cache_resource(show_spinner=False)
def gs_client(sa_info: dict):
    """Singleton gspread client shared across reruns & sessions."""
    creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SHEETS_READONLY)
    return gspread.authorize(creds)
