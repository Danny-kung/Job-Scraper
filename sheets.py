import logging

import gspread

import config

logger = logging.getLogger(__name__)


def get_worksheet() -> gspread.Worksheet:
    """Authenticate via service account and return the target worksheet."""
    gc = gspread.service_account(filename=config.CREDENTIALS_FILE)
    sh = gc.open(config.SPREADSHEET_NAME)
    return sh.worksheet(config.WORKSHEET_NAME)


def get_existing_urls(worksheet: gspread.Worksheet) -> set:
    """
    Return a set of all job URLs already tracked in the sheet.
    Reads the 'Link to Job Posting' column; skips the header row.
    """
    url_col_index = config.COLUMNS.index("Link to Job Posting") + 1  # 1-based
    all_values = worksheet.col_values(url_col_index)
    # all_values[0] is the header, skip it
    return set(all_values[1:])


def append_jobs(worksheet: gspread.Worksheet, jobs_df) -> int:
    """
    Append new jobs to the sheet.
    Date Applied and Status are left blank for the user to fill in.
    Returns the number of rows appended.
    """
    rows_to_append = []

    for _, row in jobs_df.iterrows():
        sheet_row = [
            str(row.get("company", "")).strip(),
            str(row.get("title", "")).strip(),
            "",   # Date Applied — user fills in when they apply
            str(row.get("job_url", "")).strip(),
            "",   # Status — user fills in
            "",   # Notes — user fills in
        ]
        rows_to_append.append(sheet_row)

    if rows_to_append:
        worksheet.append_rows(
            rows_to_append,
            value_input_option="USER_ENTERED",
            insert_data_option="INSERT_ROWS",
            table_range="A1",
        )
        logger.info(f"Appended {len(rows_to_append)} new job(s) to sheet.")
    else:
        logger.info("No new jobs to append.")

    return len(rows_to_append)
