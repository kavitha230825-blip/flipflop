"""
Automated Verification Script for Flask Web App and API Endpoints.
"""

import json
from app import app, token_manager

def test_everything():
    print("=== STARTING FULL FLASK APPLICATION & API VERIFICATION ===")
    client = app.test_client()

    # 1. Test All 8 Web Pages
    pages = [
        ("/", "System Dashboard"),
        ("/generator", "Attendance Token Generator"),
        ("/simulator", "4-Bit Flip-Flop Circuit Simulator"),
        ("/truth-table", "4-Bit Synchronous Counter Truth Table"),
        ("/records", "Attendance Records Log"),
        ("/test-cases", "Test Cases & Verification Suite"),
        ("/analytics", "System Analytics & Insights"),
        ("/about", "About Project Documentation")
    ]

    for path, expected_text in pages:
        res = client.get(path)
        assert res.status_code == 200, f"Page {path} failed with status {res.status_code}"
        assert expected_text.encode() in res.data, f"Page {path} missing expected text: {expected_text}"
        print(f" [PASS] Page {path} (Status 200, Rendered successfully)")

    # 2. Test Reset to clean state
    res_clear = client.post("/api/clear")
    assert res_clear.status_code == 200
    print(" [PASS] API /api/clear")

    # 3. Test API /api/status
    res_status = client.get("/api/status")
    assert res_status.status_code == 200
    data = json.loads(res_status.data)
    assert data["binary_state"] == "0000"
    assert data["counter_value"] == 0
    assert data["cycle"] == 1
    print(f" [PASS] API /api/status -> State: {data['binary_state']}, Cycle: {data['cycle']}")

    # 4. Test API /api/generate-token (Valid)
    res_gen1 = client.post("/api/generate-token", json={"student_id": "STU001", "student_name": "Aarav Sharma"})
    assert res_gen1.status_code == 200
    data_gen1 = json.loads(res_gen1.data)
    assert data_gen1["success"] is True
    assert data_gen1["token"] == "ATT-001"
    assert data_gen1["binary_state"] == "0001"
    assert data_gen1["record_id"] == "REC-001"
    print(f" [PASS] API /api/generate-token -> Token: {data_gen1['token']}, Record: {data_gen1['record_id']}")

    # 5. Test Duplicate Student Attendance Prevention
    res_dup = client.post("/api/generate-token", json={"student_id": "STU001", "student_name": "Aarav Sharma"})
    assert res_dup.status_code == 400
    data_dup = json.loads(res_dup.data)
    assert data_dup["success"] is False
    assert data_dup["error_code"] == "DUPLICATE_STUDENT_ATTENDANCE"
    print(f" [PASS] Duplicate Detection -> Error: {data_dup['error_code']}")

    # 6. Test Invalid Input Rejections
    res_inv1 = client.post("/api/generate-token", json={"student_id": "", "student_name": "Alice"})
    assert res_inv1.status_code == 400
    assert json.loads(res_inv1.data)["error_code"] == "EMPTY_STUDENT_ID"
    print(" [PASS] Validation: EMPTY_STUDENT_ID")

    res_inv2 = client.post("/api/generate-token", json={"student_id": "STU002", "student_name": ""})
    assert res_inv2.status_code == 400
    assert json.loads(res_inv2.data)["error_code"] == "EMPTY_STUDENT_NAME"
    print(" [PASS] Validation: EMPTY_STUDENT_NAME")

    res_inv3 = client.post("/api/generate-token", json={"student_id": "INVALID@#$!", "student_name": "Bob"})
    assert res_inv3.status_code == 400
    assert json.loads(res_inv3.data)["error_code"] == "INVALID_STUDENT_ID"
    print(" [PASS] Validation: INVALID_STUDENT_ID")

    # 7. Test Manual Clock Pulse
    res_pulse = client.post("/api/clock-pulse")
    assert res_pulse.status_code == 200
    data_pulse = json.loads(res_pulse.data)
    assert data_pulse["binary_state"] == "0010"
    print(f" [PASS] API /api/clock-pulse -> Next State: {data_pulse['binary_state']}")

    # 8. Test Counter Reset
    res_reset = client.post("/api/reset")
    assert res_reset.status_code == 200
    data_reset = json.loads(res_reset.data)
    assert data_reset["binary_state"] == "0000"
    assert data_reset["cycle"] == 2  # Cycle incremented on reset
    print(f" [PASS] API /api/reset -> State: {data_reset['binary_state']}, New Cycle: {data_reset['cycle']}")

    # 9. Test Record Uniqueness after Reset
    res_gen2 = client.post("/api/generate-token", json={"student_id": "STU002", "student_name": "Diya Patel"})
    assert res_gen2.status_code == 200
    data_gen2 = json.loads(res_gen2.data)
    assert data_gen2["record_id"] == "REC-002"  # Sequentially unique
    assert data_gen2["token"] == "ATT-001"      # Counter starts 1 again
    assert data_gen2["cycle"] == 2              # In Cycle 2
    print(f" [PASS] Post-Reset Record Uniqueness -> Record ID: {data_gen2['record_id']}, Cycle: {data_gen2['cycle']}")

    # 10. Test Overflow Behavior
    token_manager.counter.set_state("1111")
    res_ovf = client.post("/api/generate-token", json={"student_id": "STU003", "student_name": "Rohan Verma"})
    assert res_ovf.status_code == 200
    data_ovf = json.loads(res_ovf.data)
    assert data_ovf["binary_state"] == "0000"
    assert data_ovf["overflow"] is True
    assert data_ovf["cycle"] == 3
    print(f" [PASS] Overflow Handling -> State: {data_ovf['binary_state']}, New Cycle: {data_ovf['cycle']}, Overflow: {data_ovf['overflow']}")

    # 11. Test CSV Export
    res_export = client.get("/api/export-records")
    assert res_export.status_code == 200
    assert "text/csv" in res_export.content_type
    assert b"record_id,student_id,student_name" in res_export.data
    print(" [PASS] API /api/export-records -> Valid CSV streamed")

    # 12. Test Truth Table API
    res_tt = client.get("/api/truth-table")
    assert res_tt.status_code == 200
    data_tt = json.loads(res_tt.data)
    assert data_tt["rows"] == 16
    print(f" [PASS] API /api/truth-table -> {data_tt['rows']} rows confirmed")

    # 13. Test Run Test Cases API
    res_tc = client.get("/api/test-cases")
    assert res_tc.status_code == 200
    data_tc = json.loads(res_tc.data)
    assert data_tc["total"] == 20
    assert data_tc["passed"] == 20
    print(f" [PASS] API /api/test-cases -> {data_tc['passed']}/{data_tc['total']} passed ({data_tc['pass_rate']})")

    # 14. Test Analytics & Synthetic Students
    res_an = client.get("/api/analytics")
    assert res_an.status_code == 200
    res_st = client.get("/api/students")
    assert res_st.status_code == 200
    print(" [PASS] API /api/analytics & /api/students verified")

    print("\n>>> ALL 14 APPLICATION & API VERIFICATION SUITES PASSED WITH ZERO ERRORS! <<<")

if __name__ == "__main__":
    test_everything()
