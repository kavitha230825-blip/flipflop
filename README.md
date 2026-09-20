# Flip-Flop Based Attendance Token Generator
**Course:** EC2201 Digital Systems  
**Project Category:** Synchronous Sequential Digital Logic Simulation  
**Technologies:** Python 3.12, Flask, Pandas, NumPy, HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js

---

## 1. Project Title & Overview

The **Flip-Flop Based Attendance Token Generator** is an academic software simulation demonstrating the application of sequential digital logic to solve real-world token generation and queue tracking challenges.

The application models a hardware-accurate **4-bit synchronous binary up-counter** constructed using flip-flop excitation equations ($Q_3 Q_2 Q_1 Q_0$). Each valid student attendance entry acts as a rising-edge master clock pulse ($\uparrow$), causing deterministic state transitions, issuing sequential attendance tokens (`ATT-001`, `ATT-002`, ...), detecting duplicate attendance attempts, managing counter overflows ($1111 \to 0000$), and executing administrative resets.

---

## 2. Problem Statement & Objectives

### The Problem
Traditional manual attendance registers and uncoordinated digital loggers often suffer from:
1. **Duplicate attendance entries** (proxy check-ins or multiple submissions by the same student).
2. **Race conditions** and out-of-order sequencing in asynchronous environments.
3. **Lack of hardware-level transparency** for engineering students learning digital systems principles.

### Project Objectives
* Implement an exact **4-bit synchronous binary counter** based on flip-flop excitation logic.
* Decouple the digital counter state ($0000_2$ to $1111_2$, mod 16) from global record uniqueness (`REC-001`, `REC-002`, ...).
* Prevent duplicate attendance for the same student within an active session.
* Provide an interactive **Flip-Flop Simulator** with single-step manual clock control.
* Display the complete **16-state Truth Table** showing both T-flip-flop and D-flip-flop inputs.
* Supply a comprehensive automated test suite with **20 executable test cases** (10 Normal + 10 Edge/Fault).

---

## 3. System Architecture

```
                                  [ User Interface (Browser) ]
                                                │
                          ┌─────────────────────┴─────────────────────┐
                          ▼                                           ▼
                 Web Pages (Jinja2)                           REST API (JSON)
            (Dashboard, Generator, Simulator,           (/api/status, /api/generate-token,
             Truth Table, Records, Tests)                /api/reset, /api/clock-pulse, etc.)
                          │                                           │
                          └─────────────────────┬─────────────────────┘
                                                ▼
                                         [ app.py ] (Flask)
                                                │
                                                ▼
                                   [ token_generator.py ]
                                      (TokenManager)
                                 ┌──────────────┴──────────────┐
                                 ▼                             ▼
                      [ digital_logic.py ]           [ CSV Persistence ]
                     (FourBitCounter: Q3..Q0)    (attendance_data.csv,
                     T & D Flip-Flop Equations   system_events.csv,
                                                 synthetic_students.csv)
```

---

## 4. Digital Logic & Flip-Flop Excitation Equations

The 4-bit synchronous binary counter maintains internal states:
$$\text{State} = [Q_3, Q_2, Q_1, Q_0]$$
where $Q_3$ is the Most Significant Bit (MSB, weight 8) and $Q_0$ is the Least Significant Bit (LSB, weight 1).

### Counting Sequence
$$0000 \to 0001 \to 0010 \to 0011 \to 0100 \to 0101 \to 0110 \to 0111 \to 1000 \to 1001 \to 1010 \to 1011 \to 1100 \to 1101 \to 1110 \to 1111 \to 0000$$

### T-Flip-Flop Excitation Logic
In a T-flip-flop, the state transitions according to $Q^+ = Q \oplus T$.
For synchronous up-counting, each flip-flop toggles only when all lower-order bits are 1:
* $T_0 = 1$ (toggles on every active clock pulse)
* $T_1 = Q_0$
* $T_2 = Q_1 \land Q_0$
* $T_3 = Q_2 \land Q_1 \land Q_0$

