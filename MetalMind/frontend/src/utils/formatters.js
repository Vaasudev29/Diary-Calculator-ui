/**
 * Format currency in Indian Rupees
 * Examples: ₹5.25 Cr, ₹85.4 Lakh, ₹45,000
 */
export function formatIndianCurrency(value) {
  if (value == null || isNaN(value)) return '₹0';

  const absValue = Math.abs(value);

  // Crores (10 million)
  if (absValue >= 10000000) {
    return `₹${(value / 10000000).toFixed(2)} Cr`;
  }

  // Lakhs (100 thousand)
  if (absValue >= 100000) {
    return `₹${(value / 100000).toFixed(1)} Lakh`;
  }

  // Thousands
  if (absValue >= 1000) {
    return `₹${(value / 1000).toFixed(1)}K`;
  }

  return `₹${value.toFixed(0)}`;
}

/**
 * Format percentage with one decimal place
 */
export function formatPercent(value) {
  if (value == null || isNaN(value)) return '0.0%';
  return `${value.toFixed(1)}%`;
}

/**
 * Format large numbers with commas
 */
export function formatNumber(value) {
  if (value == null || isNaN(value)) return '0';
  return value.toLocaleString('en-IN', { maximumFractionDigits: 1 });
}
