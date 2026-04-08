"""
One-time setup script. Run manually once after configuring credentials.json:

    python3 setup_sheet.py

Creates the Google Sheet, writes headers, applies formatting, and adds the
Status dropdown validation. After running, share the printed spreadsheet URL
with your service account email as Editor.
"""
import gspread
from gspread.utils import ValidationConditionType

import config


def setup():
    gc = gspread.service_account(filename=config.CREDENTIALS_FILE)

    # Create or open the spreadsheet
    try:
        sh = gc.open(config.SPREADSHEET_NAME)
        print(f"Found existing spreadsheet: '{config.SPREADSHEET_NAME}'")
    except gspread.SpreadsheetNotFound:
        sh = gc.create(config.SPREADSHEET_NAME)
        print(f"Created new spreadsheet: '{config.SPREADSHEET_NAME}'")

    # Get or create the worksheet tab
    try:
        ws = sh.worksheet(config.WORKSHEET_NAME)
        print(f"Found existing worksheet: '{config.WORKSHEET_NAME}'")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=config.WORKSHEET_NAME, rows=1000, cols=10)
        print(f"Created worksheet: '{config.WORKSHEET_NAME}'")

    # Write header row
    ws.update([config.COLUMNS], "A1")

    # Bold + light blue background on header row
    ws.format("A1:F1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.85, "green": 0.90, "blue": 0.98},
    })

    # Freeze header row so it stays visible while scrolling
    sh.batch_update({
        "requests": [{
            "updateSheetProperties": {
                "properties": {
                    "sheetId": ws.id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        }]
    })

    # Set column widths (pixels)
    column_widths = {
        0: 200,  # Company Name
        1: 240,  # Position Title
        2: 120,  # Date Applied
        3: 350,  # Link to Job Posting
        4: 120,  # Status
        5: 300,  # Notes
    }
    resize_requests = []
    for col_idx, width in column_widths.items():
        resize_requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": ws.id,
                    "dimension": "COLUMNS",
                    "startIndex": col_idx,
                    "endIndex": col_idx + 1,
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize",
            }
        })
    sh.batch_update({"requests": resize_requests})

    # Add Status dropdown to column E (rows 2 onward)
    status_col_index = config.COLUMNS.index("Status")
    status_col_letter = chr(ord("A") + status_col_index)
    ws.add_validation(
        f"{status_col_letter}2:{status_col_letter}1000",
        ValidationConditionType.one_of_list,
        config.STATUS_OPTIONS,
        showCustomUi=True,
        strict=False,
    )

    print(f"\nSetup complete!")
    print(f"Spreadsheet URL: https://docs.google.com/spreadsheets/d/{sh.id}")
    print(f"\nNext step: open the URL above, click Share, and share it with")
    print(f"your service account email (found in credentials.json under 'client_email')")
    print(f"Grant Editor access so the scraper can write rows.")


if __name__ == "__main__":
    setup()