Next-state computation:
$$Q_0^+ = Q_0 \oplus T_0$$
$$Q_1^+ = Q_1 \oplus T_1$$
$$Q_2^+ = Q_2 \oplus T_2$$
$$Q_3^+ = Q_3 \oplus T_3$$

### Equivalent D-Flip-Flop Logic
In a D-flip-flop, $Q^+ = D$. The equivalent next-state equations are:
* $D_0 = \overline{Q_0}$
* $D_1 = Q_1 \oplus Q_0$
* $D_2 = Q_2 \oplus (Q_1 \land Q_0)$
* $D_3 = Q_3 \oplus (Q_2 \land Q_1 \land Q_0)$

---

## 5. Token Generation & Design Decisions

### Token Format & Modulo-16 Behavior
* A token directly maps the 4-bit counter value formatted with zero-padding:  
  `0001` $\to$ `ATT-001`, `0010` $\to$ `ATT-002`, ..., `1111` $\to$ `ATT-015`, `0000` $\to$ `ATT-000`.
* Because a 4-bit counter has only 16 states ($0$ through $15$), counter values repeat after overflow or reset.
* To distinguish generations, the system tracks and displays an independent **Cycle / Session Index** (`Cycle 1`, `Cycle 2`, ...).

### Decoupling Digital Counter from Record Uniqueness
* In digital systems, a 4-bit hardware counter wraps from `1111` back to `0000`. We do **not** artificially alter the digital counter to make it globally unique.
* Instead, the system assigns a globally unique, non-reusable **Record ID** (`REC-001`, `REC-002`, `REC-003`, ...) to every accepted attendance event.
* Record IDs remain strictly unique even across counter overflows and manual resets.

### Duplicate Attendance Prevention
* A student (identified by Student ID, e.g., `STU001`) is only permitted attendance once per active session.
* If a duplicate request is submitted:
  1. The request is rejected with `DUPLICATE_STUDENT_ATTENDANCE`.
  2. The digital counter does **not** advance.
  3. No token is issued and no attendance record is saved.
  4. The duplicate counter and system fault counts are incremented.
  5. An entry is written to the `system_events.csv` audit log.

### Reset & Overflow Behavior
* **Reset Operation:** When the user clicks **Reset Counter**:
  - $Q_3 Q_2 Q_1 Q_0$ is set to `0000` and decimal to `0`.
  - The `Cycle` number is incremented.
  - A `RESET` event is recorded in the audit log.
  - Historical records are preserved; `Record ID` sequence continues without reuse.
* **Counter Overflow ($1111 \to 0000$):**
  - When the counter is at $1111_2$ ($15_{10}$) and the next clock pulse arrives, state wraps to $0000_2$.
  - The `Cycle` number increments.
  - A `COUNTER_OVERFLOW` event is recorded in the audit log.
  - Record IDs remain sequential and unique.

---

## 6. Synthetic Dataset

To ensure student privacy, only synthetic data is utilized:
* `data/synthetic_students.csv`: Contains 20 simulated engineering student records (`STU001` to `STU020`).
* `data/attendance_data.csv`: Stores attendance records with columns:
  `record_id, student_id, student_name, token, cycle, counter_value, binary_state, timestamp, status`
* `data/system_events.csv`: Audit trail for `SYSTEM_INIT`, `TOKEN_GENERATED`, `RESET`, `COUNTER_OVERFLOW`, and `DUPLICATE_STUDENT_ATTENDANCE`.
* `data/test_cases.csv`: Definitions of the 20 test specifications.

---

## 7. Project Structure

