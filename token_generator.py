"""
EC2201 Digital Systems - Token Management & Data Layer Module
Integrates the 4-bit synchronous counter with attendance business logic,
duplicate detection, fault recording, and CSV persistence.
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from digital_logic import FourBitCounter


class TokenManager:
    """
    Manages token generation, student attendance verification,
    cycle tracking, fault auditing, and data persistence.
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

        self.attendance_file = os.path.join(self.data_dir, "attendance_data.csv")
        self.events_file = os.path.join(self.data_dir, "system_events.csv")
        self.students_file = os.path.join(self.data_dir, "synthetic_students.csv")

        # Initialize Digital Counter
        self.counter = FourBitCounter(0)

        # Operational metrics and state
        self.cycle: int = 1
        self.next_record_num: int = 1
        self.next_event_num: int = 1
        self.duplicate_attempts: int = 0
        self.fault_count: int = 0
        self.successful_tokens: int = 0
        self.latest_token: str = "None"
        self.latest_transition: Optional[Dict] = None

        # Load existing data to sync state
        self._initialize_persistence()

    def _initialize_persistence(self) -> None:
        """Initialize CSV files and restore state counters from existing files if present."""
        # Attendance records file
        if not os.path.exists(self.attendance_file):
            df_att = pd.DataFrame(columns=[
                "record_id", "student_id", "student_name", "token",
                "cycle", "counter_value", "binary_state", "timestamp", "status"
            ])
            df_att.to_csv(self.attendance_file, index=False)
        else:
            try:
                df = pd.read_csv(self.attendance_file)
                if not df.empty and "record_id" in df.columns:
                    # Determine next unique record number
                    ids = df["record_id"].dropna().astype(str).tolist()
                    nums = []
                    for rid in ids:
                        match = re.search(r"REC-(\d+)", rid)
                        if match:
                            nums.append(int(match.group(1)))
                    if nums:
                        self.next_record_num = max(nums) + 1
                    self.successful_tokens = len(df[df["status"] == "PRESENT"])
                    if not df.empty:
                        last_row = df.iloc[-1]
                        self.latest_token = str(last_row["token"])
                        if "cycle" in last_row and pd.notna(last_row["cycle"]):
                            self.cycle = max(1, int(last_row["cycle"]))
            except Exception:
                pass

        # Events log file
        if not os.path.exists(self.events_file):
            df_evt = pd.DataFrame(columns=[
                "event_id", "event_type", "description", "timestamp", "cycle", "counter_value"
            ])
            df_evt.to_csv(self.events_file, index=False)
            self._log_event("SYSTEM_INIT", "Flip-Flop Attendance Token Generator initialized")
        else:
            try:
                df_ev = pd.read_csv(self.events_file)
                if not df_ev.empty and "event_id" in df_ev.columns:
                    ids = df_ev["event_id"].dropna().astype(str).tolist()
                    nums = []
                    for eid in ids:
                        match = re.search(r"EVT-(\d+)", eid)
                        if match:
                            nums.append(int(match.group(1)))
                    if nums:
                        self.next_event_num = max(nums) + 1
                    
                    # Count historical faults and duplicates
                    self.duplicate_attempts = len(df_ev[df_ev["event_type"] == "DUPLICATE_STUDENT_ATTENDANCE"])
                    fault_types = ["DUPLICATE_STUDENT_ATTENDANCE", "EMPTY_STUDENT_ID", "EMPTY_STUDENT_NAME", "INVALID_STUDENT_ID", "INVALID_STUDENT_NAME"]
                    self.fault_count = len(df_ev[df_ev["event_type"].isin(fault_types)])
            except Exception:
                pass

    def _log_event(self, event_type: str, description: str) -> str:
        """Append an event to the system audit trail CSV."""
        event_id = f"EVT-{self.next_event_num:03d}"
        self.next_event_num += 1
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_row = {
            "event_id": event_id,
            "event_type": event_type,
            "description": description,
            "timestamp": now_str,
            "cycle": self.cycle,
            "counter_value": self.counter.binary_string
        }

        try:
            df = pd.DataFrame([new_row])
            df.to_csv(self.events_file, mode='a', header=not os.path.exists(self.events_file) or os.stat(self.events_file).st_size == 0, index=False)
        except Exception as e:
            print(f"Error logging event: {e}")

        return event_id

    def validate_input(self, student_id: Optional[str], student_name: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates student ID and student Name.
        Returns (is_valid, error_code, error_message).
        """
        # Empty checks
        if student_id is None or not str(student_id).strip():
            return False, "EMPTY_STUDENT_ID", "Student ID cannot be empty."

        clean_id = str(student_id).strip().upper()

        if student_name is None or not str(student_name).strip():
            return False, "EMPTY_STUDENT_NAME", "Student Name cannot be empty."

        clean_name = str(student_name).strip()

        # Format checks
        # Student ID must be alphanumeric, hyphen or underscore, 3 to 20 chars
        if not re.match(r"^[A-Z0-9_\-]{3,20}$", clean_id):
            return False, "INVALID_STUDENT_ID", f"Invalid Student ID '{clean_id}'. Must be 3-20 alphanumeric characters (e.g. STU001)."

        # Student Name must contain only letters, spaces, dots, hyphens, min 2 chars
        if not re.match(r"^[A-Za-z\s\.\-]{2,50}$", clean_name):
            return False, "INVALID_STUDENT_NAME", f"Invalid Student Name '{clean_name}'. Must contain only alphabetic characters and be 2-50 characters long."

        return True, None, None

    def is_duplicate_student(self, student_id: str) -> bool:
        """
        Checks whether the student has already been recorded in attendance records.
        """
        clean_id = student_id.strip().upper()
        if not os.path.exists(self.attendance_file):
            return False

        try:
            df = pd.read_csv(self.attendance_file)
            if df.empty or "student_id" not in df.columns:
                return False
            # Check for existing accepted record
            existing = df[(df["student_id"].str.upper() == clean_id) & (df["status"] == "PRESENT")]
            return len(existing) > 0
        except Exception:
            return False

    def generate_token(self, student_id: str, student_name: str) -> Dict[str, Union[bool, str, int, Dict]]:
        """
        Process an attendance token generation request:
        1. Validate inputs (reject empty or invalid format)
        2. Check duplicate attendance for student
        3. If valid, trigger clock pulse on 4-bit counter
        4. Detect counter overflow (1111 -> 0000), update cycle
        5. Map counter value to token: ATT-{decimal:03d}
        6. Generate globally unique Record ID (REC-xxx)
        7. Persist record to CSV
        8. Return comprehensive result payload
        """
        # 1. Validation
        is_valid, err_code, err_msg = self.validate_input(student_id, student_name)
        if not is_valid:
            self.fault_count += 1
            self._log_event(err_code or "FAULT", f"Input validation failure: {err_msg} (ID: '{student_id}', Name: '{student_name}')")
            return {
                "success": False,
                "error_code": err_code,
                "message": err_msg,
                "status": "REJECTED"
            }

        clean_id = str(student_id).strip().upper()
        clean_name = str(student_name).strip()

        # 2. Duplicate Check
        if self.is_duplicate_student(clean_id):
            self.duplicate_attempts += 1
            self.fault_count += 1
            self._log_event("DUPLICATE_STUDENT_ATTENDANCE", f"Duplicate attendance attempt for student {clean_id} ({clean_name})")
            return {
                "success": False,
                "error_code": "DUPLICATE_STUDENT_ATTENDANCE",
                "message": f"Student '{clean_id}' has already been marked present for this session.",
                "status": "DUPLICATE"
            }

        # 3. Advance the digital counter using a clock pulse
        transition = self.counter.clock_pulse()
        self.latest_transition = transition

        # 4. Handle overflow condition (1111 -> 0000)
        overflow_occurred = transition["overflow"]
        if overflow_occurred:
            self.cycle += 1
            self._log_event("COUNTER_OVERFLOW", f"Counter overflowed from 1111 (15) to 0000 (0). Incremented to Cycle {self.cycle}.")

        # 5. Compute token and record ID
        counter_val = self.counter.decimal_value
        token_str = f"ATT-{counter_val:03d}"
        self.latest_token = token_str
        self.successful_tokens += 1

        record_id = f"REC-{self.next_record_num:03d}"
        self.next_record_num += 1

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 6. Save attendance record
        new_record = {
            "record_id": record_id,
            "student_id": clean_id,
            "student_name": clean_name,
            "token": token_str,
            "cycle": self.cycle,
            "counter_value": counter_val,
            "binary_state": self.counter.binary_string,
            "timestamp": now_str,
            "status": "PRESENT"
        }

        try:
            df = pd.DataFrame([new_record])
            df.to_csv(self.attendance_file, mode='a', header=not os.path.exists(self.attendance_file) or os.stat(self.attendance_file).st_size == 0, index=False)
        except Exception as e:
            print(f"Error appending attendance record: {e}")

        self._log_event("TOKEN_GENERATED", f"Token {token_str} issued to {clean_id} (Record: {record_id}, State: {self.counter.binary_string}, Cycle: {self.cycle})")

        return {
            "success": True,
            "record_id": record_id,
            "token": token_str,
            "cycle": self.cycle,
            "student_id": clean_id,
            "student_name": clean_name,
            "counter_value": counter_val,
            "binary_state": self.counter.binary_string,
            "timestamp": now_str,
            "status": "PRESENT",
            "transition": transition,
            "overflow": overflow_occurred
        }

    def manual_clock_pulse(self) -> Dict[str, Union[bool, str, int, Dict]]:
        """
        Manually triggers a clock pulse for simulation / educational demonstration.
        Advances counter without requiring student registration.
        """
        transition = self.counter.clock_pulse()
        self.latest_transition = transition

        overflow_occurred = transition["overflow"]
        if overflow_occurred:
            self.cycle += 1
            self._log_event("COUNTER_OVERFLOW", f"Manual Clock Pulse: Counter overflowed 1111 -> 0000. Advanced to Cycle {self.cycle}.")

        token_str = f"ATT-{self.counter.decimal_value:03d}"
        self.latest_token = token_str

        self._log_event("MANUAL_CLOCK_PULSE", f"Manual clock pulse triggered. State transitioned to {self.counter.binary_string} ({self.counter.decimal_value})")

        return {
            "success": True,
            "token": token_str,
            "cycle": self.cycle,
            "counter_value": self.counter.decimal_value,
            "binary_state": self.counter.binary_string,
            "transition": transition,
            "overflow": overflow_occurred
        }

    def reset_counter(self) -> Dict[str, Union[bool, str, int, Dict]]:
        """
        Executes counter reset:
        - Sets Q3 Q2 Q1 Q0 to 0000
        - Sets decimal value to 0
        - Increments cycle count
        - Preserves previous attendance records and system history
        - Preserves sequential record ID sequence
        - Logs RESET event
        """
        reset_info = self.counter.reset()
        self.cycle += 1
        self.latest_token = "ATT-000"

        self._log_event("RESET", f"Digital counter reset to 0000. Cycle incremented to {self.cycle}. Historical records preserved.")

        return {
            "success": True,
            "message": "Counter reset successfully to 0000. Cycle updated.",
            "reset_info": reset_info,
            "cycle": self.cycle,
            "counter_value": 0,
            "binary_state": "0000",
            "token": "ATT-000"
        }

    def clear_data(self) -> Dict[str, Union[bool, str]]:
        """
        Administrative full reset: clears current attendance records and reinitializes state.
        Keeps synthetic student roster intact.
        """
        self.counter.reset()
        self.cycle = 1
        self.next_record_num = 1
        self.next_event_num = 1
        self.duplicate_attempts = 0
        self.fault_count = 0
        self.successful_tokens = 0
        self.latest_token = "None"
        self.latest_transition = None

        df_att = pd.DataFrame(columns=[
            "record_id", "student_id", "student_name", "token",
            "cycle", "counter_value", "binary_state", "timestamp", "status"
        ])
        df_att.to_csv(self.attendance_file, index=False)

        df_evt = pd.DataFrame(columns=[
            "event_id", "event_type", "description", "timestamp", "cycle", "counter_value"
        ])
        df_evt.to_csv(self.events_file, index=False)
        self._log_event("SESSION_CLEARED", "All attendance records and system logs cleared by administrator.")

        return {
            "success": True,
            "message": "All attendance data and counters have been reset to initial state."
        }

    def get_status(self) -> Dict:
        """Returns comprehensive status snapshot for dashboard and UI headers."""
        state = self.counter.get_state()
        return {
            "current_token": self.latest_token,
            "cycle": self.cycle,
            "counter_value": self.counter.decimal_value,
            "binary_state": self.counter.binary_string,
            "bits": self.counter.bits,
            "q3": self.counter.q3,
            "q2": self.counter.q2,
            "q1": self.counter.q1,
            "q0": self.counter.q0,
            "next_binary": state["next_binary"],
            "next_decimal": state["next_decimal"],
            "excitations": state["excitations"],
            "total_records": self.get_total_records_count(),
            "successful_tokens": self.successful_tokens,
            "duplicate_attempts": self.duplicate_attempts,
            "fault_count": self.fault_count,
            "latest_transition": self.latest_transition,
            "system_status": "ONLINE"
        }

    def get_total_records_count(self) -> int:
        """Returns count of recorded attendance entries."""
        if not os.path.exists(self.attendance_file):
            return 0
        try:
            df = pd.read_csv(self.attendance_file)
            return len(df)
        except Exception:
            return 0

    def get_records(self, search: Optional[str] = None, cycle_filter: Optional[str] = None) -> List[Dict]:
        """Fetch attendance records with optional search and cycle filtering."""
        if not os.path.exists(self.attendance_file):
            return []

        try:
            df = pd.read_csv(self.attendance_file)
            if df.empty:
                return []

            # Replace NaNs
            df = df.fillna("")

            # Filter by cycle
            if cycle_filter and cycle_filter.strip().lower() not in ("all", ""):
                try:
                    c_num = int(cycle_filter)
                    df = df[df["cycle"] == c_num]
                except ValueError:
                    pass

            # Search by student ID, Name, or Token
            if search and search.strip():
                query = search.strip().lower()
                mask = (
                    df["student_id"].astype(str).str.lower().str.contains(query) |
                    df["student_name"].astype(str).str.lower().str.contains(query) |
                    df["token"].astype(str).str.lower().str.contains(query) |
                    df["record_id"].astype(str).str.lower().str.contains(query)
                )
                df = df[mask]

            # Return list of dictionaries (reverse sorted by record_id)
            return df.to_dict(orient="records")
        except Exception as e:
            print(f"Error reading records: {e}")
            return []

    def get_events(self, limit: int = 20) -> List[Dict]:
        """Fetch recent system events."""
        if not os.path.exists(self.events_file):
            return []
        try:
            df = pd.read_csv(self.events_file)
            if df.empty:
                return []
            df = df.fillna("")
            records = df.to_dict(orient="records")
            return records[-limit:][::-1]  # Return latest first
        except Exception:
            return []

    def get_synthetic_students(self) -> List[Dict]:
        """Returns synthetic student roster for quick input selection."""
        if not os.path.exists(self.students_file):
            return []
        try:
            df = pd.read_csv(self.students_file)
            return df.to_dict(orient="records")
        except Exception:
            return []

    def get_analytics(self) -> Dict:
        """
        Aggregates data for charts:
        - Tokens per cycle
        - Status breakdown (Present vs Faults vs Duplicates)
        - Flip-flop bit frequencies (Q0, Q1, Q2, Q3 toggle rates)
        - Hourly/time sequence distribution
        """
        att_df = pd.DataFrame()
        if os.path.exists(self.attendance_file):
            try:
                att_df = pd.read_csv(self.attendance_file)
            except Exception:
                pass

        # Cycle distribution
        cycle_counts = {}
        if not att_df.empty and "cycle" in att_df.columns:
            counts = att_df["cycle"].value_counts().sort_index()
            for c, cnt in counts.items():
                cycle_counts[f"Cycle {c}"] = int(cnt)
        if not cycle_counts:
            cycle_counts = {f"Cycle {self.cycle}": self.successful_tokens}

        # Status breakdown
        status_breakdown = {
            "Successful Tokens": self.successful_tokens,
            "Duplicate Attempts": self.duplicate_attempts,
            "Validation Faults": max(0, self.fault_count - self.duplicate_attempts)
        }

        # Bit frequencies: how many times each bit was '1'
        bit_frequencies = {"Q0": 0, "Q1": 0, "Q2": 0, "Q3": 0}
        if not att_df.empty and "binary_state" in att_df.columns:
            for b_str in att_df["binary_state"].astype(str):
                clean = b_str.strip()
                if len(clean) == 4:
                    if clean[0] == '1': bit_frequencies["Q3"] += 1
                    if clean[1] == '1': bit_frequencies["Q2"] += 1
                    if clean[2] == '1': bit_frequencies["Q1"] += 1
                    if clean[3] == '1': bit_frequencies["Q0"] += 1

        return {
            "cycle_distribution": cycle_counts,
            "status_breakdown": status_breakdown,
            "bit_frequencies": bit_frequencies,
            "total_records": len(att_df) if not att_df.empty else 0,
            "current_cycle": self.cycle,
            "counter_decimal": self.counter.decimal_value,
            "counter_binary": self.counter.binary_string
        }
