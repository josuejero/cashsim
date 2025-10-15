from typing import Any

from gspread import Worksheet
from pandas import DataFrame, Series

def get_as_dataframe(
    worksheet: Worksheet,
    evaluate_formulas: bool = ...,
    drop_empty_rows: bool = ...,
    drop_empty_columns: bool = ...,
    **options: Any,
) -> DataFrame | Series[Any]: ...
def set_with_dataframe(
    worksheet: Worksheet,
    dataframe: DataFrame,
    row: int = ...,
    col: int = ...,
    include_index: bool = ...,
    include_column_header: bool = ...,
    resize: bool = ...,
    allow_formulas: bool = ...,
    string_escaping: str = ...,
) -> None: ...
