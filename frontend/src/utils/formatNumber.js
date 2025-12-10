/**
 * Format number with commas for thousands separator
 * @param {number|string} num - Number to format
 * @returns {string} Formatted number with commas
 */
export const formatNumber = (num) => {
  if (num === null || num === undefined || num === '') return '0';
  return Number(num).toLocaleString();
};

/**
 * Format percentage with one decimal place
 * @param {number} num - Number to format as percentage
 * @returns {string} Formatted percentage
 */
export const formatPercentage = (num) => {
  if (num === null || num === undefined || num === '') return '0.0%';
  return `${Number(num).toFixed(1)}%`;
};