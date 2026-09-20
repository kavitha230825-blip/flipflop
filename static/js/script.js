/**
 * EC2201 Digital Systems - Flip-Flop Attendance Token Generator
 * Main Frontend Controller
 */

// Toast notification helper
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `custom-toast toast-${type}`;
    
    let icon = 'bi-info-circle-fill';
    if (type === 'success') icon = 'bi-check-circle-fill text-success';
    else if (type === 'error') icon = 'bi-exclamation-triangle-fill text-danger';
    else if (type === 'warning') icon = 'bi-exclamation-circle-fill text-warning';

    toast.innerHTML = `
        <i class="bi ${icon} fs-5"></i>
        <div class="flex-grow-1">
            <div class="fw-semibold">${message}</div>
        </div>
        <button type="button" class="btn-close btn-close-white ms-2" onclick="this.parentElement.remove()"></button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        if (toast.parentElement) toast.remove();
    }, 4500);
}

// Update LEDs based on 4-bit binary string "Q3Q2Q1Q0"
function updateLEDs(binaryString) {
    if (!binaryString || binaryString.length !== 4) return;
    const bits = binaryString.split('');
    // bits[0] is Q3, bits[1] is Q2, bits[2] is Q1, bits[3] is Q0
    const ledIds = ['led-q3', 'led-q2', 'led-q1', 'led-q0'];
    ledIds.forEach((id, idx) => {
        const el = document.getElementById(id);
        if (el) {
            if (bits[idx] === '1') {
                el.classList.add('on');
                el.innerText = '1';
            } else {
                el.classList.remove('on');
                el.innerText = '0';
            }
        }
    });
}

// Refresh Live System Status from API
async function refreshStatus() {
    try {
        const res = await fetch('/api/status');
        if (!res.ok) return;
        const data = await res.json();

        // Update elements if they exist on the page
        const elToken = document.getElementById('stat-current-token');
        if (elToken) elToken.innerText = data.current_token || 'None';

        const elDec = document.getElementById('stat-counter-val');
        if (elDec) elDec.innerText = data.counter_value;

        const elBin = document.getElementById('stat-binary-state');
        if (elBin) elBin.innerText = data.binary_state;

        const elCycle = document.getElementById('stat-cycle');
        if (elCycle) elCycle.innerText = data.cycle;

        const elRecords = document.getElementById('stat-total-records');
        if (elRecords) elRecords.innerText = data.total_records;

        const elSucc = document.getElementById('stat-successful-tokens');
        if (elSucc) elSucc.innerText = data.successful_tokens;

        const elDup = document.getElementById('stat-duplicate-attempts');
        if (elDup) elDup.innerText = data.duplicate_attempts;

        const elFault = document.getElementById('stat-fault-count');
        if (elFault) elFault.innerText = data.fault_count;

        updateLEDs(data.binary_state);

        return data;
    } catch (err) {
        console.error("Error refreshing status:", err);
    }
}

// Token Generator Form Handler
async function handleGenerateToken(e) {
    if (e) e.preventDefault();
    const idInput = document.getElementById('student_id');
    const nameInput = document.getElementById('student_name');
    const btn = document.getElementById('btn-generate');

    if (!idInput || !nameInput) return;

    const student_id = idInput.value.trim();
    const student_name = nameInput.value.trim();

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Processing Clock Pulse...';
    }

    try {
        const res = await fetch('/api/generate-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ student_id, student_name })
        });
        const data = await res.json();

        const resultCard = document.getElementById('generator-result-card');
        const transitionDisplay = document.getElementById('transition-display');

        if (data.success) {
            showToast(`Attendance Confirmed: Token ${data.token} generated for ${data.student_name}`, 'success');
            
            if (resultCard) {
                resultCard.classList.remove('d-none');
                document.getElementById('res-token').innerText = data.token;
                document.getElementById('res-record-id').innerText = data.record_id;
                document.getElementById('res-cycle').innerText = `Cycle ${data.cycle}`;
                document.getElementById('res-student').innerText = `${data.student_name} (${data.student_id})`;
                document.getElementById('res-counter').innerText = `${data.counter_value} (Binary: ${data.binary_state})`;
            }

            if (transitionDisplay && data.transition) {
                const tr = data.transition;
                document.getElementById('tr-prev').innerText = tr.previous_state.binary;
                document.getElementById('tr-next').innerText = tr.current_state.binary;
                document.getElementById('tr-t-excitations').innerText = `T3=${tr.excitations.T.t3}, T2=${tr.excitations.T.t2}, T1=${tr.excitations.T.t1}, T0=${tr.excitations.T.t0}`;
                document.getElementById('tr-d-excitations').innerText = `D3=${tr.excitations.D.d3}, D2=${tr.excitations.D.d2}, D1=${tr.excitations.D.d1}, D0=${tr.excitations.D.d0}`;
            }

            if (data.overflow) {
                showToast(`Counter Overflow Event: 1111 -> 0000. System advanced to Cycle ${data.cycle}!`, 'warning');
            }

            // Clear inputs for next entry
            idInput.value = '';
            nameInput.value = '';
        } else {
            showToast(`Rejected: ${data.message}`, 'error');
            if (resultCard) {
                resultCard.classList.remove('d-none');
                document.getElementById('res-token').innerText = 'REJECTED';
                document.getElementById('res-record-id').innerText = data.error_code;
                document.getElementById('res-cycle').innerText = '-';
                document.getElementById('res-student').innerText = `${student_name || 'N/A'} (${student_id || 'N/A'})`;
                document.getElementById('res-counter').innerText = data.message;
            }
        }

        await refreshStatus();
    } catch (err) {
        showToast(`System Error: ${err.message}`, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-cpu-fill me-1"></i> Generate Attendance Token';
        }
    }
}

// Manual Clock Pulse trigger (Simulator)
async function triggerClockPulse() {
    const pulseBtn = document.getElementById('btn-clock-pulse');
    if (pulseBtn) {
        pulseBtn.disabled = true;
        pulseBtn.classList.add('pulse-highlight');
    }

    try {
        const res = await fetch('/api/clock-pulse', { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            const tr = data.transition;
            showToast(`Clock Pulse Triggered: State -> ${data.binary_state} (Dec: ${data.counter_value})`, 'info');

            // Update simulator display cards
            const prevEl = document.getElementById('sim-prev-binary');
            if (prevEl) prevEl.innerText = tr.previous_state.binary;

            const currEl = document.getElementById('sim-curr-binary');
            if (currEl) currEl.innerText = data.binary_state;

            const decEl = document.getElementById('sim-decimal-val');
            if (decEl) decEl.innerText = data.counter_value;

            const tokEl = document.getElementById('sim-token');
            if (tokEl) tokEl.innerText = `${data.token} (Cycle ${data.cycle})`;

            // Update individual flip-flop indicators
            const ffMap = [
                { q: 'q3', val: tr.current_state.q3, t: tr.excitations.T.t3, d: tr.excitations.D.d3 },
                { q: 'q2', val: tr.current_state.q2, t: tr.excitations.T.t2, d: tr.excitations.D.d2 },
                { q: 'q1', val: tr.current_state.q1, t: tr.excitations.T.t1, d: tr.excitations.D.d1 },
                { q: 'q0', val: tr.current_state.q0, t: tr.excitations.T.t0, d: tr.excitations.D.d0 }
            ];

            ffMap.forEach(item => {
                const valEl = document.getElementById(`sim-val-${item.q}`);
                if (valEl) {
                    valEl.innerText = item.val;
                    if (item.val === 1) valEl.classList.add('high');
                    else valEl.classList.remove('high');
                }
                const tEl = document.getElementById(`sim-t-${item.q}`);
                if (tEl) tEl.innerText = item.t;
                const dEl = document.getElementById(`sim-d-${item.q}`);
                if (dEl) dEl.innerText = item.d;
            });

            if (data.overflow) {
                showToast(`Counter Rollover: 1111 -> 0000 (Advanced to Cycle ${data.cycle})`, 'warning');
            }

            await refreshStatus();
        }
    } catch (err) {
        showToast(`Clock Pulse Error: ${err.message}`, 'error');
    } finally {
        setTimeout(() => {
            if (pulseBtn) {
                pulseBtn.disabled = false;
                pulseBtn.classList.remove('pulse-highlight');
            }
        }, 300);
    }
}

// Reset Counter
async function handleResetCounter() {
    if (!confirm("Are you sure you want to RESET the digital counter to 0000? (Historical records will be preserved; Cycle will increment).")) {
        return;
    }

    try {
        const res = await fetch('/api/reset', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast("Counter reset to 0000. New cycle started. Records preserved.", "warning");
            await refreshStatus();
            // If on simulator page, update visual cards
            const currEl = document.getElementById('sim-curr-binary');
            if (currEl) currEl.innerText = "0000";
            const decEl = document.getElementById('sim-decimal-val');
            if (decEl) decEl.innerText = "0";
            ['q3', 'q2', 'q1', 'q0'].forEach(q => {
                const el = document.getElementById(`sim-val-${q}`);
                if (el) { el.innerText = "0"; el.classList.remove('high'); }
            });
        }
    } catch (err) {
        showToast(`Reset Failed: ${err.message}`, "error");
    }
}

// Clear Data (Administrative fresh demo)
async function handleClearData() {
    if (!confirm("WARNING: This will clear all attendance records and reset system counters to initial state. Proceed?")) {
        return;
    }

    try {
        const res = await fetch('/api/clear', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast("Session cleared successfully.", "info");
            setTimeout(() => window.location.reload(), 800);
        }
    } catch (err) {
        showToast(`Clear failed: ${err.message}`, "error");
    }
}

// Filter and Search Attendance Records Table
function filterRecordsTable() {
    const searchInput = document.getElementById('record-search-input');
    const cycleSelect = document.getElementById('record-cycle-select');
    const table = document.getElementById('records-table');
    if (!table) return;

    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const cycle = cycleSelect ? cycleSelect.value.trim() : 'ALL';

    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    let visibleCount = 0;

    for (let row of rows) {
        const text = row.innerText.toLowerCase();
        const rowCycle = row.getAttribute('data-cycle');

        const matchesQuery = query === '' || text.includes(query);
        const matchesCycle = cycle === 'ALL' || rowCycle === cycle;

        if (matchesQuery && matchesCycle) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    }

    const counterDisplay = document.getElementById('visible-records-count');
    if (counterDisplay) counterDisplay.innerText = visibleCount;
}

// Filter Truth Table
function filterTruthTable() {
    const searchInput = document.getElementById('truth-search-input');
    const table = document.getElementById('truth-table');
    if (!table || !searchInput) return;

    const query = searchInput.value.toLowerCase().trim();
    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    for (let row of rows) {
        const text = row.innerText.toLowerCase();
        if (query === '' || text.includes(query)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    }
}

// Run All Test Cases Dynamically
async function runAllTests() {
    const btn = document.getElementById('btn-run-tests');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Running 20 Tests...';
    }

    try {
        const res = await fetch('/api/test-cases');
        const data = await res.json();

        if (data.success) {
            showToast(`Completed: ${data.passed}/${data.total} tests passed (${data.pass_rate})`, 'success');

            // Update stats banner
            const elPassed = document.getElementById('test-passed-count');
            if (elPassed) elPassed.innerText = data.passed;

            const elTotal = document.getElementById('test-total-count');
            if (elTotal) elTotal.innerText = data.total;

            const elRate = document.getElementById('test-pass-rate');
            if (elRate) elRate.innerText = data.pass_rate;

            // Update table rows
            const tbody = document.getElementById('test-cases-tbody');
            if (tbody && data.results) {
                tbody.innerHTML = '';
                data.results.forEach(tc => {
                    const tr = document.createElement('tr');
                    const badgeClass = tc.status === 'PASS' ? 'bg-success' : 'bg-danger';
                    const catBadge = tc.category === 'NORMAL' ? 'bg-primary' : 'bg-warning text-dark';

                    tr.innerHTML = `
                        <td class="fw-bold font-monospace">${tc.test_id}</td>
                        <td><span class="badge ${catBadge}">${tc.category}</span></td>
                        <td class="fw-semibold">${tc.name}</td>
                        <td><code>${tc.input}</code></td>
                        <td><code>${tc.expected_result}</code></td>
                        <td><code>${tc.actual_result}</code></td>
                        <td><span class="badge ${badgeClass}">${tc.status}</span></td>
                        <td class="small text-muted">${tc.explanation}</td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        }
    } catch (err) {
        showToast(`Test Runner Failed: ${err.message}`, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-play-circle-fill me-1"></i> Re-Run All Test Cases';
        }
    }
}

// Autocomplete Synthetic Student Select
function selectSyntheticStudent(sel) {
    if (!sel || !sel.value) return;
    const parts = sel.value.split('|');
    if (parts.length >= 2) {
        const idInput = document.getElementById('student_id');
        const nameInput = document.getElementById('student_name');
        if (idInput) idInput.value = parts[0];
        if (nameInput) nameInput.value = parts[1];
    }
}

// Auto-run on page load
document.addEventListener('DOMContentLoaded', () => {
    refreshStatus();
});
