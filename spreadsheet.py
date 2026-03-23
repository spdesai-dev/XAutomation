import csv
import openpyxl
import os
from loguru import logger

class SpreadsheetManager:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None
        self._load_data()

    def _load_data(self):
        """Loads data from the given CSV or XLSX file."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Spreadsheet not found: {self.file_path}")
            
        _, ext = os.path.splitext(self.file_path)
        ext = ext.lower()
        
        try:
            if ext == '.csv':
                with open(self.file_path, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    raw_data = list(reader)
                    raw_fieldnames = list(reader.fieldnames) if reader.fieldnames else []
                # Normalize column names: lowercase + strip whitespace
                self.columns = [str(c).strip().lower() for c in raw_fieldnames]
                col_map = {orig: norm for orig, norm in zip(raw_fieldnames, self.columns)}
                self.data = [{col_map.get(k, k.strip().lower()): ('' if v is None else str(v).strip()) for k, v in row.items()} for row in raw_data]
            elif ext in ['.xlsx', '.xls']:
                wb = openpyxl.load_workbook(self.file_path)
                sheet = wb.active
                rows = list(sheet.values)
                if not rows:
                    self.data = []
                    self.columns = []
                else:
                    # Normalize column names: lowercase + strip
                    raw_cols = [str(c).strip() if c is not None else '' for c in rows[0]]
                    self.columns = [c.lower() for c in raw_cols]
                    self.data = [
                        {self.columns[i]: ('' if v is None else str(v).strip()) for i, v in enumerate(row)}
                        for row in rows[1:]
                    ]
            else:
                raise ValueError(f"Unsupported file format: {ext}. Please use CSV or XLSX.")
                
            self._validate_columns()
            # Drop completely blank rows (no username) — these are trailing empty Excel rows
            self.data = [r for r in self.data if str(r.get('username', '')).strip().lstrip('@')]
            self._initialize_tracking_columns()
            logger.info(f"Loaded {len(self.data)} rows from {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to load spreadsheet: {str(e)}")
            raise

    def _validate_columns(self):
        """Ensures only the 'username' column is present (all others are optional)."""
        if 'username' not in self.columns:
            raise ValueError("Spreadsheet must have a 'username' column.")
        # Auto-add optional columns with empty defaults so downstream code never KeyErrors
        for optional_col in ['profile_url', 'post_url', 'post_content']:
            if optional_col not in self.columns:
                self.columns.append(optional_col)
                for row in self.data:
                    row.setdefault(optional_col, '')

    def _initialize_tracking_columns(self):
        """Adds 'status' and 'reply' columns if they don't exist."""
        if 'status' not in self.columns:
            self.columns.append('status')
        if 'reply' not in self.columns:
            self.columns.append('reply')
        if 'generated_message' not in self.columns:
            self.columns.append('generated_message')

        for row in self.data:
            if 'status' not in row or not str(row['status']).strip() or str(row['status']).lower() == 'nan':
                row['status'] = 'pending'
            if 'reply' not in row or not str(row['reply']).strip() or str(row['reply']).lower() == 'nan':
                row['reply'] = 'none'
            if 'generated_message' not in row or str(row['generated_message']).lower() == 'nan':
                 row['generated_message'] = ''
            
        # Ensure we always update the file initially with these cols
        self.save()

    def get_pending_users(self):
        """Yields rows where status is 'pending' and username is non-empty."""
        for index, row in enumerate(self.data):
            if str(row.get('status', '')).lower() == 'pending' and str(row.get('username', '')).strip():
                yield index, row

    def get_approved_users(self):
        """Yields rows where status is 'approved' and username is non-empty."""
        for index, row in enumerate(self.data):
            if str(row.get('status', '')).lower() == 'approved' and str(row.get('username', '')).strip():
                yield index, row

    def get_pending_approvals(self):
        """Returns a list of users pending manual approval or already approved."""
        approvals = []
        for index, row in enumerate(self.data):
            status = str(row.get('status', '')).lower()
            if status in ['pending_approval', 'approved', 'sent', 'failed']:
                approvals.append({"index": index, "data": row})
        return approvals

    def update_user_status(self, index: int, status: str, reply: str = 'none', generated_message: str = None):
        """Updates the status and reply columns for a specific row, and saves the file."""
        self.data[index]['status'] = status
        self.data[index]['reply'] = reply
        if generated_message is not None:
            self.data[index]['generated_message'] = generated_message
        self.save()
        logger.debug(f"Updated row {index}: status={status}, reply={reply}")

    def save(self):
        """Saves the DataFrame back to the original file format."""
        _, ext = os.path.splitext(self.file_path)
        ext = ext.lower()
        
        try:
            # Ensure all keys in data are in columns
            for row in self.data:
                for key in row.keys():
                    if key not in self.columns:
                        self.columns.append(key)

            if ext == '.csv':
                with open(self.file_path, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.columns)
                    writer.writeheader()
                    writer.writerows(self.data)
            elif ext in ['.xlsx', '.xls']:
                wb = openpyxl.Workbook()
                sheet = wb.active
                sheet.append(self.columns)
                for row in self.data:
                    sheet.append([row.get(col, '') for col in self.columns])
                wb.save(self.file_path)
        except Exception as e:
            logger.error(f"Failed to save spreadsheet: {str(e)}")
