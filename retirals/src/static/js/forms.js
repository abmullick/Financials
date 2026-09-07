function buildAdHocRow(age = '', amount = '', category = 'Other', inflation = null) {
    const row = document.createElement('div');
    row.className = 'adhoc-row p-3 rounded-lg border';
    row.style.borderColor = 'var(--stroke)';
    row.style.background = 'var(--glass)';

    const defaultInflationRates = {
        'Healthcare': 8.0,
        'Education': 8.0,
        'Home / Renovation': 6.0,
        'Vehicle / Consumer Goods': 5.0,
        'Travel / Lifestyle': 6.0,
    };

    row.innerHTML = `
        <div class="grid grid-cols-[1fr_1fr_40px] gap-x-3 gap-y-1 items-start">
            <div class="flex flex-col">
                <label class="block text-xs font-medium text-slate-300 mb-0.5">Age</label>
                <input class="adhoc-age input-shell w-full rounded-lg p-2 text-sm" type="number" min="1" placeholder=" " value="${age}">
            </div>
            <div class="relative flex flex-col">
                <div class="flex items-center gap-1 mb-0.5">
                    <label class="block text-xs font-medium text-slate-300">Cost Today</label>
                    <div class="tooltip-container">
                        <span class="tooltip-icon">ⓘ</span>
                        <div class="tooltip-content">Cost as of today.</div>
                    </div>
                </div>
                <input class="adhoc-amount input-shell w-full rounded-lg p-2 text-sm" type="text" placeholder=" " value="${formatCurrency(amount)}">
            </div>
            <button type="button" class="remove-adhoc-btn row-span-2 self-start mt-4 inline-flex h-8 w-8 items-center justify-center rounded-full bg-rose-100 text-lg font-bold text-rose-700 hover:bg-rose-200">×</button>

            <div class="flex flex-col">
                <label class="block text-xs font-medium text-slate-300 mb-0.5">Category</label>
                <select class="adhoc-category input-shell w-full rounded-lg p-2 text-sm mt-0.5">
                    <option>Healthcare</option>
                    <option>Education</option>
                    <option>Home / Renovation</option>
                    <option>Vehicle / Consumer Goods</option>
                    <option>Travel / Lifestyle</option>
                    <option>Other</option>
                    <option>Custom</option>
                </select>
            </div>
            <div class="relative flex flex-col">
                <div class="flex items-center gap-1 mb-0.5">
                    <label class="block text-xs font-medium text-slate-300">Inflation %</label>
                    <div class="tooltip-container">
                        <span class="tooltip-icon">ⓘ</span>
                        <div class="tooltip-content">Annual inflation rate.</div>
                    </div>
                </div>
                <div class="relative mt-0.5">
                    <input class="adhoc-inflation input-shell w-full rounded-lg p-2 text-sm pr-7" type="number" step="0.1" placeholder=" ">
                    <span class="absolute inset-y-0 right-0 flex items-center pr-2 text-slate-400 text-xs">%</span>
                </div>
            </div>
        </div>
    `;

    const categorySelect = row.querySelector('.adhoc-category');
    const inflationInput = row.querySelector('.adhoc-inflation');
    
    categorySelect.value = category;
    if (inflation !== null) {
        inflationInput.value = inflation;
    } else if (category === 'Other') {
        inflationInput.value = document.getElementById('avg_inflation_rate').value;
    }

    categorySelect.addEventListener('change', () => {
        const selectedCategory = categorySelect.value;
        if (selectedCategory in defaultInflationRates) {
            inflationInput.value = defaultInflationRates[selectedCategory];
        } else if (selectedCategory === 'Other') {
            inflationInput.value = document.getElementById('avg_inflation_rate').value;
        } else { // Custom
            inflationInput.value = '';
            inflationInput.focus();
        }
    });

    row.querySelector('.remove-adhoc-btn').addEventListener('click', () => row.remove());
    setupCurrencyInputs(row); // Apply currency formatting to the new amount input
    return row;
}

function seedAdHocRows() {
    const container = document.getElementById('adhocExpenseRows');
    container.innerHTML = '';
}

function getAdHocExpenses() {
    return Array.from(document.querySelectorAll('.adhoc-row')).map(row => {
        const age = parseInt(row.querySelector('.adhoc-age').value || '0', 10);
        const amount = parseCurrency(row.querySelector('.adhoc-amount').value);
        const inflationVal = row.querySelector('.adhoc-inflation').value;
        const inflationRate = (inflationVal !== '' && !isNaN(parseFloat(inflationVal))) ? parseFloat(inflationVal) / 100.0 : null;

        const expense = { age, amount };
        if (inflationRate !== null) {
            expense.inflation_rate = inflationRate;
        }

        if ((!Number.isNaN(age) && age > 0) && (!Number.isNaN(amount) && amount >= 0)) {
            return expense;
        }
        return null;
    }).filter(Boolean);
}