```
flip-flop-attendance/
│
├── app.py                     # Flask web server and REST API controller
├── digital_logic.py           # Pure 4-bit synchronous counter & flip-flop logic
├── token_generator.py         # TokenManager, business rules, duplicate check, CSV I/O
├── requirements.txt           # Python dependency specifications
├── README.md                  # Comprehensive academic documentation
│
├── data/
│   ├── synthetic_students.csv # Synthetic student roster
│   ├── attendance_data.csv    # Persistent attendance records
│   ├── system_events.csv      # Audit event log
│   └── test_cases.csv         # Test suite specifications
│
├── tests/
│   └── test_attendance.py     # 20 automated unit tests runnable via CLI or Web UI
│
├── templates/
│   ├── base.html              # Shared layout, navigation sidebar, LED monitor
│   ├── index.html             # System Dashboard with live KPIs & event log
│   ├── generator.html         # Token Generator with animated state transitions
│   ├── simulator.html         # 4-bit Flip-Flop Circuit Simulator & clock trigger
│   ├── truth_table.html       # 16-State Truth Table with T & D excitation values
│   ├── records.html           # Searchable attendance log & CSV export
│   ├── test_cases.html        # Interactive test runner interface
│   ├── analytics.html         # Chart.js analytics & digital logic insights
│   └── about.html             # Academic project report and circuit theory
│
└── static/
    ├── css/
    │   └── style.css          # Tech-themed styles, glowing LEDs, circuit cards
    └── js/
        └── script.js          # REST API handlers, LED updates, charts, filters
```

---

## 8. Installation & Setup

### Prerequisites
* Python 3.10+ (tested on Python 3.12)
* `pip` package manager

### Steps
1. Navigate to the project root directory:
   ```powershell
   cd C:\Users\HP\.gemini\antigravity\scratch\flip-flop-attendance
   ```

2. Install the required dependencies:
   ```powershell
   py -3 -m pip install -r requirements.txt
   ```

3. Run the automated test suite:
   ```powershell
   py -3 -m unittest discover -s tests -p "test_*.py" -v
   ```

4. Start the Flask application:
   ```powershell
   py -3 app.py
   ```

5. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

---

## 9. REST API Reference

| Method | Endpoint | Description | Sample Response / Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/status` | Returns live counter state, flip-flop bits, and KPI counters | `{"binary_state": "0001", "counter_value": 1, "cycle": 1, ...}` |
| `POST` | `/api/generate-token` | Processes attendance and triggers clock pulse | `Body: {"student_id": "STU001", "student_name": "Aarav Sharma"}` |
| `POST` | `/api/clock-pulse` | Triggers a single manual clock pulse for the simulator | `{"success": true, "token": "ATT-002", "transition": {...}}` |
| `POST` | `/api/reset` | Resets counter to `0000`, increments cycle, preserves data | `{"success": true, "message": "Counter reset successfully..."}` |
| `POST` | `/api/clear` | Reinitializes attendance records for a clean demonstration | `{"success": true, "message": "Session cleared..."}` |
| `GET` | `/api/records` | Returns attendance records with optional `?search=` and `?cycle=` | `{"count": 5, "records": [...]}` |
| `GET` | `/api/export-records` | Streams attendance records as a downloadable `.csv` file | Attachment: `flipflop_attendance_records.csv` |
| `GET` | `/api/truth-table` | Returns all 16 rows of the counter excitation table | `{"rows": 16, "truth_table": [...]}` |
| `GET` | `/api/test-cases` | Dynamically executes all 20 test cases and returns results | `{"total": 20, "passed": 20, "pass_rate": "100.0%", ...}` |
| `GET` | `/api/analytics` | Aggregated metrics for Chart.js rendering | `{"cycle_distribution": {...}, "bit_frequencies": {...}}` |
| `GET` | `/api/students` | Returns synthetic student roster for quick auto-fill | `{"count": 20, "students": [...]}` |

---

## 10. Automated Test Suite (20 Test Cases)

| Test ID | Category | Description | Input | Expected Output | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC01** | NORMAL | First token generation | `STU001, Aarav Sharma` | `ATT-001`, State `0001`, Cycle `1` | **PASS** |
| **TC02** | NORMAL | Sequential token generation | `STU002, Diya Patel` | `ATT-002`, State `0010`, Cycle `1` | **PASS** |
| **TC03** | NORMAL | Counter increment | 2 clock pulses | Decimal `2` | **PASS** |
| **TC04** | NORMAL | Binary state correctness | Decimal `3` | Binary `'0011'`, Bits `[0,0,1,1]` | **PASS** |
| **TC05** | NORMAL | Decimal conversion | Binary `'0111'` | Decimal `7` | **PASS** |
| **TC06** | NORMAL | Token format validation | Counter `4` $\to$ `5` | Format `ATT-005` | **PASS** |
| **TC07** | NORMAL | Multiple students | 5 distinct students | 5 tokens, Counter at `5` | **PASS** |
| **TC08** | NORMAL | Attendance record creation | Valid check-in | Record saved with unique ID | **PASS** |
| **TC09** | NORMAL | Flip-flop state transition | State `0011` with clock | State `0100`, $T_2=1$ carry | **PASS** |
| **TC10** | NORMAL | Truth table validation | Full table check | 16 rows, $1111 \to 0000$ wrap | **PASS** |
| **TC11** | EDGE/FAULT | Empty student ID | `student_id = ""` | Error `EMPTY_STUDENT_ID`, rejected | **PASS** |
| **TC12** | EDGE/FAULT | Empty student name | `student_name = " "` | Error `EMPTY_STUDENT_NAME`, rejected | **PASS** |
| **TC13** | EDGE/FAULT | Duplicate student attendance | Resubmit `STU001` | Error `DUPLICATE_STUDENT_ATTENDANCE` | **PASS** |
| **TC14** | EDGE/FAULT | Counter overflow $1111 \to 0000$ | Clock at state `1111` | State `0000`, `Cycle` increments | **PASS** |
| **TC15** | EDGE/FAULT | Counter reset | Reset button | State `0000`, historical records kept | **PASS** |
| **TC16** | EDGE/FAULT | Record ID uniqueness after reset | Post-reset check-in | `REC-001` followed by `REC-002` | **PASS** |
| **TC17** | EDGE/FAULT | Record ID uniqueness after overflow | Rollover check-ins | Zero duplicate Record IDs across cycles | **PASS** |
| **TC18** | EDGE/FAULT | Invalid student ID format | `ID!@#$` | Error `INVALID_STUDENT_ID` | **PASS** |
| **TC19** | EDGE/FAULT | Invalid student name format | `123456` | Error `INVALID_STUDENT_NAME` | **PASS** |
| **TC20** | EDGE/FAULT | Reset event logging | Counter reset | `RESET` entry in `system_events.csv` | **PASS** |

