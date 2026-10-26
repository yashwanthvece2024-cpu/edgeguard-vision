document.addEventListener("DOMContentLoaded", () => {
    let globalChartData = []; 

    // 1. Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.workspace-view');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            navItems.forEach(n => n.classList.remove('active'));
            views.forEach(v => v.classList.add('hidden'));
            views.forEach(v => v.classList.remove('active-view'));
            
            item.classList.add('active');
            const target = item.dataset.target;
            document.getElementById(target).classList.remove('hidden');
            document.getElementById(target).classList.add('active-view');
            document.getElementById('current-tab-title').textContent = item.textContent.replace(/[^\w\s]/gi, '').trim();

            if (target === 'view-overview') fetchOverview();
            if (target === 'view-history') fetchHistory();
            if (target === 'view-workspace' && globalChartData.length > 0) {
                setTimeout(() => drawChart(globalChartData), 50); 
            }
        });
    });

    // 2. Health Init
    fetch('/health').then(res => res.json()).then(data => {
        if(data.status === 'healthy') {
            document.getElementById('topbar-cv-version').textContent = data.opencv_version;
            document.getElementById('status-overview-cv').textContent = data.opencv_version;
            document.getElementById('status-cv-full').textContent = `OpenCV ${data.opencv_version}`;
        }
    }).catch(() => document.getElementById('nav-system-status').textContent = 'Degraded');

    setInterval(() => {
        document.getElementById('current-datetime').textContent = new Date().toLocaleString([], {month:'short', day:'numeric', year:'numeric', hour:'2-digit', minute:'2-digit'});
    }, 1000);

    // 3. Tab Data
    async function fetchOverview() {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            const metrics = data.metrics;
            
            document.getElementById('kpi-total').textContent = metrics.total;
            document.getElementById('kpi-anomalies').textContent = metrics.anomalies;
            document.getElementById('kpi-stable').textContent = metrics.stable;
            document.getElementById('kpi-uncertain').textContent = metrics.uncertain;
            
            document.getElementById('donut-total').textContent = metrics.total;
            document.getElementById('leg-stable').textContent = metrics.stable;
            document.getElementById('leg-anomalies').textContent = metrics.anomalies;
            document.getElementById('leg-uncertain').textContent = metrics.uncertain;
            
            if(metrics.total > 0) {
                const pStable = (metrics.stable / metrics.total) * 100;
                const pAnomaly = (metrics.anomalies / metrics.total) * 100;
                document.getElementById('outcome-donut').style.background = 
                    `conic-gradient(var(--green) 0% ${pStable}%, var(--red) ${pStable}% ${pStable + pAnomaly}%, var(--amber) ${pStable + pAnomaly}% 100%)`;
            }

            const tbody = document.getElementById('overview-recent-tbody');
            tbody.innerHTML = '';
            if(data.recent.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No recent inspections found.</td></tr>';
            } else {
                data.recent.forEach(row => {
                    const tr = document.createElement('tr');
                    let badgeClass = row.status.includes('ANOMALY') ? 'red' : row.status === 'UNCERTAIN' ? 'amber' : 'green';
                    tr.innerHTML = `<td><span style="font-family:monospace; color:var(--text-muted);">${row.id.substring(0,8)}</span></td>
                                    <td>${new Date(row.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                                    <td>${row.filename}</td>
                                    <td><span class="badge ${badgeClass}">${row.status.replace('COMPLETED_', '')}</span></td>
                                    <td>${row.scans}</td>`;
                    tbody.appendChild(tr);
                });
            }

            if(data.latest) {
                document.getElementById('latest-id').textContent = data.latest.id.substring(0,13) + "...";
                document.getElementById('latest-time').textContent = new Date(data.latest.timestamp).toLocaleString();
                document.getElementById('latest-file').textContent = data.latest.filename;
            }

            drawOverviewBarChart(metrics);
        } catch (e) { console.error("Overview stats fetch failed:", e); }
    }
    document.getElementById('refresh-overview')?.addEventListener('click', fetchOverview);
    
    async function fetchHistory() {
        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            const tbody = document.getElementById('history-tbody');
            tbody.innerHTML = '';
            data.history.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${new Date(row.timestamp).toLocaleString()}</td><td>${row.filename}</td>
                    <td><span class="badge ${row.status.includes('ANOMALY') ? 'red' : row.status === 'UNCERTAIN' ? 'amber' : 'green'}">${row.status.replace('COMPLETED_', '')}</span></td>
                    <td>${row.scans}</td><td>${row.variance.toFixed(4)}</td>`;
                tbody.appendChild(tr);
            });
        } catch (e) {}
    }

    // 4. Eval Lab
    document.getElementById('run-eval-btn').addEventListener('click', async (e) => {
        const btn = e.target;
        btn.textContent = "Running Pipeline...";
        btn.disabled = true;
        try {
            const res = await fetch('/api/evaluate');
            const data = await res.json();
            const tbody = document.getElementById('eval-tbody');
            tbody.innerHTML = '';
            data.evaluation.forEach(row => {
                const tr = document.createElement('tr');
                let badgeClass = row.status.includes('ANOMALY') ? 'red' : row.status === 'UNCERTAIN' ? 'amber' : 'green';
                if (row.status.includes('ERROR') || row.status === 'FILE_NOT_FOUND') badgeClass = 'dark';
                
                tr.innerHTML = `<td>${row.file}</td><td><span class="badge ${badgeClass}">${row.status.replace('COMPLETED_','')}</span></td><td>${row.scans}</td><td>${row.variance.toFixed(4)}</td>`;
                if(row.error) tr.innerHTML += `<tr><td colspan="4" style="color:var(--amber); font-size:0.75rem;">Error details: ${row.error}</td></tr>`;
                tbody.appendChild(tr);
            });
        } catch(err) { alert("Network connection failed during Eval."); }
        finally { btn.textContent = "Run Evaluation Suite"; btn.disabled = false; }
    });

    // 5. Video Upload & Scan Workflow
    const fileInput = document.getElementById('video-file');
    const analyzeBtn = document.getElementById('analyze-btn');
    const filenameDisplay = document.getElementById('filename-display');
    let currentVideoUrl = null;

    fileInput.addEventListener('change', (e) => {
        if (e.target.files[0]) {
            filenameDisplay.textContent = e.target.files[0].name;
            analyzeBtn.disabled = false;
        }
    });

    analyzeBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        const file = fileInput.files[0];
        if (!file) return;

        analyzeBtn.disabled = true;
        document.getElementById('loading-overlay').classList.remove('hidden');
        document.getElementById('results-dashboard').classList.add('hidden');
        const startTime = Date.now();
        const formData = new FormData();
        formData.append('video', file);

        try {
            const response = await fetch('/api/analyze', { method: 'POST', body: formData });
            if (!response.ok) throw new Error(await response.text());
            const data = await response.json();
            
            if(currentVideoUrl) URL.revokeObjectURL(currentVideoUrl);
            currentVideoUrl = URL.createObjectURL(file);
            document.getElementById('result-video').src = currentVideoUrl;
            
            const endTime = Date.now();
            displayResults(data.result, Math.floor((endTime - startTime) / 1000));
        } catch (error) {
            alert('Analysis Error: ' + error.message);
            analyzeBtn.disabled = false;
        } finally {
            document.getElementById('loading-overlay').classList.add('hidden');
        }
    });

    function displayResults(result, secondsElapsed) {
        document.getElementById('results-dashboard').classList.remove('hidden');
        
        const hero = document.getElementById('result-hero');
        const badge = document.getElementById('final-status-badge');
        const title = document.getElementById('result-title');
        const desc = document.getElementById('result-desc');
        const recText = document.getElementById('recommendation-text');
        
        if (result.status === 'UNCERTAIN') {
            badge.className = 'badge amber'; badge.textContent = 'UNCERTAIN';
            hero.style.background = 'rgba(245,158,11,0.05)'; hero.style.border = '1px solid rgba(245,158,11,0.2)';
            title.textContent = 'CAMERA MOTION DETECTED'; title.style.color = 'var(--amber)';
            desc.textContent = 'Unable to reliably isolate machinery motion due to global shake.';
        } else if (result.status.includes('ANOMALY')) {
            badge.className = 'badge red'; badge.textContent = 'ANOMALY DETECTED';
            hero.style.background = 'rgba(239,68,68,0.05)'; hero.style.border = '1px solid rgba(239,68,68,0.2)';
            title.textContent = 'COMPLETED_ANOMALY'; title.style.color = 'var(--red)';
            desc.textContent = 'Irregular motion confirmed in machinery components.';
        } else {
            badge.className = 'badge green'; badge.textContent = 'STABLE';
            hero.style.background = 'rgba(16,185,129,0.05)'; hero.style.border = '1px solid rgba(16,185,129,0.2)';
            title.textContent = 'COMPLETED_STABLE'; title.style.color = 'var(--green)';
            desc.textContent = 'Normal operation verified.';
        }
        
        recText.textContent = result.recommendation;
        document.getElementById('scan-count').textContent = result.scans_performed;
        document.getElementById('motion-variance').textContent = result.metrics.variance.toFixed(4);
        document.getElementById('motion-avg').textContent = result.metrics.mean_motion.toFixed(4);
        document.getElementById('confidence-val').textContent = (result.metrics.confidence || 0.82).toFixed(2);
        
        const min = Math.floor(secondsElapsed / 60).toString().padStart(2, '0');
        const sec = (secondsElapsed % 60).toString().padStart(2, '0');
        document.getElementById('proc-time').textContent = `${min}:${sec}`;

        if(result.scans_performed > 1) document.getElementById('thumb-detailed').classList.remove('hidden');
        else document.getElementById('thumb-detailed').classList.add('hidden');

        globalChartData = result.metrics.timeline;
        drawChart(globalChartData);

        const roiBox = document.getElementById('roi-box');
        roiBox.classList.add('hidden');
        const roiStep = result.trace.find(t => t.parameters && t.parameters.roi);
        if (roiStep && roiStep.parameters.roi) {
            roiBox.classList.remove('hidden');
            const [x, y, w, h] = roiStep.parameters.roi;
            roiBox.style.left = `${(x/640)*100}%`; roiBox.style.top = `${(y/480)*100}%`;
            roiBox.style.width = `${(w/640)*100}%`; roiBox.style.height = `${(h/480)*100}%`;
        }

        const buildTraceRows = (tbody) => {
            tbody.innerHTML = '';
            result.trace.forEach((entry, idx) => {
                const time = new Date(entry.timestamp * 1000).toISOString().split('T')[1].substring(0,8);
                let prm = '';
                for (const [k, v] of Object.entries(entry.parameters)) {
                    let cleanV = typeof v === 'string' ? v.replace(/^.*[\\\/]/, '') : JSON.stringify(v);
                    prm += `<span class="param-line"><strong>${k}:</strong> ${cleanV}</span>`;
                }
                
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><span class="num-circle">${idx + 1}</span></td>
                    <td>${time}</td>
                    <td><strong>${entry.operation}</strong></td>
                    <td class="td-params">${prm || 'N/A'}</td>
                    <td>${entry.reason}</td>
                    <td><span style="color: ${entry.result.includes('Uncertain') ? 'var(--amber)' : 'var(--cyan)'}">●</span> ${entry.result}</td>
                    <td>${entry.next_action}</td>
                `;
                tbody.appendChild(tr);
            });
        };

        buildTraceRows(document.getElementById('trace-tbody'));
        buildTraceRows(document.getElementById('global-trace-tbody'));
    }

    function drawChart(dataPoints) {
        if (!dataPoints || !dataPoints.length) return;
        const canvas = document.getElementById('motionChart');
        const wrapper = canvas.parentElement;
        if(wrapper.clientWidth === 0) return; 
        
        canvas.width = wrapper.clientWidth; canvas.height = wrapper.clientHeight;
        const ctx = canvas.getContext('2d'), W = canvas.width, H = canvas.height, pad = 20;
        
        ctx.clearRect(0, 0, W, H);
        const maxVal = Math.max(...dataPoints, 2.0); 
        
        ctx.strokeStyle = '#1e2d4a'; ctx.lineWidth = 1; ctx.beginPath();
        for(let i=0; i<=4; i++) {
            const y = pad + (i * (H - 2*pad)/4);
            ctx.moveTo(pad, y); ctx.lineTo(W - pad, y);
            ctx.fillStyle = '#8ba0c4'; ctx.font = '10px sans-serif';
            ctx.fillText((maxVal - (i * maxVal/4)).toFixed(1), 0, y + 4);
        }
        ctx.stroke();

        ctx.strokeStyle = '#00d2ff'; ctx.lineWidth = 2; ctx.beginPath();
        const stepX = (W - 2 * pad) / (Math.max(1, dataPoints.length - 1));
        
        dataPoints.forEach((val, i) => {
            const x = pad + (i * stepX), y = H - pad - ((val / maxVal) * (H - 2 * pad));
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();
        
        ctx.lineTo(W - pad, H - pad); ctx.lineTo(pad, H - pad); ctx.closePath();
        const grad = ctx.createLinearGradient(0, 0, 0, H);
        grad.addColorStop(0, 'rgba(0, 210, 255, 0.2)'); grad.addColorStop(1, 'rgba(0, 210, 255, 0)');
        ctx.fillStyle = grad; ctx.fill();
    }

    function drawOverviewBarChart(metrics) {
        const canvas = document.getElementById('barChart');
        if(!canvas) return;
        const wrapper = canvas.parentElement;
        if(wrapper.clientWidth === 0) return;
        
        canvas.width = wrapper.clientWidth; canvas.height = wrapper.clientHeight;
        const ctx = canvas.getContext('2d'), W = canvas.width, H = canvas.height, pad = 20;
        
        ctx.clearRect(0, 0, W, H);
        const maxVal = Math.max(metrics.stable, metrics.anomalies, metrics.uncertain, 5); 
        
        ctx.strokeStyle = '#1e2d4a'; ctx.lineWidth = 1; ctx.beginPath();
        for(let i=0; i<=4; i++) {
            const y = pad + (i * (H - 2*pad)/4);
            ctx.moveTo(pad, y); ctx.lineTo(W - pad, y);
        }
        ctx.stroke();

        const barWidth = 40;
        const spacing = (W - (2 * pad) - (3 * barWidth)) / 4;
        
        const drawBar = (idx, val, color) => {
            const x = pad + spacing + (idx * (barWidth + spacing));
            const barH = (val / maxVal) * (H - 2*pad);
            const y = H - pad - barH;
            ctx.fillStyle = color;
            ctx.fillRect(x, y, barWidth, barH);
        };

        drawBar(0, metrics.stable, '#10b981');   // Green
        drawBar(1, metrics.anomalies, '#ef4444'); // Red
        drawBar(2, metrics.uncertain, '#f59e0b'); // Amber
    }
});