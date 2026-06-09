document.addEventListener('DOMContentLoaded', () => {
    // === Application State Management (AppStore) ===
    const AppStore = {
        state: {
            isDataLoaded: false,
            dataset: null,
            activeTab: sessionStorage.getItem('demandalytics_tab') || 'Executive Intelligence Briefing',
            selectedCharts: [],
            primaryColor: '#1e40af', // Premium Dark Blue
            colorTheme: 'blue', // Dynamic color theme ('blue', 'multicolor', 'emerald')
            activeFocusMetric: sessionStorage.getItem('demandalytics_focus_metric') || ''
        },
        listeners: [],
        chartDescriptions: {}, // Cache for AI-generated bullet points
        chartInstances: {}, // Store Chart.js objects for manipulation
        setState(next) {
            this.state = { ...this.state, ...next };
            if (next.activeTab) sessionStorage.setItem('demandalytics_tab', next.activeTab);
            if (next.activeFocusMetric !== undefined) {
                if (next.activeFocusMetric) sessionStorage.setItem('demandalytics_focus_metric', next.activeFocusMetric);
                else sessionStorage.removeItem('demandalytics_focus_metric');
            }
            this.notify();
        },
        subscribe(fn) { this.listeners.push(fn); },
        notify() { this.listeners.forEach(fn => fn(this.state)); }
    };

    // === Global Selectors ===
    const landingSection = document.getElementById('landingSection');
    const workspaceView = document.getElementById('workspaceView');
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const quantumLoader = document.getElementById('quantumLoader');
    const loaderText = document.getElementById('loaderText');
    const activeTabText = document.getElementById('activeTabText');
    const navTabs = document.getElementById('mainNavTabs');
    const exportReportBtn = document.getElementById('exportReportBtn');
    const selectAllCharts = document.getElementById('selectAllCharts');
    const downloadOverlay = document.getElementById('downloadOverlay');
    const overlayTitle = document.getElementById('overlayTitle');
    const startAnalysisBtn = document.getElementById('startAnalysisBtn');
    const colorThemeDropdown = document.getElementById('colorThemeDropdown');

    if (colorThemeDropdown) {
        colorThemeDropdown.addEventListener('change', (e) => {
            const theme = e.target.value;
            AppStore.setState({ colorTheme: theme });

            // Update Global CSS Variables for the entire dashboard UI
            const root = document.documentElement;
            if (theme === 'emerald') {
                root.style.setProperty('--primary', '#059669');
                root.style.setProperty('--primary-hover', '#047857');
                root.style.setProperty('--primary-light', 'rgba(5, 150, 105, 0.05)');
                root.style.setProperty('--primary-medium', 'rgba(5, 150, 105, 0.12)');
                root.style.setProperty('--primary-deep', '#064e3b');
                root.style.setProperty('--accent', '#10b981');
            } else if (theme === 'multicolor') {
                root.style.setProperty('--primary', '#8b5cf6');
                root.style.setProperty('--primary-hover', '#7c3aed');
                root.style.setProperty('--primary-light', 'rgba(139, 92, 246, 0.05)');
                root.style.setProperty('--primary-medium', 'rgba(139, 92, 246, 0.12)');
                root.style.setProperty('--primary-deep', '#5b21b6');
                root.style.setProperty('--accent', '#a855f7');
            } else if (theme === 'sunset') {
                root.style.setProperty('--primary', '#ea580c');
                root.style.setProperty('--primary-hover', '#d97706');
                root.style.setProperty('--primary-light', 'rgba(234, 88, 12, 0.05)');
                root.style.setProperty('--primary-medium', 'rgba(234, 88, 12, 0.12)');
                root.style.setProperty('--primary-deep', '#7c2d12');
                root.style.setProperty('--accent', '#f97316');
            } else if (theme === 'amethyst') {
                root.style.setProperty('--primary', '#6d28d9');
                root.style.setProperty('--primary-hover', '#5b21b6');
                root.style.setProperty('--primary-light', 'rgba(109, 40, 217, 0.05)');
                root.style.setProperty('--primary-medium', 'rgba(109, 40, 217, 0.12)');
                root.style.setProperty('--primary-deep', '#4c1d95');
                root.style.setProperty('--accent', '#8b5cf6');
            } else if (theme === 'ruby') {
                root.style.setProperty('--primary', '#be123c');
                root.style.setProperty('--primary-hover', '#9f1239');
                root.style.setProperty('--primary-light', 'rgba(190, 18, 60, 0.05)');
                root.style.setProperty('--primary-medium', 'rgba(190, 18, 60, 0.12)');
                root.style.setProperty('--primary-deep', '#881337');
                root.style.setProperty('--accent', '#e11d48');
            } else if (theme === 'ocean') {
                root.style.setProperty('--primary', '#0f766e');
                root.style.setProperty('--primary-hover', '#0d9488');
                root.style.setProperty('--primary-light', 'rgba(15, 118, 110, 0.05)');
                root.style.setProperty('--primary-medium', 'rgba(15, 118, 110, 0.12)');
                root.style.setProperty('--primary-deep', '#115e59');
                root.style.setProperty('--accent', '#06b6d4');
            } else {
                root.style.setProperty('--primary', '#1e40af');
                root.style.setProperty('--primary-hover', '#1d4ed8');
                root.style.setProperty('--primary-light', 'rgba(30, 64, 175, 0.05)');
                root.style.setProperty('--primary-medium', 'rgba(30, 64, 175, 0.12)');
                root.style.setProperty('--primary-deep', '#1e3a8a');
                root.style.setProperty('--accent', '#3b82f6');
            }

            if (analysisCache) {
                // Re-render dashboard to apply new colors
                renderDashboard(AppStore.state.activeTab === 'Executive Intelligence Briefing' ? 'executive' : 'pulse');
            }
        });
    }

    let analysisCache = null; // Stores backend analysis results
    let originalAnalysisCache = null; // Stores unfiltered copy for clear/reset

    // === Color Utility ===
    function adjustColor(hex, percent) {
        let r = parseInt(hex.substring(1, 3), 16);
        let g = parseInt(hex.substring(3, 5), 16);
        let b = parseInt(hex.substring(5, 7), 16);
        const factor = percent / 100;
        r = Math.round(r + (255 - r) * factor);
        g = Math.round(g + (255 - g) * factor);
        b = Math.round(b + (255 - b) * factor);
        return "#" + r.toString(16).padStart(2, '0') + g.toString(16).padStart(2, '0') + b.toString(16).padStart(2, '0');
    }

    // === Intelligence Clock System ===
    function startIntelligenceClock() {
        const timeEl = document.getElementById('liveIntelligenceClock');
        const dateEl = document.getElementById('currentIntelligenceDate');

        setInterval(() => {
            const now = new Date();
            if (timeEl) timeEl.textContent = now.toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' });
            if (dateEl) dateEl.textContent = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        }, 1000);
    }
    startIntelligenceClock();

    // === Initialization ===
    function init() {
        const savedData = sessionStorage.getItem('demandalytics_data');
        if (savedData) {
            const parsed = JSON.parse(savedData);

            // Invalidate stale sessionStorage if it still holds old theme names
            const themes = parsed.themes || [];
            const hasOldNames = themes.some(t => t === 'Operational Pulse' || t === 'Data Inventory' || t === 'Analytical Pulse' || t === 'Demand & Trend Analytics' || t === 'Raw Dataset Audit & Search');
            if (hasOldNames) {
                sessionStorage.removeItem('demandalytics_data');
                sessionStorage.removeItem('demandalytics_tab');
                setupChartDefaults();
                applyTabSwitch('Executive Intelligence Briefing');
                return;
            }

            analysisCache = parsed;
            AppStore.setState({ isDataLoaded: true });

            // Critical UI Persistence Fix
            landingSection.classList.add('hidden');
            workspaceView.classList.remove('hidden');

            const btn = document.getElementById('floatingChatBtn');
            if (btn) btn.classList.remove('hidden-chat');

            renderDashboard();
            populateFilters(analysisCache.filter_options || {});
            initItemSearch(analysisCache.searchable_columns || []);
            initMlConfigurator();
        }
        setupChartDefaults();
        applyTabSwitch(AppStore.state.activeTab);
    }

    function setupChartDefaults() {
        if (window.Chart) {
            Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif";
            Chart.defaults.font.size = 11;
            Chart.defaults.font.weight = '600';
            Chart.defaults.color = '#64748B';
            Chart.defaults.plugins.tooltip.backgroundColor = '#0F172A';
            Chart.defaults.plugins.tooltip.padding = 12;
            Chart.defaults.plugins.tooltip.cornerRadius = 8;
            Chart.defaults.responsive = true;
            Chart.defaults.maintainAspectRatio = false;
        }
    }

    // === Navigation Logic ===
    function buildTabs(themes) {
        navTabs.innerHTML = '';

        // Append "Strategic AI Modeler" to guarantee it is always present
        const allTabs = [...themes];
        if (!allTabs.includes("Strategic AI Modeler")) {
            allTabs.push("Strategic AI Modeler");
        }

        allTabs.forEach(theme => {
            const btn = document.createElement('button');
            btn.className = `tab-link ${AppStore.state.activeTab === theme ? 'active' : ''}`;
            btn.textContent = theme;
            btn.onclick = () => applyTabSwitch(theme);
            navTabs.appendChild(btn);
        });
    }

    function applyTabSwitch(theme) {
        AppStore.setState({ activeTab: theme });

        const dashboardCanvas = document.getElementById('dashboardCanvas');
        const actionPlannerCanvas = document.getElementById('actionPlannerCanvas');
        const diagnosticsCanvas = document.getElementById('diagnosticsCanvas');
        const mlPredictiveCanvas = document.getElementById('mlPredictiveCanvas');
        const activeTabText = document.getElementById('activeTabText');
        const headerDesc = document.querySelector('.header-left p');

        // Reset UI Highlights
        document.querySelectorAll('.tab-link').forEach(btn => {
            btn.classList.toggle('active', btn.textContent === theme);
        });

        if (activeTabText) activeTabText.textContent = theme;

        // Hide all screens initially
        if (dashboardCanvas) dashboardCanvas.classList.add('hidden');
        if (actionPlannerCanvas) actionPlannerCanvas.classList.add('hidden');
        if (diagnosticsCanvas) diagnosticsCanvas.classList.add('hidden');
        if (mlPredictiveCanvas) mlPredictiveCanvas.classList.add('hidden');

        if (theme === 'Category Diagnostics Scorecard') {
            if (diagnosticsCanvas) diagnosticsCanvas.classList.remove('hidden');
            if (headerDesc) headerDesc.textContent = "Segment performance scorecard, margin contribution share, and health audits";
            if (analysisCache) renderDiagnosticsScorecard(analysisCache.category_scorecard);
        } else if (theme === 'Strategic Action Planner') {
            if (actionPlannerCanvas) actionPlannerCanvas.classList.remove('hidden');
            if (headerDesc) headerDesc.textContent = "Dollar-quantified business optimizations and real-time execution checklists";
            if (analysisCache) renderActionPlanner(analysisCache.action_plans);
        } else if (theme === 'Strategic AI Modeler') {
            if (mlPredictiveCanvas) mlPredictiveCanvas.classList.remove('hidden');
            if (headerDesc) headerDesc.textContent = "Train dynamic RandomForest predictive models and run interactive simulations";
            initMlConfigurator();
        } else {
            if (dashboardCanvas) dashboardCanvas.classList.remove('hidden');
            if (headerDesc) headerDesc.textContent = "Key metrics, AI-powered insights, and anomaly detection";
            if (analysisCache) renderDashboard('executive');
        }
    }

    // === File Upload Logic ===
    if (startAnalysisBtn) {
        startAnalysisBtn.onclick = () => fileInput.click();
    }

    if (dropZone) {
        dropZone.onclick = () => fileInput.click();
        dropZone.ondragover = (e) => { e.preventDefault(); dropZone.classList.add('dragover'); };
        dropZone.ondragleave = () => dropZone.classList.remove('dragover');
        dropZone.ondrop = (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                handleUpload();
            }
        };
    }

    fileInput.onchange = () => fileInput.files.length && handleUpload();

    async function handleUpload() {
        const files = fileInput.files;
        if (!files || files.length === 0) return;

        landingSection.classList.add('hidden');
        quantumLoader.classList.remove('hidden');

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        try {
            // Loading Sequence Animation
            const stages = [
                "Demandalytics Analyzing...",
                "Mapping Semantic Features...",
                "Synthesizing Executive Themes...",
                "Optimizing Chart Layouts..."
            ];
            let stageIndex = 0;
            const stageInterval = setInterval(() => {
                if (stageIndex < stages.length) {
                    loaderText.textContent = stages[stageIndex++];
                }
            }, 800);

            const resp = await fetch('/api/analyze', { method: 'POST', body: formData });

            clearInterval(stageInterval);
            const data = await resp.json();
            if (data.error) throw new Error(data.error);

            analysisCache = data;
            originalAnalysisCache = JSON.parse(JSON.stringify(data)); // Keep unfiltered copy
            sessionStorage.setItem('demandalytics_data', JSON.stringify(data));
            AppStore.setState({ isDataLoaded: true });

            // Transition UI
            landingSection.classList.add('hidden');
            workspaceView.classList.remove('hidden');

            const btn = document.getElementById('floatingChatBtn');
            if (btn) btn.classList.remove('hidden-chat');

            renderDashboard();
            populateFilters(data.filter_options || {});
            initItemSearch(data.searchable_columns || []);
            initMlConfigurator();
        } catch (err) {
            alert(`Analysis Error: ${err.message}`);
            landingSection.classList.remove('hidden');
            workspaceView.classList.add('hidden');
        } finally {
            quantumLoader.classList.add('hidden');
        }
    }

    // === Dashboard Rendering ===
    function renderDashboard(view = 'executive') {
        if (!analysisCache) return;
        const mode = document.getElementById('reportMode').value;

        // Update workspace-wrapper class for mode-specific styling
        workspaceView.classList.remove('mode-visual', 'mode-analytical');
        workspaceView.classList.add(`mode-${mode}`);

        buildTabs(analysisCache.themes || ["Executive Intelligence Briefing", "Strategic Action Planner", "Category Diagnostics Scorecard"]);

        const kpiRow = document.getElementById('kpiRow');
        const chartGrid = document.getElementById('chartGrid');
        const strategicText = document.getElementById('aiStrategicText');
        const lastUpdatedText = document.getElementById('lastUpdatedText');

        if (lastUpdatedText) {
            const now = new Date();
            lastUpdatedText.textContent = `Data Updated: ${now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} • ${now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
        }

        if (strategicText && analysisCache.insights) {
            strategicText.innerHTML = `<ul>${analysisCache.insights.map(i => `<li>${i}</li>`).join('')}</ul>`;
        }

        // Render simplified KPI cards as requested (No manual trends)
        kpiRow.innerHTML = '';
        analysisCache.kpis.forEach(kpi => {
            const card = document.createElement('div');
            card.className = 'kpi-card';

            // Dynamic B2B icon mapping
            let iconHtml = '<i class="fa-solid fa-chart-simple"></i>';
            const labelLower = (kpi.label || '').toLowerCase();
            if (labelLower.includes('price') || labelLower.includes('revenue') || labelLower.includes('sales') || labelLower.includes('profit') || labelLower.includes('cost') || labelLower.includes('spend') || labelLower.includes('amount') || labelLower.includes('total') || labelLower.includes('value') || (kpi.value && kpi.value.startsWith('$'))) {
                iconHtml = '<i class="fa-solid fa-coins"></i>';
            } else if (labelLower.includes('rate') || labelLower.includes('pct') || labelLower.includes('percent') || labelLower.includes('margin') || labelLower.includes('growth') || labelLower.includes('efficiency') || (kpi.value && kpi.value.endsWith('%'))) {
                iconHtml = '<i class="fa-solid fa-chart-line"></i>';
            } else if (labelLower.includes('quantity') || labelLower.includes('count') || labelLower.includes('volume') || labelLower.includes('inventory') || labelLower.includes('products') || labelLower.includes('items') || labelLower.includes('sku')) {
                iconHtml = '<i class="fa-solid fa-cubes"></i>';
            }

            const insightText = kpi.insight ? kpi.insight : 'Aggregated system metric for active cohort.';

            card.innerHTML = `
                <div class="kpi-top-row">
                    <h3>${kpi.label}</h3>
                    <div class="kpi-icon-pill">${iconHtml}</div>
                </div>
                <div class="value">${kpi.value}</div>
                <p class="kpi-insight-text">${insightText}</p>
            `;
            kpiRow.appendChild(card);
        });

        // Render Anomalies
        const anomalyPanel = document.getElementById('anomalyPanel');
        const anomalyList = document.getElementById('anomalyList');
        if (anomalyPanel && anomalyList) {
            if (analysisCache.anomalies && analysisCache.anomalies.length > 0 && view === 'executive') {
                anomalyPanel.classList.remove('hidden');
                anomalyList.innerHTML = analysisCache.anomalies.map(a => `
                    <div class="anomaly-item" title="${a.reason || 'Flagged as statistical outlier'}">
                        <div class="anomaly-item-icon">
                            <i class="fa-solid fa-circle-exclamation"></i>
                        </div>
                        <div class="anomaly-item-body">
                            <div class="anomaly-item-top">
                                <span class="anomaly-item-title">${a.type} Detected</span>
                                <span class="anomaly-item-value">${smartFormat(a.value)}</span>
                            </div>
                            <div class="anomaly-item-label">${a.metric} • <strong>${a.label}</strong></div>
                            <div class="anomaly-item-reason">${a.reason || 'Statistical variance deviation from average distribution.'}</div>
                        </div>
                    </div>
                `).join('');
            } else {
                anomalyPanel.classList.add('hidden');
            }
        }

        // Render Charts Filtered by View
        chartGrid.innerHTML = '';

        // Show filter bar if options exist
        const filterBar = document.getElementById('filterBar');
        const hasDropdowns = analysisCache.filter_options && Object.keys(analysisCache.filter_options).length > 0;
        const hasSearchable = analysisCache.searchable_columns && analysisCache.searchable_columns.length > 0;

        if (filterBar && (hasDropdowns || hasSearchable)) {
            filterBar.classList.remove('hidden');
        }

        let chartsToRender = analysisCache.charts;
        if (view === 'pulse') {
            // Pulse mode focuses on radar, pie, and line charts (trends)
            chartsToRender = analysisCache.charts.filter(c => ['radar', 'pie', 'line', 'doughnut'].includes(c.type));
            // Ensure at least some charts show up if fallback
            if (chartsToRender.length === 0) chartsToRender = analysisCache.charts.slice(0, 4);
        }

        chartsToRender.forEach((cData, idx) => {
            const card = document.createElement('div');
            card.className = 'bento-card';
            card.id = `card-wrapper-${idx}`;
            const canvasId = `chart-${idx}`;

            card.innerHTML = `
                <div class="card-header">
                    <div class="title-group">
                        <h3>${cData.title}</h3>
                        ${cData.desc ? `<p class="chart-interpretation">${cData.desc}</p>` : ''}
                    </div>
                    <div class="card-actions">
                        <button class="action-btn" title="Export CSV Data" onclick="exportCSV(${idx})">
                            <i class="fa-solid fa-file-csv"></i>
                        </button>
                        <button class="action-btn" title="Toggle Big Screen" onclick="toggleFullscreen('${card.id}', '${canvasId}', ${idx})">
                            <i class="fa-solid fa-expand"></i>
                        </button>
                        <input type="checkbox" class="chart-selector" data-index="${idx}" ${AppStore.state.selectedCharts.includes(idx) ? 'checked' : ''}>
                    </div>
                </div>
                <div class="chart-container-inner" id="container-${canvasId}">
                    <canvas id="${canvasId}"></canvas>
                </div>
            `;
            chartGrid.appendChild(card);

            // If in Analytical Mode, show the AI Insight container
            if (mode === 'analytical') {
                const aiContainer = document.createElement('div');
                aiContainer.className = 'ai-insight-container';
                aiContainer.id = `ai-insight-${idx}`;

                // Read description directly from the mega-prompt payload
                let chartDesc = cData.strategic_description;
                if (!chartDesc) {
                    chartDesc = AppStore.chartDescriptions[cData.title] || "Strategic analysis not available for this chart.";
                } else {
                    AppStore.chartDescriptions[cData.title] = chartDesc;
                }

                aiContainer.innerHTML = `
                    <div class="ai-insight-title">
                        <i class="fa-solid fa-wand-magic-sparkles"></i> DEMANDALYTICS STRATEGIC PULSE
                    </div>
                    <div class="ai-content">
                        ${parseBullets(chartDesc)}
                    </div>
                `;
                card.appendChild(aiContainer);
            }

            initChart(canvasId, cData, idx);
        });

        // Select All listener
        const selectAllCb = document.getElementById('selectAllCharts');
        if (selectAllCb) {
            selectAllCb.onchange = () => {
                const selected = selectAllCb.checked ? chartsToRender.map((_, i) => i) : [];
                AppStore.setState({ selectedCharts: selected });
                document.querySelectorAll('.chart-selector').forEach(cb => cb.checked = selectAllCb.checked);
                syncSelectedCount();
            };
            selectAllCb.checked = AppStore.state.selectedCharts.length === chartsToRender.length;
        }

        // Checkbox listeners
        document.querySelectorAll('.chart-selector').forEach(cb => {
            cb.onchange = () => {
                const idx = parseInt(cb.getAttribute('data-index'));
                let selected = [...AppStore.state.selectedCharts];
                if (cb.checked) {
                    if (!selected.includes(idx)) selected.push(idx);
                } else {
                    selected = selected.filter(i => i !== idx);
                }
                AppStore.setState({ selectedCharts: selected });
                if (selectAllCb) selectAllCb.checked = selected.length === chartsToRender.length;
                syncSelectedCount();
            };
        });

        if (AppStore.state.selectedCharts.length === 0) {
            AppStore.setState({ selectedCharts: chartsToRender.map((_, i) => i) });
        }
        syncSelectedCount();
    }

    function renderActionPlanner(plans) {
        const grid = document.getElementById('actionPlannerGrid');
        if (!grid) return;
        grid.innerHTML = '';
        if (!plans || plans.length === 0) {
            grid.innerHTML = `<div class="loading-desc">Please ingest a dataset to construct strategic action plans.</div>`;
            return;
        }
        plans.forEach((plan, idx) => {
            const card = document.createElement('div');
            card.className = 'action-card';

            const stepsHtml = plan.steps.map((step, sIdx) => `
                <label class="action-checklist-item">
                    <input type="checkbox" id="check-${idx}-${sIdx}" onchange="this.parentElement.classList.toggle('checked', this.checked)">
                    <span>${step}</span>
                </label>
            `).join('');

            card.innerHTML = `
                <div class="action-card-header">
                    <h4>${plan.title}</h4>
                    <span class="action-impact-badge">${plan.impact}</span>
                </div>
                <p class="action-desc">${plan.description}</p>
                <div class="action-steps-list">
                    ${stepsHtml}
                </div>
            `;
            grid.appendChild(card);
        });
    }

    function renderDiagnosticsScorecard(scorecard) {
        const table = document.getElementById('diagnosticsScorecardTable');
        if (!table) return;
        table.innerHTML = '';
        if (!scorecard || scorecard.length === 0) {
            table.innerHTML = `<tbody><tr><td class="loading-desc">Please ingest a dataset to populate the Category Performance scorecard.</td></tr></tbody>`;
            return;
        }
        let html = `<thead><tr>
            <th>SEGMENT BRAND / CATEGORY</th>
            <th>TOTAL SALES VOLUME</th>
            <th>CONTRIBUTION SHARE %</th>
            <th>PERFORMANCE STATUS</th>
            <th>STRATEGIC DIAGNOSTIC REVIEW</th>
        </tr></thead><tbody>`;

        scorecard.forEach(row => {
            let badgeClass = 'perf-core';
            if (row.status === 'High-Volume Engine') badgeClass = 'perf-high-volume';
            else if (row.status === 'Margin Anchor') badgeClass = 'perf-margin-anchor';
            else if (row.status === 'Efficiency Alert') badgeClass = 'perf-alert';

            const formattedSales = typeof row.sales === 'number' ? '$' + row.sales.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : row.sales;

            html += `<tr>
                <td class="segment-name"><strong>${row.category.toUpperCase()}</strong></td>
                <td class="segment-sales">${formattedSales}</td>
                <td class="segment-share">
                    <div class="share-progress-wrapper">
                        <span class="share-label">${row.share}%</span>
                        <div class="share-bar-container"><div class="share-bar-fill" style="width: ${row.share}%"></div></div>
                    </div>
                </td>
                <td><span class="badge-status ${badgeClass}">${row.status}</span></td>
                <td class="segment-review">${row.review}</td>
            </tr>`;
        });
        html += '</tbody>';
        table.innerHTML = html;
    }

    function renderDataGrid(data) {
        if (!data || data.length === 0) return;
        const table = document.getElementById('rawDataTable');
        const metadata = document.getElementById('datasetMetadata');

        // Metadata summary
        metadata.innerHTML = `<span class="status-badge"><i class="fa-solid fa-database"></i> ${data.length} RECORDS FOUND</span>`;

        // Table Construction (Limit to first 100 for high performance)
        const cols = Object.keys(data[0]);
        let html = `<thead><tr>${cols.map(c => `<th>${c.replace(/_/g, ' ').toUpperCase()}</th>`).join('')}</tr></thead>`;

        html += '<tbody>';
        data.slice(0, 100).forEach(row => {
            html += `<tr>${cols.map(c => `<td>${row[c]}</td>`).join('')}</tr>`;
        });
        html += '</tbody>';

        table.innerHTML = html;
    }

    window.smartFormat = function smartFormat(val) {
        if (typeof val === 'string' && (val.includes('%') || !val.match(/^\d+$/))) return val;
        let num = parseFloat(String(val).replace(/,/g, ''));
        if (isNaN(num)) return val;
        if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B';
        if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
        return num.toLocaleString();
    }

    function initChart(id, cData, index) {
        const canvas = document.getElementById(id);
        const container = document.getElementById(`container-${id}`);
        const ctx = canvas.getContext('2d');

        // --- ADAPTIVE SCALING (Zoom-In Logic) ---
        // If data points are > 30, we expand the canvas width to allow side scrolling
        const pointCount = cData.labels ? cData.labels.length : 0;
        if (pointCount > 30) {
            const minWidthPerPoint = 35;
            canvas.style.width = (pointCount * minWidthPerPoint) + 'px';
            canvas.style.height = '100%';
        } else {
            canvas.style.width = '100%';
            canvas.style.height = '100%';
        }
        const baseColor = AppStore.state.primaryColor;

        // Advanced Visual Configs
        const isArea = cData.style === 'area' || cData.style === 'stacked';
        const isSpline = cData.style === 'spline';
        const isStacked = cData.style === 'stacked';
        const isHorizontal = cData.style === 'horizontal' || cData.type === 'horizontalBar';

        const typeMapping = {
            'horizontal': 'bar',
            'horizontalBar': 'bar',
            'spline': 'line',
            'area': 'line',
            'box': 'boxplot'
        };

        const chartType = typeMapping[cData.type] || cData.type;

        // --- PALETTES ---
        const palettes = {
            blue: [
                { border: '#1e40af', bg: 'rgba(30, 64, 175, 0.85)' },
                { border: '#2563eb', bg: 'rgba(37, 99, 235, 0.7)' },
                { border: '#3b82f6', bg: 'rgba(59, 130, 246, 0.55)' },
                { border: '#60a5fa', bg: 'rgba(96, 165, 250, 0.4)' },
                { border: '#93c5fd', bg: 'rgba(147, 197, 253, 0.25)' },
                { border: '#dbeafe', bg: 'rgba(219, 234, 254, 0.15)' }
            ],
            multicolor: [
                { border: '#d97706', bg: 'rgba(250, 204, 21, 0.85)' },  // Vibrant Gold Yellow
                { border: '#ea580c', bg: 'rgba(249, 115, 22, 0.85)' },  // Vibrant Orange
                { border: '#991b1b', bg: 'rgba(220, 38, 38, 0.85)' },  // Rich Brick Red
                { border: '#6b21a8', bg: 'rgba(147, 51, 234, 0.85)' },  // Vibrant Purple
                { border: '#0f172a', bg: 'rgba(30, 58, 138, 0.85)' },   // Deep Navy Blue
                { border: '#1d4ed8', bg: 'rgba(59, 130, 246, 0.85)' },   // Royal Blue
                { border: '#0f766e', bg: 'rgba(13, 148, 136, 0.85)' },   // Sea Teal/Turquoise
                { border: '#166534', bg: 'rgba(34, 197, 94, 0.85)' }    // Bright Leaf Green
            ],
            emerald: [
                { border: '#064e3b', bg: 'rgba(6, 78, 59, 0.85)' },   // Solid Deep Green
                { border: '#059669', bg: 'rgba(5, 150, 105, 0.7)' },  // Medium Green
                { border: '#10b981', bg: 'rgba(16, 185, 129, 0.55)' }, // Bright Green
                { border: '#34d399', bg: 'rgba(52, 211, 153, 0.4)' },  // Light Green
                { border: '#6ee7b7', bg: 'rgba(110, 231, 183, 0.25)' } // Soft Green
            ],
            sunset: [
                { border: '#9a3412', bg: 'rgba(154, 52, 18, 0.85)' },   // Rust Orange
                { border: '#ea580c', bg: 'rgba(234, 88, 12, 0.85)' },   // Sunset Orange
                { border: '#f97316', bg: 'rgba(249, 115, 22, 0.7)' },   // Orange
                { border: '#f59e0b', bg: 'rgba(245, 158, 11, 0.55)' },  // Amber
                { border: '#fef08a', bg: 'rgba(254, 240, 138, 0.4)' }   // Warm Yellow
            ],
            amethyst: [
                { border: '#4c1d95', bg: 'rgba(76, 29, 149, 0.85)' },   // Deep Violet
                { border: '#6d28d9', bg: 'rgba(109, 40, 217, 0.7)' },   // Amethyst Purple
                { border: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.55)' },  // Medium Purple
                { border: '#a78bfa', bg: 'rgba(167, 139, 250, 0.4)' },   // Light Purple
                { border: '#c084fc', bg: 'rgba(192, 132, 252, 0.25)' }  // Lavender
            ],
            ruby: [
                { border: '#881337', bg: 'rgba(136, 19, 55, 0.85)' },   // Deep Cherry/Burgundy
                { border: '#be123c', bg: 'rgba(190, 18, 60, 0.7)' },    // Ruby Red
                { border: '#e11d48', bg: 'rgba(225, 29, 72, 0.55)' },   // Vibrant Red
                { border: '#fb7185', bg: 'rgba(251, 113, 133, 0.4)' },   // Soft Rose
                { border: '#fda4af', bg: 'rgba(253, 164, 175, 0.25)' }  // Pink
            ],
            ocean: [
                { border: '#115e59', bg: 'rgba(17, 94, 89, 0.85)' },    // Deep Teal
                { border: '#0f766e', bg: 'rgba(15, 118, 110, 0.7)' },   // Ocean Teal
                { border: '#0d9488', bg: 'rgba(13, 148, 136, 0.55)' },  // Mint Teal
                { border: '#14b8a6', bg: 'rgba(20, 184, 166, 0.4)' },   // Light Teal
                { border: '#2dd4bf', bg: 'rgba(45, 212, 191, 0.25)' }   // Soft Cyan
            ]
        };

        const activePalette = palettes[AppStore.state.colorTheme] || palettes['blue'];

        const config = {
            type: chartType,
            data: {
                labels: cData.labels,
                datasets: (cData.datasets || [{ label: cData.title, data: cData.data }]).map((ds, dIdx) => {
                    const isMulticolor = ['pie', 'doughnut', 'polarArea'].includes(chartType);
                    const isBar = chartType === 'bar';
                    const dsType = ds.type || chartType;
                    const isLine = dsType === 'line';

                    let datasetBg, datasetBorder;

                    if (isMulticolor) {
                        datasetBg = cData.labels.map((_, i) => activePalette[i % activePalette.length].bg);
                        datasetBorder = cData.labels.map((_, i) => activePalette[i % activePalette.length].border);
                    } else if (isBar && !isArea) {
                        if (cData.datasets && cData.datasets.length > 1) {
                            const theme = activePalette[dIdx % activePalette.length];
                            datasetBg = theme.bg;
                            datasetBorder = theme.border;
                        } else {
                            // If it's a multi-color-capable theme, color each bar differently!
                            if (['multicolor', 'sunset', 'ocean'].includes(AppStore.state.colorTheme)) {
                                datasetBg = cData.labels.map((_, i) => activePalette[i % activePalette.length].bg);
                                datasetBorder = cData.labels.map((_, i) => activePalette[i % activePalette.length].border);
                            } else {
                                const theme = activePalette[0];
                                const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                                gradient.addColorStop(0, theme.bg);
                                gradient.addColorStop(1, 'rgba(255, 255, 255, 0.05)'); // subtle fade
                                datasetBg = gradient;
                                datasetBorder = theme.border;
                            }
                        }
                    } else {
                        const theme = activePalette[dIdx % activePalette.length];
                        if (isArea) {
                            const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                            gradient.addColorStop(0, theme.bg.replace(/[\d\.]+\)$/g, '0.4)'));
                            gradient.addColorStop(1, 'rgba(255, 255, 255, 0.0)');
                            datasetBg = gradient;
                        } else {
                            datasetBg = theme.bg.replace(/[\d\.]+\)$/g, '0.04)');
                        }
                        datasetBorder = theme.border;
                    }

                    let extraConfig = {};
                    if (chartType === 'matrix') {
                        const maxV = Math.max(...ds.data.map(d => d.v));
                        const minV = Math.min(...ds.data.map(d => d.v));
                        datasetBg = (ctx2) => {
                            if (!ctx2.dataset || ctx2.dataIndex === undefined) return 'rgba(30,64,175,0.1)';
                            const v = ctx2.dataset.data[ctx2.dataIndex].v;
                            const alpha = (v - minV) / (maxV - minV || 1);
                            return `rgba(30, 64, 175, ${0.1 + alpha * 0.8})`;
                        };
                        datasetBorder = '#ffffff';
                        extraConfig = {
                            width: ({ chart }) => (chart.chartArea || {}).width / 10 - 1,
                            height: ({ chart }) => (chart.chartArea || {}).height / 10 - 1
                        };
                    }

                    // Special positive green / negative red coloring for Growth Rate charts!
                    if (cData.title.includes("Growth") && ds.data) {
                        datasetBg = ds.data.map(v => v >= 0 ? 'rgba(16, 185, 129, 0.85)' : 'rgba(244, 63, 94, 0.85)');
                        datasetBorder = ds.data.map(v => v >= 0 ? '#10b981' : '#f43f5e');
                    }


                    if (chartType === 'treemap') {
                        extraConfig = {
                            tree: cData.labels.map((lbl, i) => ({ value: ds.data[i], name: lbl })),
                            key: 'value',
                            groups: ['name'],
                            borderWidth: 1,
                            spacing: 1
                        };
                    } else if (chartType === 'boxplot') {
                        extraConfig = {
                            borderWidth: 2,
                            itemRadius: 2
                        };
                    }

                    return {
                        ...ds,
                        backgroundColor: datasetBg,
                        borderColor: datasetBorder,
                        borderWidth: isLine ? 2.5 : 2,
                        fill: isArea,
                        tension: isSpline || isLine ? 0.35 : 0,
                        pointRadius: chartType === 'radar' || isLine ? 3 : (chartType === 'scatter' ? 4 : 0),
                        pointHoverRadius: 6,
                        ...extraConfig
                    };
                })
            },
            options: {
                animation: {
                    duration: 1200,
                    easing: 'easeOutQuart',
                },
                indexAxis: isHorizontal ? 'y' : 'x',
                maintainAspectRatio: false,
                responsive: true,
                plugins: {
                    legend: { display: (['pie', 'doughnut', 'polarArea'].includes(chartType) || (cData.datasets && cData.datasets.length > 1)) },
                    tooltip: {
                        mode: ['line', 'radar', 'scatter'].includes(chartType) ? 'index' : 'nearest',
                        intersect: ['line', 'radar', 'scatter'].includes(chartType) ? false : true
                    }
                },
                scales: ['pie', 'doughnut', 'radar', 'treemap'].includes(chartType) ? {} : {
                    ...(chartType === 'matrix' ? {
                        x: { type: 'category', grid: { display: false } },
                        y: { type: 'category', grid: { display: false } }
                    } : {
                        y: {
                            beginAtZero: true,
                            stacked: isStacked,
                            grid: { color: 'rgba(241, 245, 249, 1)', drawBorder: false }
                        },
                        x: {
                            stacked: isStacked,
                            grid: { display: false }
                        },
                        ...(cData.style === 'dual_axis' ? {
                            y1: {
                                type: 'linear',
                                display: true,
                                position: 'right',
                                grid: { drawOnChartArea: false }
                            }
                        } : {})
                    })
                }
            }
        };

        if (AppStore.chartInstances[id]) AppStore.chartInstances[id].destroy();
        AppStore.chartInstances[id] = new Chart(ctx, config);
    }

    window.exportCSV = function (idx) {
        if (!analysisCache || !analysisCache.charts || !analysisCache.charts[idx]) return;
        const cData = analysisCache.charts[idx];
        let csvContent = "data:text/csv;charset=utf-8,";

        // Add headers
        csvContent += "Label,Value\n";

        // Add rows
        const labels = cData.labels || [];
        const datasets = cData.datasets || [{ data: cData.data || [] }];

        labels.forEach((label, i) => {
            const values = datasets.map(ds => ds.data ? ds.data[i] : '').join(',');
            // Escape labels containing commas
            const safeLabel = typeof label === 'string' && label.includes(',') ? `"${label}"` : label;
            csvContent += `${safeLabel},${values}\n`;
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `${cData.title || 'chart_data'}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    // Helper: Parse AI bullet text into styled HTML list
    function parseBullets(text) {
        if (!text || text === 'loading') return '';
        // Split on bullet character OR newlines
        let lines = text.split(/\n|(?=• )/).filter(l => l.trim().length > 2);
        if (lines.length <= 1) {
            // Try splitting on numbered patterns like "1." or "- "
            lines = text.split(/(?=\d+\.\s)|(?=[-•]\s)/).filter(l => l.trim().length > 2);
        }
        if (lines.length <= 1 && text.length > 10) lines = [text]; // Use as single paragraph
        return `<ul class="ai-bullet-list">${lines.map(l => `<li class="ai-bullet-item">${l.replace(/^[•\-\*\d+\.]\s*/, '').trim()}</li>`).join('')}</ul>`;
    }

    async function fetchChartDescription(cData, chartIdx) {
        // Deprecated: Chart descriptions are now generated universally via Mega-Prompt in ai_manager
        console.warn("fetchChartDescription is deprecated. Descriptions are bundled in payload.");
    }

    // === Export Logic (Backend Powered) ===
    async function exportDocument(type) {
        const selectedIndices = AppStore.state.selectedCharts;
        if (selectedIndices.length === 0) {
            alert("Please select at least one visual for the strategy report.");
            return;
        }

        downloadOverlay.classList.remove('hidden');
        overlayTitle.textContent = "Capturing Executive Visuals...";

        try {
            const chartsToExport = [];
            const bentoCards = document.querySelectorAll('.bento-card');
            const mode = document.getElementById('reportMode').value;

            const totalToCapture = selectedIndices.length;
            let currentCapture = 0;

            for (const idx of selectedIndices) {
                currentCapture++;
                overlayTitle.textContent = `Capturing Executive Visuals (${currentCapture} of ${totalToCapture})...`;

                const card = bentoCards[idx];
                const cData = analysisCache.charts[idx];

                // Grab the Chart.js canvas directly — crisp, full quality, no UI clutter
                const chartCanvas = card.querySelector('canvas');
                let imageDataUrl = '';

                if (chartCanvas && AppStore.chartInstances[`chart-${idx}`]) {
                    // Render at 3× resolution for sharp PPTX output
                    const exportCanvas = document.createElement('canvas');
                    const SCALE = 3;
                    exportCanvas.width = chartCanvas.width * SCALE;
                    exportCanvas.height = chartCanvas.height * SCALE;
                    const exportCtx = exportCanvas.getContext('2d');
                    exportCtx.fillStyle = '#ffffff';
                    exportCtx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
                    exportCtx.drawImage(chartCanvas, 0, 0, exportCanvas.width, exportCanvas.height);
                    imageDataUrl = exportCanvas.toDataURL('image/png');
                } else {
                    // Fallback: capture whole card via html2canvas
                    const aiInsight = card.querySelector('.ai-insight-container');
                    const cardActions = card.querySelector('.card-actions');
                    if (aiInsight) aiInsight.style.display = 'none';
                    if (cardActions) cardActions.style.display = 'none';
                    const snapCanvas = await html2canvas(card, { scale: 2, useCORS: true, backgroundColor: '#ffffff' });
                    if (aiInsight) aiInsight.style.display = '';
                    if (cardActions) cardActions.style.display = '';
                    imageDataUrl = snapCanvas.toDataURL('image/png');
                }

                chartsToExport.push({
                    title: cData.title,
                    image: imageDataUrl
                });
            }

            // Descriptions are now fully loaded via Mega-Prompt on dashboard render
            let descriptions = { ...AppStore.chartDescriptions };

            const endpoint = type === 'pptx' ? '/api/export_pptx' : '/api/export_pdf';
            overlayTitle.textContent = `Architecting Final ${type.toUpperCase()} Structure...`;
            const respDoc = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    mode: mode,
                    title: "Executive Strategic Report",
                    charts: chartsToExport,
                    insights: analysisCache.insights,
                    descriptions: descriptions,
                    theme: AppStore.state.colorTheme
                })
            });

            if (!respDoc.ok) throw new Error(`Backend ${type.toUpperCase()} generation failed.`);

            const blob = await respDoc.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Demandalytics_Strategic_Report_${mode}.${type}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

        } catch (err) {
            console.error("Export Error:", err);
            alert(`Strategic ${type.toUpperCase()} Export Failed. Please check backend connection.`);
        } finally {
            downloadOverlay.classList.add('hidden');
        }
    }

    exportReportBtn.onclick = () => exportDocument('pdf');
    const exportPptxBtn = document.getElementById('exportPptxBtn');
    if (exportPptxBtn) {
        exportPptxBtn.onclick = () => exportDocument('pptx');
    }

    // --- Premium Pill Toggle (Gliding Version) ---
    const glider = document.querySelector('.mode-glider');
    const updateGlider = (activeBtn) => {
        if (!glider || !activeBtn) return;
        glider.style.width = activeBtn.offsetWidth + 'px';
        glider.style.left = activeBtn.offsetLeft + 'px';
    };

    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.onclick = (e) => {
            const activeBtn = e.currentTarget;
            const mode = activeBtn.getAttribute('data-mode');
            document.getElementById('reportMode').value = mode;

            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            activeBtn.classList.add('active');
            updateGlider(activeBtn);

            // Re-render dashboard to apply mode changes
            if (AppStore.state.isDataLoaded) {
                renderDashboard(AppStore.state.activeTab === 'Analytical Pulse' ? 'pulse' : 'executive');
            }
        };
    });
    // Initial glider position
    setTimeout(() => updateGlider(document.querySelector('.mode-btn.active')), 500);

    function syncSelectedCount() {
        const count = AppStore.state.selectedCharts.length;
        const btn = document.getElementById('exportReportBtn');
        const countSpan = document.getElementById('selectedCount');

        if (countSpan) countSpan.textContent = count > 0 ? `(${count})` : '';

        if (btn) {
            if (count === 0) {
                btn.classList.add('btn-disabled');
                btn.style.opacity = '0.5';
                btn.style.pointerEvents = 'none';
                btn.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> SELECT CHARTS`;
            } else {
                btn.classList.remove('btn-disabled');
                btn.style.opacity = '1';
                btn.style.pointerEvents = 'auto';
                btn.innerHTML = `<i class="fa-solid fa-file-export"></i> EXPORT REPORT <span id="selectedCount">(${count})</span>`;
            }
        }
    }

    window.resetWorkspace = function () {
        // Clear session and state
        sessionStorage.removeItem('demandalytics_data');
        analysisCache = null;
        originalAnalysisCache = null;
        AppStore.setState({ isDataLoaded: false, selectedCharts: [] });
        AppStore.chartDescriptions = {};
        trainedModelCache = null;

        // UI Navigation
        workspaceView.classList.add('hidden');
        landingSection.classList.remove('hidden');

        // Reset file input
        if (fileInput) fileInput.value = '';

        // Reset ML Panel
        const targetSelect = document.getElementById('mlTargetSelect');
        if (targetSelect) targetSelect.innerHTML = '<option value="">Select Target...</option>';
        const featuresContainer = document.getElementById('mlFeaturesContainer');
        if (featuresContainer) featuresContainer.innerHTML = '<p class="loading-desc">Please upload a dataset first...</p>';
        const emptyState = document.getElementById('mlEmptyState');
        if (emptyState) emptyState.classList.remove('hidden');
        const activeWorkspace = document.getElementById('mlActiveWorkspace');
        if (activeWorkspace) activeWorkspace.classList.add('hidden');

        // Destroy ML Chart instances
        if (AppStore.mlDriversChartInstance) {
            AppStore.mlDriversChartInstance.destroy();
            AppStore.mlDriversChartInstance = null;
        }
        if (AppStore.mlFitChartInstance) {
            AppStore.mlFitChartInstance.destroy();
            AppStore.mlFitChartInstance = null;
        }

        // Smooth scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    window.toggleFullscreen = function (cardId, chartId, index) {
        const card = document.getElementById(cardId);
        const icon = card.querySelector('.fa-expand, .fa-compress');
        const isOpening = !card.classList.contains('fullscreen-card');

        if (isOpening) {
            card.classList.add('fullscreen-card');
            icon.classList.replace('fa-expand', 'fa-compress');
            document.body.style.overflow = 'hidden'; // Prevent background scroll
        } else {
            card.classList.remove('fullscreen-card');
            icon.classList.replace('fa-compress', 'fa-expand');
            document.body.style.overflow = 'auto';
        }

        // Trigger chart resize
        if (AppStore.chartInstances[chartId]) {
            setTimeout(() => {
                AppStore.chartInstances[chartId].resize();
            }, 300);
        }
    };

    // === DRILL-DOWN SEARCH & FILTER SYSTEM ===
    let activeSearchCol = null; // Track which column the search bar is currently mapped to
    let searchDebounceTimer = null;

    function initItemSearch(searchCols) {
        const wrapper = document.getElementById('itemSearchContainer');
        const input = document.getElementById('itemSearchInput');
        const pop = document.getElementById('searchSuggestPop');

        if (!wrapper || !input || !pop) return;

        if (!searchCols || searchCols.length === 0) {
            wrapper.classList.add('hidden');
            activeSearchCol = null;
            return;
        }

        // Setup to target top recognized item column
        activeSearchCol = searchCols[0].name;
        wrapper.classList.remove('hidden');
        input.placeholder = `Search ${activeSearchCol.replace(/_/g, ' ')}...`;

        // Basic reset
        input.value = '';
        pop.innerHTML = '';
        pop.classList.add('hidden');

        // Key listeners for dynamic suggestion
        input.oninput = (e) => {
            const val = e.target.value.trim();
            clearTimeout(searchDebounceTimer);

            if (val.length < 1) {
                pop.classList.add('hidden');
                return;
            }

            searchDebounceTimer = setTimeout(() => fetchSuggestions(val), 350);
        };

        // Hide popup when click outside
        document.addEventListener('click', (e) => {
            if (!wrapper.contains(e.target)) pop.classList.add('hidden');
        });
    }

    async function fetchSuggestions(query) {
        const pop = document.getElementById('searchSuggestPop');
        const filename = analysisCache?.metadata?.filename || originalAnalysisCache?.metadata?.filename;

        if (!pop || !filename || !activeSearchCol) return;

        try {
            const resp = await fetch('/api/suggest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename, column: activeSearchCol, query })
            });
            const items = await resp.json();

            pop.innerHTML = '';
            if (items.length === 0) {
                pop.innerHTML = '<div class="no-results">No exact matches</div>';
            } else {
                items.forEach(item => {
                    const div = document.createElement('div');
                    div.textContent = item;
                    div.onclick = () => {
                        document.getElementById('itemSearchInput').value = item;
                        pop.classList.add('hidden');
                        // Explicitly set trigger search filter flow
                        applyDrillDownFilter(activeSearchCol, item);
                    };
                    pop.appendChild(div);
                });
            }
            pop.classList.remove('hidden');
        } catch (e) {
            console.error("Search suggest issue:", e);
        }
    }

    function populateFilters(filterOptions) {
        const container = document.getElementById('filterDropdowns');
        const filterBar = document.getElementById('filterBar');
        const hasSearchable = analysisCache?.searchable_columns?.length > 0;
        const hasDropdowns = filterOptions && Object.keys(filterOptions).length > 0;

        // Permanently keep the Filter Bar visible as a corporate header
        if (filterBar) filterBar.classList.remove('hidden');

        // Populate dynamic Focus Metric Dropdown
        const metricSelect = document.getElementById('metricFocusSelect');
        if (metricSelect && analysisCache && analysisCache.metadata && analysisCache.metadata.metric_cols) {
            const currentSelected = AppStore.state.activeFocusMetric || analysisCache.metadata.metric_cols[0];
            if (!AppStore.state.activeFocusMetric) {
                AppStore.setState({ activeFocusMetric: currentSelected });
            }
            metricSelect.innerHTML = analysisCache.metadata.metric_cols.map(m =>
                `<option value="${m}" ${m === currentSelected ? 'selected' : ''}>${m.replace(/_/g, ' ').toUpperCase()}</option>`
            ).join('');
        }

        if (!container) return;
        container.innerHTML = '';

        if (!hasDropdowns) return;

        for (const [col, values] of Object.entries(filterOptions)) {
            const group = document.createElement('div');
            group.className = 'filter-select-group';
            const cleanLabel = col.replace(/_/g, ' ');
            group.innerHTML = `
                <label>${cleanLabel}</label>
                <select data-column="${col}" onchange="applyDrillDownFilter()">
                    <option value="">All ${cleanLabel}</option>
                    ${values.map(v => `<option value="${v}">${v}</option>`).join('')}
                </select>
            `;
            container.appendChild(group);
        }
    }

    window.applyDrillDownFilter = async function (manualCol, manualVal) {
        const selects = document.querySelectorAll('#filterDropdowns select');
        const filters = {};
        let hasActiveFilter = false;

        // 1. Extract standard Dropdowns
        selects.forEach(sel => {
            if (sel.value) {
                filters[sel.getAttribute('data-column')] = sel.value;
                sel.classList.add('active-filter');
                hasActiveFilter = true;
            } else {
                sel.classList.remove('active-filter');
            }
        });

        // 2. Extract & Merge the Item Search (Manual Override from search pop)
        const input = document.getElementById('itemSearchInput');
        if (manualCol && manualVal) {
            filters[manualCol] = manualVal;
            hasActiveFilter = true;
        } else if (activeSearchCol && input && input.value.trim()) {
            // If triggering standard filter update but text already typed manually
            filters[activeSearchCol] = input.value.trim();
            hasActiveFilter = true;
        }

        // 3. Extract the dynamic focus metric focus parameter
        const metricSelect = document.getElementById('metricFocusSelect');
        const focus_metric = metricSelect ? metricSelect.value : (AppStore.state.activeFocusMetric || '');
        if (focus_metric) {
            AppStore.setState({ activeFocusMetric: focus_metric });
        }

        const isPivotActive = focus_metric && (focus_metric !== (originalAnalysisCache?.metadata?.metric_cols?.[0] || ''));

        const clearBtn = document.getElementById('clearFiltersBtn');
        const badge = document.getElementById('activeFilterBadge');

        if (!hasActiveFilter && !isPivotActive) {
            // Reset to original unfiltered data
            if (originalAnalysisCache) {
                analysisCache = JSON.parse(JSON.stringify(originalAnalysisCache));
                AppStore.chartDescriptions = {};
                renderDashboard();
            }
            if (clearBtn) clearBtn.classList.add('hidden');
            if (badge) badge.classList.add('hidden');
            return;
        }

        // Show clear button and badge
        if (clearBtn) clearBtn.classList.remove('hidden');
        const filterText = Object.entries(filters).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`).join(' • ');

        if (badge) {
            if (hasActiveFilter) {
                badge.classList.remove('hidden');
                badge.innerHTML = `<i class="fa-solid fa-bullseye"></i> ${filterText}`;
            } else {
                badge.classList.add('hidden');
            }
        }

        // Show loader
        const quantumLoader = document.getElementById('quantumLoader');
        const loaderText = document.getElementById('loaderText');
        if (quantumLoader) quantumLoader.classList.remove('hidden');
        if (loaderText) loaderText.textContent = isPivotActive && !hasActiveFilter ? `Pivoting dashboard to: ${focus_metric.replace(/_/g, ' ').toUpperCase()}...` : `Drilling into: ${filterText}...`;

        try {
            const filename = analysisCache.metadata?.filename || originalAnalysisCache?.metadata?.filename;
            const resp = await fetch('/api/analyze_filtered', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename, filters, focus_metric })
            });

            const data = await resp.json();
            if (data.error) throw new Error(data.error);

            analysisCache = data;
            AppStore.chartDescriptions = {}; // Clear old AI descriptions
            AppStore.setState({ selectedCharts: [] });
            renderDashboard();
        } catch (err) {
            alert(`Filter Error: ${err.message}`);
        } finally {
            if (quantumLoader) quantumLoader.classList.add('hidden');
        }
    };

    window.clearAllFilters = function () {
        // Reset all dropdowns
        document.querySelectorAll('#filterDropdowns select').forEach(sel => {
            sel.value = '';
            sel.classList.remove('active-filter');
        });

        // Reset Item Search
        const input = document.getElementById('itemSearchInput');
        if (input) input.value = '';

        const clearBtn = document.getElementById('clearFiltersBtn');
        const badge = document.getElementById('activeFilterBadge');
        if (clearBtn) clearBtn.classList.add('hidden');
        if (badge) badge.classList.add('hidden');

        // Restore original unfiltered data BUT pivot around focus_metric if active!
        if (originalAnalysisCache) {
            const focus_metric = AppStore.state.activeFocusMetric || '';
            const default_metric = originalAnalysisCache?.metadata?.metric_cols?.[0] || '';

            if (focus_metric && focus_metric !== default_metric) {
                // Re-trigger analysis with empty filters but keeping the custom focus metric pivot
                applyDrillDownFilter();
            } else {
                analysisCache = JSON.parse(JSON.stringify(originalAnalysisCache));
                AppStore.chartDescriptions = {};
                renderDashboard();
            }
        }
    };

    // === CHATBOT LOGIC ===
    window.toggleChat = function () {
        const widget = document.getElementById('chatWidget');
        const btn = document.getElementById('floatingChatBtn');
        if (widget && btn) {
            widget.classList.toggle('hidden-chat');
            // Hide floating button if widget is open
            if (widget.classList.contains('hidden-chat')) {
                btn.classList.remove('hidden-chat');
            } else {
                btn.classList.add('hidden-chat');
            }
        }
    };

    window.sendMessage = async function () {
        const input = document.getElementById('chatInput');
        const messages = document.getElementById('chatMessages');
        const text = input.value.trim();
        if (!text) return;

        // User message
        messages.innerHTML += `<div class="message user-message">${text}</div>`;
        input.value = '';
        messages.scrollTop = messages.scrollHeight;

        // Typing indicator
        const typingId = 'typing-' + Date.now();
        messages.innerHTML += `<div class="message ai-message" id="${typingId}"><i class="fa-solid fa-spinner fa-spin"></i> Analyzing data...</div>`;
        messages.scrollTop = messages.scrollHeight;

        try {
            // Provide a data summary and sample data context
            const summary = analysisCache ? `Dataset has ${analysisCache.metadata.rows} rows. Columns: ${Object.keys(analysisCache.raw_data[0] || {}).join(', ')}.` : "No dataset loaded.";
            const sampleData = analysisCache ? analysisCache.raw_data.slice(0, 5) : [];

            const resp = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, data_summary: summary, sample_data: sampleData })
            });
            const data = await resp.json();

            document.getElementById(typingId).remove();

            if (data.type === 'chart' && data.chart_config) {
                // Dynamically inject chart
                if (!analysisCache.charts) analysisCache.charts = [];
                const newIdx = analysisCache.charts.length;
                analysisCache.charts.push(data.chart_config);

                const card = document.createElement('div');
                card.className = 'bento-card';
                card.id = `card-wrapper-${newIdx}`;
                const canvasId = `chart-${newIdx}`;

                card.innerHTML = `
                    <div class="card-header">
                        <div class="title-group">
                            <h3>${data.chart_config.title}</h3>
                        </div>
                        <div class="card-actions">
                            <button class="action-btn" title="Export CSV Data" onclick="exportCSV(${newIdx})">
                                <i class="fa-solid fa-file-csv"></i>
                            </button>
                            <button class="action-btn" title="Toggle Big Screen" onclick="toggleFullscreen('${card.id}', '${canvasId}', ${newIdx})">
                                <i class="fa-solid fa-expand"></i>
                            </button>
                            <input type="checkbox" class="chart-selector" data-index="${newIdx}" checked>
                        </div>
                    </div>
                    <div class="chart-container-inner" id="container-${canvasId}">
                        <canvas id="${canvasId}"></canvas>
                    </div>
                `;

                const grid = document.getElementById('chartGrid');
                if (grid) grid.insertBefore(card, grid.firstChild); // Insert at the top

                initChart(data.chart_config, newIdx);
                AppStore.state.selectedCharts.push(newIdx);

                // Also update the UI selected count if needed
                const selectAllCb = document.getElementById('selectAllCharts');
                if (selectAllCb) selectAllCb.checked = false;

                let replyText = data.message || "I have generated the chart and placed it at the top of your dashboard.";
                messages.innerHTML += `<div class="message ai-message">${replyText}</div>`;

            } else {
                // Format AI response
                let replyText = data.message || data.response || "Sorry, I encountered an error.";
                replyText = replyText.replace(/\n/g, '<br>');
                replyText = replyText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

                messages.innerHTML += `<div class="message ai-message">${replyText}</div>`;
            }
        } catch (e) {
            document.getElementById(typingId).remove();
            messages.innerHTML += `<div class="message ai-message" style="color:red;">Error connecting to AI backend.</div>`;
        }
        messages.scrollTop = messages.scrollHeight;
    };

    // === AUTOML PREDICTIVE ENGINE JS LOGIC ===
    let trainedModelCache = null;
    let mlPredictDebounceTimer = null;

    function initMlConfigurator() {
        const targetSelect = document.getElementById('mlTargetSelect');
        const featuresContainer = document.getElementById('mlFeaturesContainer');
        const trainBtn = document.getElementById('mlTrainBtn');

        if (!analysisCache || !analysisCache.raw_data || analysisCache.raw_data.length === 0) {
            targetSelect.innerHTML = '<option value="">No dataset loaded</option>';
            featuresContainer.innerHTML = '<p class="loading-desc">Please upload a dataset first...</p>';
            return;
        }

        // Keep existing user configurator selections if returning back to the tab
        if (targetSelect.options.length > 1) return;

        targetSelect.innerHTML = '<option value="">Select Target Variable (Y)...</option>';
        featuresContainer.innerHTML = '';

        const sampleRow = analysisCache.raw_data[0];
        const columns = Object.keys(sampleRow);

        // Dynamic scan of numeric columns for the Target selector
        const numericCols = [];
        columns.forEach(col => {
            const val = sampleRow[col];
            const isNum = !isNaN(parseFloat(val)) && isFinite(val);
            if (isNum && !col.toLowerCase().includes('id') && !col.toLowerCase().includes('zip') && !col.toLowerCase().includes('index') && !col.toLowerCase().includes('code')) {
                numericCols.push(col);
                const opt = document.createElement('option');
                opt.value = col;
                opt.textContent = col.replace(/_/g, ' ').toUpperCase();
                targetSelect.appendChild(opt);
            }
        });

        // Populate Feature checklists with intelligent auto-encoded badges
        columns.forEach((col) => {
            const item = document.createElement('label');
            item.className = 'ml-checklist-item';

            let badgeType = 'categorical';
            let badgeLabel = 'text';

            const isNumeric = numericCols.includes(col);
            const isDate = col.toLowerCase().includes('date') || col.toLowerCase().includes('time') || col.toLowerCase().includes('year') || col.toLowerCase().includes('month') || col.toLowerCase().includes('day');

            if (isDate) {
                badgeType = 'date';
                badgeLabel = 'date';
            } else if (isNumeric) {
                badgeType = 'numeric';
                badgeLabel = 'num';
            }

            // Exclude obvious target columns by default but display them in list
            const isDefaultChecked = col.toLowerCase() !== 'id' && !col.toLowerCase().includes('id') && !col.toLowerCase().includes('index');

            item.innerHTML = `
                <input type="checkbox" value="${col}" ${isDefaultChecked ? 'checked' : ''}>
                <span>${col.replace(/_/g, ' ')}</span>
                <span class="feat-badge ${badgeType}">${badgeLabel}</span>
            `;
            featuresContainer.appendChild(item);
        });

        // Bind AutoML Training button callback
        trainBtn.onclick = handleModelTraining;
    }

    async function handleModelTraining() {
        const targetSelect = document.getElementById('mlTargetSelect');
        const target = targetSelect.value;
        if (!target) {
            alert("Please select a target variable (Y) in the sidebar configurator.");
            return;
        }

        const features = [];
        document.querySelectorAll('#mlFeaturesContainer input[type="checkbox"]:checked').forEach(cb => {
            features.push(cb.value);
        });

        // Target cannot be its own feature
        const filteredFeatures = features.filter(f => f !== target);

        if (filteredFeatures.length === 0) {
            alert("Please select at least one predictor feature (X) distinct from the target.");
            return;
        }

        // Show Full-Screen loader
        const quantumLoader = document.getElementById('quantumLoader');
        const loaderText = document.getElementById('loaderText');
        if (quantumLoader) quantumLoader.classList.remove('hidden');
        if (loaderText) loaderText.textContent = "Training Enterprise ML Model...";

        try {
            const filename = analysisCache.metadata.filename;
            const filters = analysisCache.active_filters || {};

            const resp = await fetch('/api/train_model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename, target, features: filteredFeatures, filters })
            });

            const data = await resp.json();
            if (data.error) throw new Error(data.error);

            // Save trained model variables
            trainedModelCache = data;
            trainedModelCache.target_col = target;

            // Slide out empty panel, reveal workspace
            document.getElementById('mlEmptyState').classList.add('hidden');
            document.getElementById('mlActiveWorkspace').classList.remove('hidden');

            // 1. Accuracy Circular Dial Animation
            const r2Val = data.r2 || 0;
            document.getElementById('accuracyPercentVal').textContent = `${r2Val}%`;
            const fillCircle = document.getElementById('accuracyGaugeFill');
            if (fillCircle) {
                const radius = 40;
                const circumference = 2 * Math.PI * radius; // ~251.2
                const offset = circumference - (circumference * (r2Val / 100));
                fillCircle.style.strokeDashoffset = offset;
            }

            // 2. Load Evaluation Metrics
            document.getElementById('metricMaeValue').textContent = data.mae.toLocaleString();
            document.getElementById('metricRmseValue').textContent = data.rmse.toLocaleString();

            // Set dynamic header name for simulated output KPI card
            document.getElementById('predictedTargetLabel').textContent = `Predicted ${target.replace(/_/g, ' ').toUpperCase()}`;

            // 3. Render Driver importances and alignment plots
            renderDriversChart(data.importances);
            renderFitChart(data.alignment);

            // 4. Generate dynamic What-If sliders & selectors
            buildInteractiveSliders(data.features_info);

            // 5. Trigger initial predicted target value calculation
            triggerLiveMlPrediction();

        } catch (e) {
            alert(`AutoML Training Failed: ${e.message}`);
        } finally {
            if (quantumLoader) quantumLoader.classList.add('hidden');
        }
    }

    function renderDriversChart(importances) {
        const ctx = document.getElementById('mlDriversChart').getContext('2d');
        if (AppStore.mlDriversChartInstance) {
            AppStore.mlDriversChartInstance.destroy();
        }

        const labels = importances.map(x => x.name);
        const dataVals = importances.map(x => x.weight);

        AppStore.mlDriversChartInstance = new Chart(ctx, {
            type: 'bar',
            options: {
                indexAxis: 'y',
                maintainAspectRatio: false,
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (ctx) => ` Relative Impact: ${ctx.raw}%` } }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: 'rgba(241, 245, 249, 1)', drawBorder: false },
                        ticks: { callback: (val) => `${val}%` }
                    },
                    y: {
                        grid: { display: false }
                    }
                }
            },
            data: {
                labels: labels,
                datasets: [{
                    label: 'Relative Weight %',
                    data: dataVals,
                    backgroundColor: 'rgba(13, 148, 136, 0.85)',
                    borderColor: '#0d9488',
                    borderWidth: 1.5,
                    borderRadius: 6
                }]
            }
        });
    }

    function renderFitChart(alignment) {
        const ctx = document.getElementById('mlFitChart').getContext('2d');
        if (AppStore.mlFitChartInstance) {
            AppStore.mlFitChartInstance.destroy();
        }

        const labels = alignment.map(x => `Pt ${x.index}`);
        const actuals = alignment.map(x => x.actual);
        const predicteds = alignment.map(x => x.predicted);

        AppStore.mlFitChartInstance = new Chart(ctx, {
            type: 'line',
            options: {
                maintainAspectRatio: false,
                responsive: true,
                plugins: {
                    legend: { display: true, position: 'top' }
                },
                scales: {
                    y: {
                        grid: { color: 'rgba(241, 245, 249, 1)', drawBorder: false }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            },
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Actual Values',
                        data: actuals,
                        borderColor: '#94a3b8',
                        backgroundColor: 'rgba(148, 163, 184, 0.05)',
                        borderWidth: 1.8,
                        pointRadius: 2,
                        fill: false,
                        tension: 0.15
                    },
                    {
                        label: 'AI Predicted Fit',
                        data: predicteds,
                        borderColor: '#0d9488',
                        backgroundColor: 'rgba(13, 148, 136, 0.05)',
                        borderWidth: 2.2,
                        pointRadius: 2,
                        fill: false,
                        tension: 0.15
                    }
                ]
            }
        });
    }

    function buildInteractiveSliders(featuresInfo) {
        const grid = document.getElementById('mlSlidersGrid');
        grid.innerHTML = '';

        featuresInfo.forEach(info => {
            const card = document.createElement('div');
            card.className = 'sim-slider-card';
            const cleanName = info.name.replace(/_/g, ' ').toUpperCase();

            if (info.type === 'numeric') {
                const defaultVal = info.mean !== undefined ? info.mean : (info.max + info.min) / 2;
                const step = (info.max - info.min) / 100 || 1;

                card.innerHTML = `
                    <div class="sim-slider-row-header">
                        <label title="${info.name}">${cleanName}</label>
                        <span class="slider-val-bubble" id="val-bubble-${info.name}">${smartFormat(defaultVal)}</span>
                    </div>
                    <input type="range" 
                        class="sim-range-input ml-input-param" 
                        data-column="${info.name}" 
                        data-type="numeric"
                        min="${info.min}" 
                        max="${info.max}" 
                        step="${step}" 
                        value="${defaultVal}"
                        oninput="document.getElementById('val-bubble-${info.name}').textContent = smartFormat(this.value); triggerLiveMlPrediction();">
                    <div class="sim-range-boundaries">
                        <span>${smartFormat(info.min)}</span>
                        <span>${smartFormat(info.max)}</span>
                    </div>
                `;
            } else if (info.type === 'categorical') {
                card.innerHTML = `
                    <div class="sim-slider-row-header">
                        <label title="${info.name}">${cleanName}</label>
                    </div>
                    <select class="sim-cat-select ml-input-param" 
                        data-column="${info.name}" 
                        data-type="categorical"
                        onchange="triggerLiveMlPrediction();">
                        ${info.categories.map(cat => `<option value="${cat}" ${cat === info.default ? 'selected' : ''}>${cat}</option>`).join('')}
                    </select>
                `;
            } else if (info.type === 'date') {
                const monthStr = String(info.default_month).padStart(2, '0');
                const dayStr = String(info.default_day).padStart(2, '0');
                const dateStr = `${info.default_year}-${monthStr}-${dayStr}`;

                card.innerHTML = `
                    <div class="sim-slider-row-header">
                        <label title="${info.name}">${cleanName}</label>
                    </div>
                    <input type="date" 
                        class="sim-cat-select ml-input-param" 
                        data-column="${info.name}" 
                        data-type="date"
                        value="${dateStr}"
                        onchange="triggerLiveMlPrediction();">
                `;
            }

            grid.appendChild(card);
        });
    }

    window.triggerLiveMlPrediction = function () {
        clearTimeout(mlPredictDebounceTimer);
        mlPredictDebounceTimer = setTimeout(runLiveMlPrediction, 120);
    };

    async function runLiveMlPrediction() {
        if (!trainedModelCache || !trainedModelCache.model_path) return;

        const inputs = {};
        const paramElements = document.querySelectorAll('.ml-input-param');
        paramElements.forEach(el => {
            const col = el.getAttribute('data-column');
            inputs[col] = el.value;
        });

        const outputVal = document.getElementById('predictedTargetValue');
        const outputDelta = document.getElementById('predictedTargetDelta');

        outputVal.style.opacity = '0.5';

        try {
            const filename = analysisCache.metadata.filename;
            const resp = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: filename,
                    model_path: trainedModelCache.model_path,
                    inputs: inputs
                })
            });

            if (resp.ok) {
                const data = await resp.json();
                if (data.prediction !== undefined) {
                    const pred = data.prediction;
                    const isCurrency = ['revenue', 'sales', 'profit', 'cost', 'price', 'amount', 'spend'].some(k => trainedModelCache.target_col.toLowerCase().includes(k));
                    const prefix = isCurrency ? '$' : '';

                    outputVal.textContent = `${prefix}${pred.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

                    // Display delta relative to historical mean
                    const histMean = trainedModelCache.historical_mean_target;
                    if (histMean > 0) {
                        const delta = ((pred - histMean) / histMean) * 100;
                        const sign = delta >= 0 ? '+' : '';
                        const deltaClass = delta >= 0 ? 'delta-plus' : 'delta-minus';
                        outputDelta.className = `sim-out-delta ${deltaClass}`;
                        outputDelta.innerHTML = `<i class="fa-solid ${delta >= 0 ? 'fa-arrow-trend-up' : 'fa-arrow-trend-down'}"></i> ${sign}${delta.toFixed(1)}% vs dataset average`;
                    } else {
                        outputDelta.className = 'sim-out-delta delta-neutral';
                        outputDelta.textContent = '--';
                    }
                }
            }
        } catch (e) {
            console.error("Predict endpoint issue:", e);
        } finally {
            outputVal.style.opacity = '1';
        }
    }

    // === Modal Navigation Controls & Try Demo ===
    const loadDemoBtn = document.getElementById('loadDemoBtn');
    const howItWorksBtn = document.getElementById('howItWorksBtn');
    const contactSupportBtn = document.getElementById('contactSupportBtn');

    const howItWorksModal = document.getElementById('howItWorksModal');
    const contactSupportModal = document.getElementById('contactSupportModal');

    const closeHowItWorksBtn = document.getElementById('closeHowItWorksBtn');
    const closeContactBtn = document.getElementById('closeContactBtn');
    const successCloseBtn = document.getElementById('successCloseBtn');

    const contactForm = document.getElementById('contactForm');
    const feedbackSuccessState = document.getElementById('feedbackSuccessState');

    // How it Works Modal events
    if (howItWorksBtn && howItWorksModal) {
        howItWorksBtn.addEventListener('click', () => {
            howItWorksModal.classList.remove('hidden');
        });
    }

    if (closeHowItWorksBtn && howItWorksModal) {
        closeHowItWorksBtn.addEventListener('click', () => {
            howItWorksModal.classList.add('hidden');
        });
    }

    // Contact Support Modal events
    if (contactSupportBtn && contactSupportModal) {
        contactSupportBtn.addEventListener('click', () => {
            contactSupportModal.classList.remove('hidden');
            if (contactForm) contactForm.classList.remove('hidden');
            if (feedbackSuccessState) feedbackSuccessState.classList.add('hidden');
        });
    }

    if (closeContactBtn && contactSupportModal) {
        closeContactBtn.addEventListener('click', () => {
            contactSupportModal.classList.add('hidden');
        });
    }

    if (successCloseBtn && contactSupportModal) {
        successCloseBtn.addEventListener('click', () => {
            contactSupportModal.classList.add('hidden');
        });
    }

    // Close modals on clicking outside the card
    window.addEventListener('click', (e) => {
        if (e.target === howItWorksModal) {
            howItWorksModal.classList.add('hidden');
        }
        if (e.target === contactSupportModal) {
            contactSupportModal.classList.add('hidden');
        }
    });

    // Try Demo Button event
    if (loadDemoBtn) {
        loadDemoBtn.addEventListener('click', async () => {
            landingSection.classList.add('hidden');
            quantumLoader.classList.remove('hidden');
            loaderText.textContent = "Generating Demo Dataset...";

            try {
                // Interactive stages during demo creation
                const stages = [
                    "Synthesizing Retail Transactions...",
                    "Injecting Seasonal Outliers...",
                    "Running Anomaly Detection...",
                    "Preparing Dashboard Workspace..."
                ];
                let stageIndex = 0;
                const stageInterval = setInterval(() => {
                    if (stageIndex < stages.length) {
                        loaderText.textContent = stages[stageIndex++];
                    }
                }, 700);

                const resp = await fetch('/api/load_demo', { method: 'POST' });
                clearInterval(stageInterval);

                const data = await resp.json();
                if (data.error) throw new Error(data.error);

                analysisCache = data;
                originalAnalysisCache = JSON.parse(JSON.stringify(data)); // Keep unfiltered copy
                sessionStorage.setItem('demandalytics_data', JSON.stringify(data));
                AppStore.setState({ isDataLoaded: true });

                // Switch to workspace view
                landingSection.classList.add('hidden');
                workspaceView.classList.remove('hidden');

                const chatBtn = document.getElementById('floatingChatBtn');
                if (chatBtn) chatBtn.classList.remove('hidden-chat');

                renderDashboard();
                populateFilters(data.filter_options || {});
                initItemSearch(data.searchable_columns || []);
                initMlConfigurator();
            } catch (err) {
                alert(`Demo Ingestion Error: ${err.message}`);
                landingSection.classList.remove('hidden');
                workspaceView.classList.add('hidden');
            } finally {
                quantumLoader.classList.add('hidden');
            }
        });
    }

    // ==========================================
    // EMAILJS CONFIGURATION (OPTIONAL)
    // To receive real email notifications, sign up at https://www.emailjs.com/
    // and populate these fields with your credentials:
    // ==========================================
    const EMAILJS_CONFIG = {
        publicKey: "1a21zDHtG0cdHKUki",      // Insert EmailJS Public Key (e.g. "user_xxxxxxxxxxxx")
        serviceId: "service_ont28jh",      // Insert EmailJS Service ID (e.g. "service_xxxxxxx")
        templateId: "template_64acfyu"      // Insert EmailJS Template ID (e.g. "template_xxxxxxx")
    };

    // Contact Support form submission
    if (contactForm) {
        contactForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = contactForm.querySelector('button[type="submit"]');
            const originalBtnHtml = submitBtn.innerHTML;

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting...';

            const name = document.getElementById('feedbackName').value;
            const email = document.getElementById('feedbackEmail').value;
            const category = document.getElementById('feedbackCategory').value;
            const message = document.getElementById('feedbackMessage').value;

            try {
                // 1. Save locally to backend
                const resp = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: name,
                        email: email,
                        category: category,
                        message: message
                    })
                });

                const data = await resp.json();
                if (data.error) throw new Error(data.error);

                // 2. Dispatch via EmailJS (if configured)
                if (window.emailjs && EMAILJS_CONFIG.publicKey && EMAILJS_CONFIG.serviceId && EMAILJS_CONFIG.templateId) {
                    try {
                        emailjs.init({
                            publicKey: EMAILJS_CONFIG.publicKey,
                        });
                        await emailjs.send(EMAILJS_CONFIG.serviceId, EMAILJS_CONFIG.templateId, {
                            name: name,
                            email: email,
                            title: category,
                            message: message,
                            time: new Date().toLocaleString()
                        });
                        console.log("EmailJS dispatch completed successfully.");
                    } catch (emailErr) {
                        console.error("EmailJS sending failed:", emailErr);
                        // We do not fail the user flow if backend saving succeeded
                    }
                }

                // Show success state
                contactForm.classList.add('hidden');
                if (feedbackSuccessState) feedbackSuccessState.classList.remove('hidden');
                contactForm.reset();
            } catch (err) {
                alert(`Submission Error: ${err.message}`);
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHtml;
            }
        });
    }

    init();
});
