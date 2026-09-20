"""
EC2201 Digital Systems - Web Application Server
Flask backend implementing REST API and serving responsive web pages for
the Flip-Flop Based Attendance Token Generator.
"""

import os
import io
from flask import Flask, render_template, request, jsonify, send_file, Response
import pandas as pd

from digital_logic import FourBitCounter
from token_generator import TokenManager
from tests.test_attendance import run_all_test_cases

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['SECRET_KEY'] = 'ec2201-flip-flop-digital-systems-key'

# Instantiate global TokenManager
token_manager = TokenManager(DATA_DIR)


# =========================================================================
# WEB PAGE ROUTES
# =========================================================================

@app.route("/")
def index():
    """Dashboard page."""
    status = token_manager.get_status()
    recent_events = token_manager.get_events(limit=5)
    return render_template("index.html", status=status, recent_events=recent_events, active_page="dashboard")


@app.route("/generator")
def generator_page():
    """Token Generator page."""
    status = token_manager.get_status()
    students = token_manager.get_synthetic_students()
    return render_template("generator.html", status=status, students=students, active_page="generator")


@app.route("/simulator")
def simulator_page():
    """Flip-Flop Simulator page."""
    status = token_manager.get_status()
    return render_template("simulator.html", status=status, active_page="simulator")


@app.route("/truth-table")
def truth_table_page():
    """16-State Truth Table page."""
    table = FourBitCounter.get_truth_table()
    status = token_manager.get_status()
    return render_template("truth_table.html", truth_table=table, status=status, active_page="truth_table")


@app.route("/records")
def records_page():
    """Attendance Records page."""
    records = token_manager.get_records()
    status = token_manager.get_status()
    return render_template("records.html", records=records, status=status, active_page="records")


@app.route("/test-cases")
def test_cases_page():
    """Test Cases evaluation page."""
    status = token_manager.get_status()
    # Read test definitions from CSV if available
    test_cases_file = os.path.join(DATA_DIR, "test_cases.csv")
    csv_tests = []
    if os.path.exists(test_cases_file):
        try:
            df = pd.read_csv(test_cases_file)
            csv_tests = df.fillna("").to_dict(orient="records")
        except Exception:
            pass
    return render_template("test_cases.html", status=status, test_cases=csv_tests, active_page="test_cases")


@app.route("/analytics")
def analytics_page():
    """Results / Analytics page."""
    status = token_manager.get_status()
    analytics_data = token_manager.get_analytics()
    return render_template("analytics.html", status=status, analytics=analytics_data, active_page="analytics")


@app.route("/about")
def about_page():
    """Academic About Project documentation page."""
    status = token_manager.get_status()
    return render_template("about.html", status=status, active_page="about")


# =========================================================================
# REST API ENDPOINTS
# =========================================================================

@app.route("/api/status", methods=["GET"])
def api_status():
    """Return live counter state, metrics, and health."""
    return jsonify(token_manager.get_status())


@app.route("/api/generate-token", methods=["POST"])
def api_generate_token():
    """Generate attendance token from submitted student credentials."""
    data = request.get_json() or {}
    student_id = data.get("student_id", "")
    student_name = data.get("student_name", "")

    result = token_manager.generate_token(student_id, student_name)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@app.route("/api/clock-pulse", methods=["POST"])
def api_clock_pulse():
    """Trigger manual clock pulse for simulator."""
    result = token_manager.manual_clock_pulse()
    return jsonify(result)


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Reset counter to 0000, increment cycle, preserve historical records."""
    result = token_manager.reset_counter()
    return jsonify(result)


@app.route("/api/clear", methods=["POST"])
def api_clear():
    """Administrative clear of attendance records and state."""
    result = token_manager.clear_data()
    return jsonify(result)


@app.route("/api/records", methods=["GET"])
def api_records():
    """Fetch attendance records with optional search and cycle filtering."""
    search = request.args.get("search", None)
    cycle = request.args.get("cycle", None)
    records = token_manager.get_records(search=search, cycle_filter=cycle)
    return jsonify({"success": True, "count": len(records), "records": records})


@app.route("/api/export-records", methods=["GET"])
def api_export_records():
    """Export attendance records to a downloadable CSV."""
    records = token_manager.get_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=[
            "record_id", "student_id", "student_name", "token",
            "cycle", "counter_value", "binary_state", "timestamp", "status"
        ])

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return Response(
        csv_buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=flipflop_attendance_records.csv"}
    )


@app.route("/api/truth-table", methods=["GET"])
def api_truth_table():
    """Return all 16 rows of the 4-bit synchronous counter truth table."""
    table = FourBitCounter.get_truth_table()
    return jsonify({"success": True, "rows": len(table), "truth_table": table})


@app.route("/api/test-cases", methods=["GET"])
def api_test_cases():
    """Run all 20 test cases dynamically and return detailed results."""
    results = run_all_test_cases()
    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    return jsonify({
        "success": True,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": f"{(passed / total) * 100:.1f}%",
        "results": results
    })


@app.route("/api/history", methods=["GET"])
@app.route("/api/events", methods=["GET"])
def api_events():
    """Return recent system events audit trail."""
    limit = request.args.get("limit", 50, type=int)
    events = token_manager.get_events(limit=limit)
    return jsonify({"success": True, "count": len(events), "events": events})


@app.route("/api/analytics", methods=["GET"])
def api_analytics():
    """Return aggregated metrics for chart rendering."""
    analytics = token_manager.get_analytics()
    return jsonify({"success": True, "analytics": analytics})


@app.route("/api/students", methods=["GET"])
def api_students():
    """Return synthetic student roster."""
    students = token_manager.get_synthetic_students()
    return jsonify({"success": True, "count": len(students), "students": students})


if __name__ == "__main__":
    # College lab demo server run configuration
    print("===================================================================")
    print(" EC2201 DIGITAL SYSTEMS: Flip-Flop Attendance Token Generator")
    print(" Server starting on http://127.0.0.1:5000")
    print(" Press Ctrl+C to stop.")
    print("===================================================================")
    app.run(host="127.0.0.1", port=5000, debug=True)
