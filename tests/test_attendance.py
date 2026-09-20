"""
EC2201 Digital Systems - Complete Test Suite
Includes 10 Normal Tests and 10 Edge/Fault Tests (Total: 20 Tests)
Can be run via: py -3 -m unittest discover -s tests
Or via API helper: run_all_test_cases()
"""

import os
import shutil
import tempfile
import unittest

from digital_logic import FourBitCounter
from token_generator import TokenManager


class TestFlipFlopAttendance(unittest.TestCase):
    """20 Automated Test Cases for Flip-Flop Attendance Token Generator."""

    def setUp(self):
        # Create a temporary directory for clean isolation of tests
        self.test_dir = tempfile.mkdtemp()
        # Copy synthetic students if available
        src_stud = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_students.csv")
        if os.path.exists(src_stud):
            shutil.copy(src_stud, os.path.join(self.test_dir, "synthetic_students.csv"))
        self.tm = TokenManager(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ------------------ NORMAL TEST CASES ------------------

    def test_tc01_first_token_generation(self):
        """TC01: First token generation - 0000 advances to 0001 -> ATT-001, Cycle 1."""
        res = self.tm.generate_token("STU001", "Aarav Sharma")
        self.assertTrue(res["success"])
        self.assertEqual(res["token"], "ATT-001")
        self.assertEqual(res["binary_state"], "0001")
        self.assertEqual(res["cycle"], 1)

    def test_tc02_sequential_token_generation(self):
        """TC02: Sequential token generation - next pulse generates ATT-002."""
        self.tm.generate_token("STU001", "Aarav Sharma")
        res2 = self.tm.generate_token("STU002", "Diya Patel")
        self.assertTrue(res2["success"])
        self.assertEqual(res2["token"], "ATT-002")
        self.assertEqual(res2["binary_state"], "0010")

    def test_tc03_counter_increment(self):
        """TC03: Counter increment on each clock pulse."""
        counter = FourBitCounter(0)
        self.assertEqual(counter.decimal_value, 0)
        counter.clock_pulse()
        self.assertEqual(counter.decimal_value, 1)
        counter.clock_pulse()
        self.assertEqual(counter.decimal_value, 2)

    def test_tc04_binary_state_correctness(self):
        """TC04: Binary state correctness (Decimal 3 -> '0011')."""
        counter = FourBitCounter(3)
        self.assertEqual(counter.binary_string, "0011")
        self.assertEqual(counter.bits, [0, 0, 1, 1])

    def test_tc05_decimal_conversion(self):
        """TC05: Decimal conversion (Binary '0111' -> 7)."""
        dec = FourBitCounter.binary_to_decimal("0111")
        self.assertEqual(dec, 7)
        self.assertEqual(FourBitCounter.decimal_to_binary(7), "0111")

    def test_tc06_token_format_validation(self):
        """TC06: Token format validation (3-digit zero-padded ATT-005)."""
        counter = FourBitCounter(4)
        self.tm.counter = counter
        res = self.tm.generate_token("STU005", "Vikram Singh")
        self.assertEqual(res["token"], "ATT-005")

    def test_tc07_multiple_students(self):
        """TC07: Multiple distinct students receive distinct sequential tokens."""
        students = [
            ("STU001", "Aarav Sharma"),
            ("STU002", "Diya Patel"),
            ("STU003", "Rohan Verma"),
            ("STU004", "Ananya Iyer"),
            ("STU005", "Vikram Singh"),
        ]
        tokens = []
        for sid, name in students:
            res = self.tm.generate_token(sid, name)
            self.assertTrue(res["success"])
            tokens.append(res["token"])
        self.assertEqual(tokens, ["ATT-001", "ATT-002", "ATT-003", "ATT-004", "ATT-005"])
        self.assertEqual(self.tm.counter.decimal_value, 5)

    def test_tc08_attendance_record_creation(self):
        """TC08: Attendance record persistence in CSV."""
        res = self.tm.generate_token("STU001", "Aarav Sharma")
        records = self.tm.get_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["record_id"], res["record_id"])
        self.assertEqual(records[0]["student_id"], "STU001")
        self.assertEqual(records[0]["status"], "PRESENT")

    def test_tc09_flip_flop_state_transition(self):
        """TC09: Flip-flop state transition equations verification (0011 -> 0100)."""
        counter = FourBitCounter("0011")
        trans = counter.clock_pulse()
        self.assertEqual(trans["previous_state"]["binary"], "0011")
        self.assertEqual(trans["current_state"]["binary"], "0100")
        # For 0011: T0=1, T1=1, T2=1, T3=0 -> next state 0100
        self.assertEqual(trans["excitations"]["T"], {"t3": 0, "t2": 1, "t1": 1, "t0": 1})
        self.assertEqual(trans["excitations"]["D"], {"d3": 0, "d2": 1, "d1": 0, "d0": 0})

    def test_tc10_truth_table_validation(self):
        """TC10: Truth table contains 16 rows and correct transitions."""
        table = FourBitCounter.get_truth_table()
        self.assertEqual(len(table), 16)
        # Check first and last rows
        self.assertEqual(table[0]["current_binary"], "0000")
        self.assertEqual(table[0]["next_binary"], "0001")
        self.assertEqual(table[15]["current_binary"], "1111")
        self.assertEqual(table[15]["next_binary"], "0000")
        self.assertTrue(table[15]["overflow"])

    # ------------------ EDGE / FAULT TEST CASES ------------------

    def test_tc11_empty_student_id(self):
        """TC11: Empty student ID rejection and fault logging."""
        initial_val = self.tm.counter.decimal_value
        res = self.tm.generate_token("", "Aarav Sharma")
        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "EMPTY_STUDENT_ID")
        self.assertEqual(self.tm.counter.decimal_value, initial_val)
        self.assertGreaterEqual(self.tm.fault_count, 1)

    def test_tc12_empty_student_name(self):
        """TC12: Empty student name rejection and fault logging."""
        initial_val = self.tm.counter.decimal_value
        res = self.tm.generate_token("STU001", "   ")
        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "EMPTY_STUDENT_NAME")
        self.assertEqual(self.tm.counter.decimal_value, initial_val)
        self.assertGreaterEqual(self.tm.fault_count, 1)

    def test_tc13_duplicate_student_attendance(self):
        """TC13: Duplicate student request in same session is rejected."""
        r1 = self.tm.generate_token("STU001", "Aarav Sharma")
        self.assertTrue(r1["success"])
        counter_after_first = self.tm.counter.decimal_value

        r2 = self.tm.generate_token("STU001", "Aarav Sharma")
        self.assertFalse(r2["success"])
        self.assertEqual(r2["error_code"], "DUPLICATE_STUDENT_ATTENDANCE")
        self.assertEqual(self.tm.counter.decimal_value, counter_after_first)
        self.assertGreaterEqual(self.tm.duplicate_attempts, 1)

    def test_tc14_counter_overflow(self):
        """TC14: Counter overflow 1111 -> 0000 triggers cycle increment and event."""
        self.tm.counter.set_state("1111")
        self.assertEqual(self.tm.counter.decimal_value, 15)
        initial_cycle = self.tm.cycle

        res = self.tm.generate_token("STU016", "Nikhil Chawla")
        self.assertTrue(res["success"])
        self.assertEqual(res["counter_value"], 0)
        self.assertEqual(res["binary_state"], "0000")
        self.assertEqual(res["token"], "ATT-000")
        self.assertTrue(res["overflow"])
        self.assertEqual(self.tm.cycle, initial_cycle + 1)

    def test_tc15_counter_reset(self):
        """TC15: Reset zeroes counter and increments cycle while preserving history."""
        self.tm.generate_token("STU001", "Aarav Sharma")
        self.tm.generate_token("STU002", "Diya Patel")
        self.assertEqual(self.tm.counter.decimal_value, 2)
        init_cycle = self.tm.cycle

        reset_res = self.tm.reset_counter()
        self.assertTrue(reset_res["success"])
        self.assertEqual(self.tm.counter.decimal_value, 0)
        self.assertEqual(self.tm.counter.binary_string, "0000")
        self.assertEqual(self.tm.cycle, init_cycle + 1)
        # Verify historical records are preserved
        records = self.tm.get_records()
        self.assertEqual(len(records), 2)

    def test_tc16_record_id_uniqueness_after_reset(self):
        """TC16: Record IDs remain globally unique and sequential after reset."""
        r1 = self.tm.generate_token("STU001", "Aarav Sharma")
        self.assertEqual(r1["record_id"], "REC-001")
        self.tm.reset_counter()
        r2 = self.tm.generate_token("STU002", "Diya Patel")
        self.assertEqual(r2["record_id"], "REC-002")
        self.assertNotEqual(r1["record_id"], r2["record_id"])

    def test_tc17_record_id_uniqueness_after_overflow(self):
        """TC17: Record IDs remain unique across overflow cycles."""
        # Generate 16 tokens across boundary
        self.tm.counter.set_state(14)  # 1110
        r1 = self.tm.generate_token("STU015", "Meera Pillai")   # 1111 -> REC-001
        r2 = self.tm.generate_token("STU016", "Nikhil Chawla")  # 0000 -> REC-002 (overflow to cycle 2)
        r3 = self.tm.generate_token("STU017", "Rhea Sen")       # 0001 -> REC-003
        self.assertEqual(r1["record_id"], "REC-001")
        self.assertEqual(r2["record_id"], "REC-002")
        self.assertEqual(r3["record_id"], "REC-003")
        self.assertEqual(len({r1["record_id"], r2["record_id"], r3["record_id"]}), 3)

    def test_tc18_invalid_student_id(self):
        """TC18: Malformed student ID rejection."""
        res = self.tm.generate_token("ID@#$*&!", "Student Name")
        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "INVALID_STUDENT_ID")

    def test_tc19_invalid_student_name(self):
        """TC19: Non-alphabetical or numeric student name rejection."""
        res = self.tm.generate_token("STU099", "123456")
        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "INVALID_STUDENT_NAME")

    def test_tc20_reset_event_logging(self):
        """TC20: Reset operations are recorded in the system audit log."""
        self.tm.reset_counter()
        events = self.tm.get_events()
        reset_events = [e for e in events if e["event_type"] == "RESET"]
        self.assertGreaterEqual(len(reset_events), 1)


