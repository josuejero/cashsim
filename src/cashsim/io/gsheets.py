from __future__ import annotations
from typing import Dict
import pandas as pd
import gspread
from google.oauth2 import service_account
from gspread_dataframe import get_as_dataframe

SHEETS_READONLY = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def read_wishlist_by_url(sheet_url: str, worksheet_name: str, sa_info: Dict) -> pd.DataFrame:
    """
    Read a wishlist sheet into a DataFrame using a Service Account.

    Expected columns:
      - Item, Category, Price, Name, Days I have to Buy Again, Priority
    """
    creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SHEETS_READONLY)
    client = gspread.authorize(creds)
    sh = client.open_by_url(sheet_url)   # Share the sheet with the service account's client_email!
    ws = sh.worksheet(worksheet_name)
    df = get_as_dataframe(ws, evaluate_formulas=True, header=0)
    df = df.dropna(how="all")

    wanted = ["Item", "Category", "Price", "Name", "Days I have to Buy Again", "Priority"]
    missing = [c for c in wanted if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["Price"] = pd.to_numeric(df["Price"], errors="coerce").fillna(0.0)
    df["Priority"] = pd.to_numeric(df["Priority"], downcast="integer", errors="coerce").fillna(0).astype(int)
    df["Days I have to Buy Again"] = pd.to_numeric(
        df["Days I have to Buy Again"], errors="coerce"
    ).fillna(0).astype(int)

    return df[wanted]