function setupStepper() {
    const stepperContainer = document.getElementById('stepper');
    const steps = document.querySelectorAll('.form-step');
    const stepperItems = document.querySelectorAll('.stepper-item');
    const toggleBtn = document.getElementById('toggleStepsBtn');
    const stepNavButtons = document.querySelectorAll('.next-step-btn, .prev-step-btn');
    let currentStep = 1;
    let isExpanded = false;

    function showStep(stepNumber) {
        if (isExpanded) return;
        steps.forEach(step => {
            step.classList.toggle('hidden', parseInt(step.dataset.step) !== stepNumber);
        });
        stepperItems.forEach(item => {
            item.classList.toggle('active', parseInt(item.dataset.stepId) === stepNumber);
        });
        currentStep = stepNumber;
    }

    function toggleExpand() {
        isExpanded = !isExpanded;
        stepperContainer.classList.toggle('hidden', isExpanded);
        stepNavButtons.forEach(btn => btn.parentElement.classList.toggle('hidden', isExpanded));

        if (isExpanded) {
            steps.forEach(step => step.classList.remove('hidden'));
            stepperItems.forEach(item => item.classList.add('active'));
            toggleBtn.textContent = 'Collapse';
        } else {
            showStep(currentStep); // Restore to the current step view
            toggleBtn.textContent = 'Show All';
        }
    }

    document.querySelectorAll('.next-step-btn').forEach(btn => {
        btn.addEventListener('click', () => showStep(currentStep + 1));
    });
    document.querySelectorAll('.prev-step-btn').forEach(btn => {
        btn.addEventListener('click', () => showStep(currentStep - 1));
    });
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleExpand);
    }

    showStep(1);
}

function setupAllocationSliders() {
    const sliders = {
        equity: { slider: document.getElementById('equity_slider'), valueDisplay: document.getElementById('equity_slider_value'), hiddenInput: document.getElementById('allocation_equity') },
        debt: { slider: document.getElementById('debt_slider'), valueDisplay: document.getElementById('debt_slider_value'), hiddenInput: document.getElementById('allocation_debt') },
        arbitrage: { slider: document.getElementById('arbitrage_slider'), valueDisplay: document.getElementById('arbitrage_slider_value'), hiddenInput: document.getElementById('allocation_arbitrage') },
        reit: { slider: document.getElementById('reit_slider'), valueDisplay: document.getElementById('reit_slider_value'), hiddenInput: document.getElementById('allocation_reit') }
    };
    const sliderKeys = Object.keys(sliders);
    const totalDisplay = document.getElementById('allocationTotalDisplay');

    function updateTotal() {
        let total = 0;
        sliderKeys.forEach(key => {
            total += parseInt(sliders[key].hiddenInput.value, 10);
        });
        totalDisplay.textContent = total + '%';
        // Optionally add invalid indication class if total != 100
        if (total !== 100) {
            totalDisplay.classList.add('text-red-500');
        } else {
            totalDisplay.classList.remove('text-red-500');
        }
    }

    // Initialize total display
    updateTotal();

    sliderKeys.forEach(key => {
        const s = sliders[key];
        s.slider.addEventListener('input', () => {
            s.hiddenInput.value = s.slider.value;
            s.valueDisplay.textContent = s.slider.value + '%';
            updateTotal();
        });
    });
}function setupEquitySplitValidator() {
    const inputs = document.querySelectorAll('.equity-split-input');
    const totalDisplay = document.getElementById('equitySplitTotalDisplay');

    function validateEquitySplit() {
        const ltcg = parseFloat(document.getElementById('equity_ltcg_split').value) || 0;
        const stcg = parseFloat(document.getElementById('equity_stcg_split').value) || 0;
        const total = ltcg + stcg;

        totalDisplay.textContent = `${total.toFixed(0)}%`;

        totalDisplay.classList.remove('bg-emerald-100', 'text-emerald-800', 'bg-rose-100', 'text-rose-800');
        if (Math.abs(total - 100) < 0.01) {
            totalDisplay.classList.add('bg-emerald-100', 'text-emerald-800');
        } else {
            totalDisplay.classList.add('bg-rose-100', 'text-rose-800');
        }
    }

    inputs.forEach(input => input.addEventListener('input', validateEquitySplit));
    validateEquitySplit(); // Initial validation on load
}

// Handlers for currency input focus/blur
function handleCurrencyFocus(e) {
    e.target.value = parseCurrency(e.target.value);
}

function handleCurrencyBlur(e) {
    const numericValue = parseCurrency(e.target.value);
    e.target.value = formatCurrency(numericValue);
}

// Function to set up currency formatting for inputs
function setupCurrencyInputs(container = document) {
    const currencyInputs = container.querySelectorAll(
        '#current_annual_expenses, #current_corpus, #annual_contribution, ' +
        '#ltcg_exemption, #one_time_lumpsum, #annual_pension, ' +
        '.adhoc-amount' // Include ad-hoc amounts by class
    );

    currencyInputs.forEach(input => {
        // Remove existing listeners to prevent duplicates if called multiple times
        input.removeEventListener('focus', handleCurrencyFocus);
        input.removeEventListener('blur', handleCurrencyBlur);

        // Add new listeners
        input.addEventListener('focus', handleCurrencyFocus);
        input.addEventListener('blur', handleCurrencyBlur);

        // Apply initial formatting if the value is a raw number and not already formatted
        // This handles default values and dynamically added ad-hoc rows
        const currentValue = input.value;
        // Check if it's a number and not already formatted (doesn't start with '₹')
        if (currentValue && !currentValue.startsWith('₹') && !isNaN(parseFloat(currentValue))) {
            input.value = formatCurrency(parseCurrency(currentValue));
        }
    });
}