---

## 11. Screenshots & Demonstration Guide

1. **Dashboard (`/`):**
   - Live KPI cards for Latest Token, Counter Value, Successful Tokens, and Faults.
   - Glowing LED indicators showing active states of $Q_3, Q_2, Q_1, Q_0$.
   - Live audit activity log updating on every event.
2. **Token Generator (`/generator`):**
   - Quick-fill dropdown from synthetic roster.
   - Animated digital state transition card showing Previous State $\to$ Clock Pulse $\to$ Next State.
3. **Flip-Flop Simulator (`/simulator`):**
   - Interactive flip-flop circuit boxes ($Q_3, Q_2, Q_1, Q_0$) with active HIGH/LOW indicators.
   - "Send Clock Pulse" single-step button to demonstrate manual toggle progression.
4. **Truth Table (`/truth-table`):**
   - Complete 16-row excitation table with instant search and active-state row highlighting.
5. **Attendance Records (`/records`):**
   - Searchable, cycle-filterable log with direct "Export to CSV" download.
6. **Test Cases (`/test-cases`):**
   - "Run All 20 Test Cases Now" button with real-time pass/fail badges and technical explanations.
7. **Analytics (`/analytics`):**
   - Chart.js charts: Tokens per Cycle, Verification & Fault Donut, and Flip-Flop Bit Frequency.
8. **About Project (`/about`):**
   - Detailed academic report, equations, and applications for EC2201 Digital Systems.

---

## 12. References

1. M. Morris Mano & Michael D. Ciletti, *Digital Design: With an Introduction to the Verilog HDL*, 5th Edition, Pearson.
2. Ronald J. Tocci, Neal S. Widmer, & Gregory L. Moss, *Digital Systems: Principles and Applications*, 12th Edition, Pearson.
3. Thomas L. Floyd, *Digital Fundamentals*, 11th Edition, Pearson.
