import { format, formatDistanceToNow, parseISO } from 'date-fns';
import { fromZonedTime, toZonedTime, formatInTimeZone } from 'date-fns-tz';

// EST timezone identifier
const EST_TIMEZONE = 'America/New_York';

/**
 * Convert UTC date to EST timezone
 * @param {Date|string} utcDate - UTC date object or ISO string
 * @returns {Date} - Date object in EST timezone
 */
export const convertToEST = (utcDate) => {
  if (!utcDate) return null;
  
  // Parse ISO string if needed
  const date = typeof utcDate === 'string' ? parseISO(utcDate) : utcDate;
  
  // Convert UTC to EST
  return toZonedTime(date, EST_TIMEZONE);
};

/**
 * Format date in EST timezone
 * @param {Date|string} utcDate - UTC date object or ISO string
 * @param {string} formatString - Format string for date-fns format function
 * @returns {string} - Formatted date string in EST
 */
export const formatInEST = (utcDate, formatString = 'MMM dd, yyyy HH:mm:ss zzz') => {
  if (!utcDate) return '';
  
  // Parse ISO string if needed
  const date = typeof utcDate === 'string' ? parseISO(utcDate) : utcDate;
  
  // Use date-fns-tz formatInTimeZone function
  return formatInTimeZone(date, EST_TIMEZONE, formatString);
};

/**
 * Format distance to now in EST timezone
 * @param {Date|string} utcDate - UTC date object or ISO string
 * @returns {string} - Formatted distance string (e.g., "2 minutes ago")
 */
export const formatDistanceToNowEST = (utcDate) => {
  if (!utcDate) return '';
  
  const estDate = convertToEST(utcDate);
  return formatDistanceToNow(estDate, { addSuffix: true });
};

/**
 * Get current time in EST
 * @returns {Date} - Current date in EST timezone
 */
export const getCurrentEST = () => {
  return toZonedTime(new Date(), EST_TIMEZONE);
};

/**
 * Convert EST date to UTC for API calls
 * @param {Date} estDate - Date in EST timezone
 * @returns {Date} - Date in UTC timezone
 */
export const convertESTToUTC = (estDate) => {
  if (!estDate) return null;
  return fromZonedTime(estDate, EST_TIMEZONE);
};