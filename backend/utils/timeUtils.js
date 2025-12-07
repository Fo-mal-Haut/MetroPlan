/**
 * Time utility functions for the pathfinding algorithm
 */

/**
 * Parse HH:MM time string into minutes since midnight
 * @param {string} timeStr - Time string in HH:MM format
 * @returns {number} - Minutes since midnight
 */
function parseTime(timeStr) {
  if (!timeStr) return 0;
  if (timeStr === "00:00") return 1440; // Next day

  const [hours, minutes] = timeStr.split(':').map(Number);
  return hours * 60 + minutes;
}

/**
 * Convert minutes since midnight to HH:MM time string
 * @param {number} totalMinutes - Minutes since midnight
 * @returns {string} - Time string in HH:MM format
 */
function toTime(totalMinutes) {
  const minutes = totalMinutes % 1440;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
}

/**
 * Calculate time difference between two times
 * @param {number} startTime - Start time in minutes
 * @param {number} endTime - End time in minutes
 * @returns {number} - Time difference in minutes
 */
function timeDifference(startTime, endTime) {
  let diff = endTime - startTime;
  if (diff < 0) diff += 1440; // Handle next day
  return diff;
}

/**
 * Format duration from minutes to readable string
 * @param {number} minutes - Duration in minutes
 * @returns {string} - Formatted duration string
 */
function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}

module.exports = {
  parseTime,
  toTime,
  timeDifference,
  formatDuration
};