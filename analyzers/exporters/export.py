import json
from io import BytesIO
import pandas as pd


def export_csv(data: list[dict]) -> bytes:
    """
    Export a list of dicts to CSV bytes
    """
    df = pd.DataFrame(data)
    return df.to_csv(index=False).encode("utf-8")


def export_excel(sheets: dict[str, list[dict]]) -> bytes:
    """
    Export multiple sheets to one Excel file
    sheets = { "Sheet name": [ {row}, {row} ] }
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, rows in sheets.items():
            df = pd.DataFrame(rows)
            df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()


def export_json(payload: dict) -> bytes:
    """
    Export raw results as JSON bytes
    """
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