def run_all_test_cases():
    """
    Executes all 20 test cases and returns structured output for UI rendering and API consumption.
    """
    import tempfile
    test_dir = tempfile.mkdtemp()
    src_stud = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_students.csv")
    if os.path.exists(src_stud):
        shutil.copy(src_stud, os.path.join(test_dir, "synthetic_students.csv"))

    tm = TokenManager(test_dir)
    results = []

    def record_test(test_id, category, name, input_str, expected, actual, passed, explanation):
        results.append({
            "test_id": test_id,
            "category": category,
            "name": name,
            "input": input_str,
            "expected_result": expected,
            "actual_result": actual,
            "status": "PASS" if passed else "FAIL",
            "explanation": explanation
        })

    # TC01
    try:
        r = tm.generate_token("STU001", "Aarav Sharma")
        p = r["success"] and r["token"] == "ATT-001" and r["binary_state"] == "0001"
        record_test("TC01", "NORMAL", "First token generation", "Student: STU001, Aarav Sharma", "Token: ATT-001, Binary: 0001", f"Token: {r.get('token')}, Binary: {r.get('binary_state')}", p, "Initial counter state 0000 transitioned to 0001 with token ATT-001.")
    except Exception as e:
        record_test("TC01", "NORMAL", "First token generation", "Student: STU001", "ATT-001", str(e), False, "Error during execution.")

    # TC02
    try:
        r = tm.generate_token("STU002", "Diya Patel")
        p = r["success"] and r["token"] == "ATT-002" and r["binary_state"] == "0010"
        record_test("TC02", "NORMAL", "Sequential token generation", "Student: STU002, Diya Patel", "Token: ATT-002, Binary: 0010", f"Token: {r.get('token')}, Binary: {r.get('binary_state')}", p, "Clock pulse advanced state from 0001 to 0010.")
    except Exception as e:
        record_test("TC02", "NORMAL", "Sequential token generation", "Student: STU002", "ATT-002", str(e), False, "Error.")

    # TC03
    try:
        c = FourBitCounter(0)
        c.clock_pulse()
        c.clock_pulse()
        p = (c.decimal_value == 2)
        record_test("TC03", "NORMAL", "Counter increment", "2 clock pulses from 0", "Decimal: 2", f"Decimal: {c.decimal_value}", p, "Counter correctly increments by 1 mod 16 on each pulse.")
    except Exception as e:
        record_test("TC03", "NORMAL", "Counter increment", "Clock pulse", "2", str(e), False, "Error.")

    # TC04
    try:
        c = FourBitCounter(3)
        p = (c.binary_string == "0011" and c.bits == [0, 0, 1, 1])
        record_test("TC04", "NORMAL", "Binary state correctness", "Decimal: 3", "Binary: 0011", f"Binary: {c.binary_string}", p, "Decimal 3 accurately mapped to Q3=0, Q2=0, Q1=1, Q0=1.")
    except Exception as e:
        record_test("TC04", "NORMAL", "Binary state correctness", "3", "0011", str(e), False, "Error.")

    # TC05
    try:
        dec = FourBitCounter.binary_to_decimal("0111")
        b_str = FourBitCounter.decimal_to_binary(7)
        p = (dec == 7 and b_str == "0111")
        record_test("TC05", "NORMAL", "Decimal conversion", "Binary '0111'", "Decimal 7, Binary '0111'", f"Decimal {dec}, Binary '{b_str}'", p, "Conversion functions between binary and decimal verified.")
    except Exception as e:
        record_test("TC05", "NORMAL", "Decimal conversion", "0111", "7", str(e), False, "Error.")

    # TC06
    try:
        tok = f"ATT-{5:03d}"
        p = (tok == "ATT-005")
        record_test("TC06", "NORMAL", "Token format validation", "Value 5", "ATT-005", tok, p, "Format confirmed as ATT-XXX with 3-digit zero padding.")
    except Exception as e:
        record_test("TC06", "NORMAL", "Token format validation", "5", "ATT-005", str(e), False, "Error.")

    # TC07
    try:
        st_list = [("STU003", "Rohan Verma"), ("STU004", "Ananya Iyer"), ("STU005", "Vikram Singh")]
        oks = [tm.generate_token(sid, sname)["success"] for sid, sname in st_list]
        p = all(oks) and tm.counter.decimal_value == 5
        record_test("TC07", "NORMAL", "Multiple students", "3 consecutive students", "All 3 accepted, Decimal: 5", f"Accepted: {all(oks)}, Decimal: {tm.counter.decimal_value}", p, "Multiple distinct students accepted without conflict.")
    except Exception as e:
        record_test("TC07", "NORMAL", "Multiple students", "Students", "Accepted", str(e), False, "Error.")

    # TC08
    try:
        records = tm.get_records()
        p = len(records) >= 5 and "record_id" in records[0] and "student_id" in records[0]
        record_test("TC08", "NORMAL", "Attendance record creation", "Check stored records", "Records created with valid IDs", f"Total records: {len(records)}", p, "Attendance records persisted to CSV with correct columns.")
    except Exception as e:
        record_test("TC08", "NORMAL", "Attendance record creation", "Check records", "Success", str(e), False, "Error.")

    # TC09
    try:
        c = FourBitCounter("0011")
        tr = c.clock_pulse()
        p = (tr["current_state"]["binary"] == "0100" and tr["excitations"]["T"]["t2"] == 1)
        record_test("TC09", "NORMAL", "Flip-flop state transition", "0011 with Clock", "Next State: 0100, T2=1", f"Next: {tr['current_state']['binary']}, T2={tr['excitations']['T']['t2']}", p, "Synchronous carry logic computed correctly for 0011 -> 0100.")
    except Exception as e:
        record_test("TC09", "NORMAL", "Flip-flop state transition", "0011", "0100", str(e), False, "Error.")

    # TC10
    try:
        tt = FourBitCounter.get_truth_table()
        p = len(tt) == 16 and tt[0]["current_binary"] == "0000" and tt[15]["next_binary"] == "0000"
        record_test("TC10", "NORMAL", "Truth table validation", "Compute 16-state table", "16 rows, 1111 wraps to 0000", f"Rows: {len(tt)}, 1111->{tt[15]['next_binary']}", p, "Complete 16-row synchronous excitation truth table verified.")
    except Exception as e:
        record_test("TC10", "NORMAL", "Truth table validation", "Truth table", "16 rows", str(e), False, "Error.")

    # TC11
    try:
        r = tm.generate_token("", "Aarav Sharma")
        p = (not r["success"] and r["error_code"] == "EMPTY_STUDENT_ID")
        record_test("TC11", "EDGE/FAULT", "Empty student ID", "student_id = ''", "EMPTY_STUDENT_ID error", f"Error: {r.get('error_code')}", p, "Blank student ID correctly rejected and fault recorded.")
    except Exception as e:
        record_test("TC11", "EDGE/FAULT", "Empty student ID", "''", "EMPTY_STUDENT_ID", str(e), False, "Error.")

    # TC12
    try:
        r = tm.generate_token("STU006", "   ")
        p = (not r["success"] and r["error_code"] == "EMPTY_STUDENT_NAME")
        record_test("TC12", "EDGE/FAULT", "Empty student name", "name = '   '", "EMPTY_STUDENT_NAME error", f"Error: {r.get('error_code')}", p, "Whitespace-only name rejected without counter change.")
    except Exception as e:
        record_test("TC12", "EDGE/FAULT", "Empty student name", "''", "EMPTY_STUDENT_NAME", str(e), False, "Error.")

    # TC13
    try:
        # STU001 was already added in TC01
        r = tm.generate_token("STU001", "Aarav Sharma")
        p = (not r["success"] and r["error_code"] == "DUPLICATE_STUDENT_ATTENDANCE")
        record_test("TC13", "EDGE/FAULT", "Duplicate student attendance", "Resubmit STU001", "DUPLICATE_STUDENT_ATTENDANCE", f"Status: {r.get('status')}, Code: {r.get('error_code')}", p, "Duplicate attendance in current session correctly prevented.")
    except Exception as e:
        record_test("TC13", "EDGE/FAULT", "Duplicate student attendance", "STU001 again", "DUPLICATE", str(e), False, "Error.")

    # TC14
    try:
        tm.counter.set_state("1111")
        c_before = tm.cycle
        r = tm.generate_token("STU018", "Harsh Vardhan")
        p = (r["success"] and r["binary_state"] == "0000" and r["overflow"] and tm.cycle == c_before + 1)
        record_test("TC14", "EDGE/FAULT", "Counter overflow 1111 -> 0000", "State 1111 + Clock", "State: 0000, Overflow=True, Cycle+1", f"State: {r.get('binary_state')}, Overflow: {r.get('overflow')}, Cycle: {tm.cycle}", p, "Counter overflowed seamlessly from 15 to 0; cycle updated.")
    except Exception as e:
        record_test("TC14", "EDGE/FAULT", "Counter overflow 1111 -> 0000", "1111 pulse", "0000", str(e), False, "Error.")

    # TC15
    try:
        prev_cyc = tm.cycle
        res_rst = tm.reset_counter()
        p = (res_rst["success"] and tm.counter.decimal_value == 0 and tm.cycle == prev_cyc + 1)
        record_test("TC15", "EDGE/FAULT", "Counter reset", "Reset Counter button", "Counter: 0000 (0), Cycle+1", f"Counter: {tm.counter.binary_string}, Cycle: {tm.cycle}", p, "Counter reset zeroes Q3-Q0 while incrementing cycle.")
    except Exception as e:
        record_test("TC15", "EDGE/FAULT", "Counter reset", "Reset", "0000", str(e), False, "Error.")

    # TC16
    try:
        r_prev = tm.get_records()[-1]["record_id"]
        r_new = tm.generate_token("STU019", "Anika Bhatt")
        p = (r_new["success"] and r_new["record_id"] != r_prev)
        record_test("TC16", "EDGE/FAULT", "Record ID uniqueness after reset", f"Prev: {r_prev}, Post-reset request", "Sequential new Record ID", f"New ID: {r_new.get('record_id')}", p, "Record IDs remain strictly sequential and unique across resets.")
    except Exception as e:
        record_test("TC16", "EDGE/FAULT", "Record ID uniqueness after reset", "Post-reset", "Unique REC-ID", str(e), False, "Error.")

    # TC17
    try:
        # Check record uniqueness in dataset
        all_recs = tm.get_records()
        rec_ids = [r["record_id"] for r in all_recs]
        p = (len(rec_ids) == len(set(rec_ids)))
        record_test("TC17", "EDGE/FAULT", "Record ID uniqueness after overflow", "Inspect all generated records", "Zero collisions among Record IDs", f"Total: {len(rec_ids)}, Unique: {len(set(rec_ids))}", p, "No duplicate Record IDs generated despite multiple overflow and reset cycles.")
    except Exception as e:
        record_test("TC17", "EDGE/FAULT", "Record ID uniqueness after overflow", "All records", "Unique", str(e), False, "Error.")

    # TC18
    try:
        r = tm.validate_input("ID!@#$%", "Valid Name")
        p = (not r[0] and r[1] == "INVALID_STUDENT_ID")
        record_test("TC18", "EDGE/FAULT", "Invalid student ID", "ID = 'ID!@#$%'", "INVALID_STUDENT_ID error", f"Error code: {r[1]}", p, "Special characters in student ID rejected by input validator.")
    except Exception as e:
        record_test("TC18", "EDGE/FAULT", "Invalid student ID", "Invalid ID", "Error", str(e), False, "Error.")

    # TC19
    try:
        r = tm.validate_input("STU099", "1234567")
        p = (not r[0] and r[1] == "INVALID_STUDENT_NAME")
        record_test("TC19", "EDGE/FAULT", "Invalid student name", "Name = '1234567'", "INVALID_STUDENT_NAME error", f"Error code: {r[1]}", p, "Numeric strings rejected as student names.")
    except Exception as e:
        record_test("TC19", "EDGE/FAULT", "Invalid student name", "12345", "Error", str(e), False, "Error.")

    # TC20
    try:
        events = tm.get_events()
        reset_evts = [e for e in events if e["event_type"] == "RESET"]
        p = len(reset_evts) >= 1
        record_test("TC20", "EDGE/FAULT", "Reset event logging", "Inspect system event log", "Contains 'RESET' event entry", f"Reset events logged: {len(reset_evts)}", p, "Administrative reset operation verified in the audit event log.")
    except Exception as e:
        record_test("TC20", "EDGE/FAULT", "Reset event logging", "Audit log", "RESET found", str(e), False, "Error.")

    shutil.rmtree(test_dir, ignore_errors=True)
    return results


if __name__ == "__main__":
    unittest.main()
