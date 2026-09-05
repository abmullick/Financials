import re

with open('retirals/src/static/index.html', 'r') as f:
    content = f.read()

# Function to replace calculateMetrics
new_calc_metrics = '''        async function calculateMetrics() {
            clearCalculationError();

            console.log("calculateMetrics invoked."); // Debugging: Confirm function call

            const payload = {
                current_age: parseInt(document.getElementById('current_age').value),
                retirement_age: parseInt(document.getElementById('retirement_age').value),
                life_expectancy: parseInt(document.getElementById('life_expectancy').value),
                current_annual_expenses: parseCurrency(document.getElementById('current_annual_expenses').value),
                avg_inflation_rate: parseFloat(document.getElementById('avg_inflation_rate').value) / 100.0,
                current_corpus: parseCurrency(document.getElementById('current_corpus').value),
                annual_contribution: parseCurrency(document.getElementById('annual_contribution').value),
                return_equity: parseFloat(document.getElementById('return_equity').value) / 100.0,
                return_debt: parseFloat(document.getElementById('return_debt').value) / 100.0,
                return_arbitrage: parseFloat(document.getElementById('return_arbitrage').value) / 100.0,
                return_reit: parseFloat(document.getElementById('return_reit').value) / 100.0,
                contribution_increase: parseFloat(document.getElementById('contribution_increase').value) / 100.0,
                ltcg_exemption: parseCurrency(document.getElementById('ltcg_exemption').value),
                one_time_lumpsum: parseCurrency(document.getElementById('one_time_lumpsum').value),
                // Pension
                include_pension: document.getElementById('include_pension').checked,
                pension_start_age: parseInt(document.getElementById('pension_start_age').value),
                annual_pension: parseCurrency(document.getElementById('annual_pension').value),
                pension_increase: parseFloat(document.getElementById('pension_increase').value) / 100.0,
                pension_tax_rate: parseFloat(document.getElementById('pension_tax_rate').value) / 100.0,
                reinvest_pension_surplus: document.getElementById('reinvest_pension_surplus').checked,

                stress_scenario: document.getElementById('stress_scenario').value,
                adhoc_expenses: getAdHocExpenses(),
                // Portfolio Allocation
                allocation_equity: parseFloat(document.getElementById('allocation_equity').value) / 100,
                allocation_debt: parseFloat(document.getElementById('allocation_debt').value) / 100,
                allocation_arbitrage: parseFloat(document.getElementById('allocation_arbitrage').value) / 100,
                allocation_reit: parseFloat(document.getElementById('allocation_reit').value) / 100,
                // Equity sub-allocation
                equity_ltcg_split: parseFloat(document.getElementById('equity_ltcg_split').value) / 100,
                equity_stcg_split: parseFloat(document.getElementById('equity_stcg_split').value) / 100,
                // Tax rates
                tax_ltcg: parseFloat(document.getElementById('tax_ltcg').value) / 100.0,
                tax_stcg: parseFloat(document.getElementById('tax_stcg').value) / 100.0,
                tax_debt: parseFloat(document.getElementById('tax_debt').value) / 100.0,
                tax_arbitrage: parseFloat(document.getElementById('tax_arbitrage').value) / 100.0,
                reit_gain_fraction: parseFloat(document.getElementById('reit_gain_fraction').value) / 100.0
            };

            if (![payload.current_age, payload.retirement_age, payload.life_expectancy].every(Number.isFinite)) {
                showCalculationError('Please enter valid numeric ages before running the simulation.');
                return;
            }

            if (payload.retirement_age <= payload.current_age) {
                showCalculationError('Retirement age must be greater than the current age.');
                return;
            }

            if (payload.life_expectancy < payload.retirement_age) {
                showCalculationError('Life expectancy must be greater than or equal to the retirement age.');
                return;
            }

            // Validate allocation sums to 100%
            const totalAlloc = payload.allocation_equity + payload.allocation_debt + payload.allocation_arbitrage + payload.allocation_reit;
            if (totalAlloc < 0.995 || totalAlloc > 1.005) {
                showCalculationError('Portfolio allocation must sum to 100%.');
                return;
            }

            try {
                const response = await fetch('/calculate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    let message = 'The calculation could not be completed.';
                    try {
                        const errorBody = await response.json();
                        if (Array.isArray(errorBody.detail)) {
                            message = errorBody.detail.map(err => `${err.loc[1]}: ${err.msg}`).join('; ');
                        } else {
                            message = errorBody.detail || message;
                        }
                    } catch (error) {
                        // Ignore JSON parsing failures and keep the default message.
                    }
                    throw new Error(message);
                }

                const data = await response.json();

                lastCalculationResult = { mode: 'deterministic', payload, data };
                deterministicResult = data;
                updateAiInsightButtonState();

                // --- Update KPIs with conditional coloring ---
                const finalCorpusEl = document.getElementById('kpi_final_corpus');
                finalCorpusEl.innerText = fmt(data.metrics.final_corpus);
                finalCorpusEl.classList.remove('text-success', 'text-danger');
                if (data.metrics.readiness_percent >= 100 || data.metrics.final_corpus >= 0) {
                    finalCorpusEl.classList.add('text-success');
                } else {
                    finalCorpusEl.classList.add('text-danger');
                }

                const readinessEl = document.getElementById('kpi_readiness_percent');
                readinessEl.innerText = `${data.metrics.readiness_percent.toFixed(2)}%`;
                readinessEl.classList.remove('text-success', 'text-warning', 'text-danger');
                if (data.metrics.readiness_percent >= 100) {
                    readinessEl.classList.add('text-success');
                } else if (data.metrics.readiness_percent >= 75) {
                    readinessEl.classList.add('text-warning');
                } else {
                    readinessEl.classList.add('text-danger');
                }

                const targetContributionEl = document.getElementById('kpi_target_annual_contribution');
                targetContributionEl.innerText = fmt(data.metrics.target_annual_contribution_for_gap);
                targetContributionEl.classList.remove('text-success', 'text-danger', 'text-warning');
                if (data.metrics.readiness_percent >= 100) {
                    targetContributionEl.classList.add('text-success');
                } else {
                    targetContributionEl.classList.add('text-danger');
                }

                const minCorpusEl = document.getElementById('kpi_minimum_corpus_required');
                minCorpusEl.innerText = fmt(data.metrics.minimum_corpus_required);
                minCorpusEl.classList.remove('text-success', 'text-warning');
                if (data.metrics.readiness_percent >= 100) {
                    minCorpusEl.classList.add('text-success');
                } else {
                    minCorpusEl.classList.add('text-warning');
                }
                // --- Update other KPIs ---
                document.getElementById('kpi_retirement_corpus').innerText = fmt(data.metrics.corpus_at_retirement);
                document.getElementById('kpi_peak_age').innerText = data.metrics.peak_age;
                document.getElementById('kpi_retirement_span').innerHTML = `${data.metrics.years_in_retirement} yrs <span style="font-size: 0.6em; color: var(--text-3); display: block; margin-top: 4px;">(${data.metrics.retirement_projection_points} data points)</span>`;
                document.getElementById('kpi_req_pre_ret_return').innerText = `${data.metrics.required_pre_retirement_return.toFixed(2)}%`;
                document.getElementById('kpi_req_post_ret_return').innerText = `${data.metrics.required_post_retirement_return.toFixed(2)}%`;

                // --- Update Pension KPIs ---
                const pensionKpiSection = document.getElementById('pensionKpiSection');
                if (payload.include_pension) {
                    pensionKpiSection.classList.remove('hidden');
                    document.getElementById('kpi_total_pension').innerText = fmt(data.metrics.total_pension_received);
                    document.getElementById('kpi_total_surplus_reinvested').innerText = fmt(data.metrics.total_surplus_reinvested);
                    document.getElementById('kpi_total_pension_tax').innerText = fmt(data.metrics.total_pension_tax);

                    const coverage = data.metrics.average_pension_coverage;
                    const coverageEl = document.getElementById('kpi_pension_coverage');
                    coverageEl.innerText = `${coverage.toFixed(1)}%`;
                    coverageEl.classList.remove('text-success', 'text-warning');
                    if (coverage >= 50) coverageEl.classList.add('text-success');
                    else if (coverage >= 25) coverageEl.classList.add('text-warning');
                }

                // --- Update charts ---
                updateCharts(data);
            } catch (error) {
                console.error('Calculation error:', error);
                showCalculationError(error.message || 'Unexpected error while calculating retirement metrics.');
            }
        }'''

