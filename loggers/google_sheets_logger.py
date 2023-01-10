import consts

import gspread
from oauth2client.service_account import ServiceAccountCredentials


class GoogleSheetsLogger:
    def __init__(self, creds_file, sheet_name):
        self.creds_file = creds_file
        self.sheet_name = sheet_name

    async def log(self, current_date, action, user_id, username, full_name):
        scope = [consts.SPREADSHEETS, consts.SPREADSHEETS_API, consts.DRIVE_FILE, consts.DRIVE_API]

        creds_sample = ServiceAccountCredentials.from_json_keyfile_name(self.creds_file, scope)
        client = gspread.authorize(creds_sample)
        sheet = client.open(self.sheet_name).sheet1

        data_to_append = [current_date, action, user_id, username, full_name]
        sheet.append_row(data_to_append)

