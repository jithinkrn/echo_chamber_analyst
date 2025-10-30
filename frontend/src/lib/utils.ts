import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 4,
  }).format(amount);
}

/**
 * Format date to local timezone in format: "Oct 30, 2025 3:45 PM"
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return 'Not set';

  try {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).format(new Date(date));
  } catch (error) {
    return 'Invalid date';
  }
}

/**
 * Format datetime for display on campaign cards
 * Returns "Oct 30, 2025 3:45 PM" or "Not set"
 */
export function formatCampaignDateTime(date: string | Date | null | undefined): string {
  return formatDate(date);
}

/**
 * Get frequency display text from schedule interval (in seconds)
 * Format: "Every X mins" or "Every X hours Y mins"
 */
export function formatScheduleFrequency(intervalSeconds: number | null | undefined): string {
  if (!intervalSeconds) return 'Not scheduled';

  const hours = Math.floor(intervalSeconds / 3600);
  const minutes = Math.floor((intervalSeconds % 3600) / 60);
  const seconds = intervalSeconds % 60;

  // If less than 1 hour
  if (hours === 0) {
    if (minutes === 0) {
      return `Every ${seconds} seconds`;
    }
    return `Every ${minutes} min${minutes !== 1 ? 's' : ''}`;
  }

  // If 1 hour or more
  if (minutes === 0) {
    return `Every ${hours} hour${hours !== 1 ? 's' : ''}`;
  }

  return `Every ${hours} hour${hours !== 1 ? 's' : ''} ${minutes} min${minutes !== 1 ? 's' : ''}`;
}

/**
 * Calculate next scheduled run time based on last run and interval
 * If nextRunAt is provided by backend, use that directly
 */
export function getNextScheduledRun(
  lastRunAt: string | Date | null | undefined,
  intervalSeconds: number | null | undefined,
  scheduleEnabled: boolean | any,
  nextRunAt?: string | Date | null | undefined
): string {
  // If backend provides next_run_at, use it directly
  if (nextRunAt) {
    return formatDate(nextRunAt);
  }

  // Check if schedule is enabled (handle both boolean and string values)
  const isScheduleEnabled = scheduleEnabled === true || scheduleEnabled === 'true' || scheduleEnabled === 1;

  // If schedule is not enabled or no interval, not scheduled
  if (!isScheduleEnabled || !intervalSeconds || intervalSeconds <= 0) {
    return 'Not scheduled';
  }

  try {
    // Calculate next run from last run + interval
    // If never run before, use current time as base
    const lastRun = lastRunAt ? new Date(lastRunAt) : new Date();
    const nextRun = new Date(lastRun.getTime() + intervalSeconds * 1000);
    return formatDate(nextRun);
  } catch (error) {
    return 'Not scheduled';
  }
}

export function getSentimentColor(score: number): string {
  if (score > 0.1) return 'text-green-600';
  if (score < -0.1) return 'text-red-600';
  return 'text-gray-600';
}

export function getSentimentLabel(score: number): string {
  if (score > 0.5) return 'Very Positive';
  if (score > 0.1) return 'Positive';
  if (score > -0.1) return 'Neutral';
  if (score > -0.5) return 'Negative';
  return 'Very Negative';
}