# Replace the old calculateMetrics function.
start = content.find('        async function calculateMetrics()')
next_func = content.find('        async function calculateMonteCarlo()', start)
if start == -1 or next_func == -1:
    print('Could not find calculateMetrics boundaries')
    exit(1)
new_content = content[:start] + new_calc_metrics + content[next_func:]

# Now replace calculateMonteCarlo function in new_content.
start2 = new_content.find('        async function calculateMonteCarlo()')
next_func2 = new_content.find('        function renderMonteCarloResults(data)', start2)
if start2 == -1 or next_func2 == -1:
    print('Could not find calculateMonteCarlo boundaries')
    exit(1)
new_calc_monte = '''        async function calculateMonteCarlo() {
            clearCalculationError();

            const btn = document.getElementById('mcRunBtn');
            const overlay = document.getElementById('mcOverlay');
            btn.classList.add('mc-loading');
            btn.disabled = true;
            btn.querySelector('.mc-btn-text').textContent = '⏳ Calculating...';
            overlay.classList.add('active');

            const payload = {
                current_age: parseInt(document.getElementById('current_age').value),
                retirement_age: parseInt(document.getElementById('retirement_age').value),
                life_expectancy: parseInt(document.getElementById('life_expectancy').value),
                current_annual_expenses: parseCurrency(document.getElementById('current_annual_expenses').value),
                avg_inflation_rate: parseFloat(document.getElementById('avg_inflation_rate').value) / 100.0,
                current_corpus: parseCurrency(document.getElementById('current_corpus').value),
                annual_contribution: parseCurrency(document.getElementById('annual_contribution').value),
                contribution_increase: parseFloat(document.getElementById('contribution_increase').value) / 100.0,
                ltcg_exemption: parseCurrency(document.getElementById('ltcg_exemption').value),
                one_time_lumpsum: parseCurrency(document.getElementById('one_time_lumpsum').value),
                include_pension: document.getElementById('include_pension').checked,
                pension_start_age: parseInt(document.getElementById('pension_start_age').value),
                annual_pension: parseCurrency(document.getElementById('annual_pension').value),
                pension_increase: parseFloat(document.getElementById('pension_increase').value) / 100.0,
                pension_tax_rate: parseFloat(document.getElementById('pension_tax_rate').value) / 100.0,
                reinvest_pension_surplus: document.getElementById('reinvest_pension_surplus').checked,
                stress_scenario: document.getElementById('stress_scenario').value,
                adhoc_expenses: getAdHocExpenses(),
                allocation_equity: parseFloat(document.getElementById('allocation_equity').value) / 100,
                allocation_debt: parseFloat(document.getElementById('allocation_debt').value) / 100,
                allocation_arbitrage: parseFloat(document.getElementById('allocation_arbitrage').value) / 100,
                allocation_reit: parseFloat(document.getElementById("allocation_reit").value) / 100,
                equity_ltcg_split: parseFloat(document.getElementById('equity_ltcg_split').value) / 100,
                equity_stcg_split: parseFloat(document.getElementById('equity_stcg_split').value) / 100,
                tax_ltcg: parseFloat(document.getElementById('tax_ltcg').value) / 100,
                tax_stcg: parseFloat(document.getElementById('tax_stcg').value) / 100,
                tax_debt: parseFloat(document.getElementById('tax_debt').value) / 100,
                tax_arbitrage: parseFloat(document.getElementById('tax_arbitrage').value) / 100,
                reit_gain_fraction: parseFloat(document.getElementById('reit_gain_fraction').value) / 100.0,
                return_equity: parseFloat(document.getElementById('return_equity').value) / 100.0,
                return_debt: parseFloat(document.getElementById('return_debt').value) / 100.0,
                return_arbitrage: parseFloat(document.getElementById('return_arbitrage').value) / 100.0,
                return_reit: parseFloat(document.getElementById('return_reit').value) / 100.0,
                num_simulations: parseInt(document.getElementById('num_simulations').value),
                volatility_equity: parseFloat(document.getElementById('volatility_equity').value) / 100,
                volatility_debt: parseFloat(document.getElementById('volatility_debt').value) / 100,
                volatility_arbitrage: parseFloat(document.getElementById('volatility_arbitrage').value) / 100,
                equity_debt_correlation: parseFloat(document.getElementById('equity_debt_correlation').value),
                equity_arbitrage_correlation: parseFloat(document.getElementById('equity_arbitrage_correlation').value),
                debt_arbitrage_correlation: parseFloat(document.getElementById('debt_arbitrage_correlation').value),
                return_distribution: document.getElementById('return_distribution').value,
                monte_carlo_seed: document.getElementById('monte_carlo_seed').value ? parseInt(document.getElementById('monte_carlo_seed').value) : null,
                retirement_age_sensitivity: (() => {
                    const raw = document.getElementById('retirement_age_sensitivity').value.trim();
                    if (!raw) return null;
                    return raw.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n));
                })(),
            };

            if (isNaN(payload.current_age) || isNaN(payload.retirement_age) || isNaN(payload.life_expectancy)) {
                showCalculationError('Please enter valid numeric ages before running the simulation.');
                overlay.classList.remove('active');
                btn.classList.remove('mc-loading');
                btn.disabled = false;
                btn.querySelector('.mc-btn-text').textContent = '🎲 Run Monte Carlo Simulation';
                return;
            }

            if (payload.retirement_age <= payload.current_age) {
                showCalculationError('Retirement age must be greater than the current age.');
                overlay.classList.remove('active');
                btn.classList.remove('mc-loading');
                btn.disabled = false;
                btn.querySelector('.mc-btn-text').textContent = '🎲 Run Monte Carlo Simulation';
                return;
            }

            if (payload.life_expectancy < payload.retirement_age) {
                showCalculationError('Life expectancy must be greater than or equal to the retirement age.');
                overlay.classList.remove('active');
                btn.classList.remove('mc-loading');
                btn.disabled = false;
                btn.querySelector('.mc-btn-text').textContent = '🎲 Run Monte Carlo Simulation';
                return;
            }

            // Validate allocation sums to 100%
            const totalAlloc = payload.allocation_equity + payload.allocation_debt + payload.allocation_arbitrage + payload.allocation_reit;
            if (totalAlloc < 0.995 || totalAlloc > 1.005) {
                showCalculationError('Portfolio allocation must sum to 100%.');
                overlay.classList.remove('active');
                btn.classList.remove('mc-loading');
                btn.disabled = false;
                btn.querySelector('.mc-btn-text').textContent = '🎲 Run Monte Carlo Simulation';
                return;
            }

            try {
                const response = await fetch('/calculate-mc', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    let message = `The Monte Carlo calculation failed (HTTP ${response.status}).`;
                    try {
                        const errorBody = await response.json();
                        if (Array.isArray(errorBody.detail)) {
                            message = errorBody.detail.map(err => `${err.loc[1]}: ${err.msg}`).join('; ');
                        } else if (errorBody.detail) {
                            message = errorBody.detail;
                        }
                    } catch (jsonError) {
                        const text = await response.text();
                        console.error('MC error response (non-JSON):', text);
                        message = `The Monte Carlo calculation could not be completed. Server returned ${response.status}.`;
                    }
                    throw new Error(message);
                }

                const data = await response.json();

                lastCalculationResult = { mode: 'monte_carlo', payload, data };
                monteCarloResult = data;
                updateAiInsightButtonState();
                renderMonteCarloResults(data);
            } catch (error) {
                console.error('Monte Carlo calculation error:', error);
                showCalculationError(error.message || 'Unexpected error while running Monte Carlo simulation.');
            } finally {
                const btn = document.getElementById('mcRunBtn');
                btn.classList.remove('mc-loading');
                btn.disabled = false;
                btn.querySelector('.mc-btn-text').textContent = '🎲 Run Monte Carlo Simulation';
                document.getElementById('mcOverlay').classList.remove('active');
            }
        }'''

# Replace the function.
final_content = new_content[:start2] + new_calc_monte + new_content[next_func2:]

with open('retirals/src/static/index.html', 'w') as f:
    f.write(final_content)
print('Replaced calculateMetrics and calculateMonteCarlo')
