function cleanPct(val) {
    return parseFloat(val) / 100.0;
}

function formatCurrency(value) {
    const num = Number(value);
    if (isNaN(num)) return '';
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(num);
}

function parseCurrency(value) {
    if (typeof value !== 'string') return parseFloat(value);
    // Remove currency symbol and commas
    return parseFloat(value.replace(/₹/g, '').replace(/,/g, '')) || 0;
}

function fmt(num) {
    // Use the new formatCurrency function for consistency
    return formatCurrency(num);
}

function fitKpiValue(element) {
    const card = element.closest('.kpi-3d');
    if (!card) return;

    const maxWidth = card.clientWidth - 20;
    const maxHeight = card.clientHeight - 42;
    let size = 28;

    element.style.fontSize = size + 'px';
    element.style.lineHeight = '1.1';

    while (size > 10) {
        if (element.scrollWidth <= maxWidth && element.scrollHeight <= maxHeight) {
            break;
        }
        size -= 1;
        element.style.fontSize = size + 'px';
    }
}

function fitAllKpiValues() {
    document.querySelectorAll('.kpi-value').forEach(fitKpiValue);
}
