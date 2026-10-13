// ── Budget status calculation ───────────────────────────────────────────────
// Uses integer math to avoid float drift per TRD §3.9

export type BudgetLevel = 'none' | 'ok' | 'approaching' | 'over';

export interface BudgetStatus {
  hasBudget: boolean;
  spentMinor: number;
  budgetMinor: number | null;
  remainingMinor: number; // may be negative
  percentUsed: number; // 1 decimal, e.g. 80.5
  level: BudgetLevel;
  crossed: number[]; // thresholds where percent >= threshold
}

export function budgetStatus(
  spentMinor: number,
  budgetMinor: number | null,
  thresholds: number[] = [80, 100]
): BudgetStatus {
  if (budgetMinor === null || budgetMinor <= 0) {
    return {
      hasBudget: false,
      spentMinor,
      budgetMinor: null,
      remainingMinor: 0,
      percentUsed: 0,
      level: 'none',
      crossed: [],
    };
  }

  const remainingMinor = budgetMinor - spentMinor;

  // Integer math: (spent * 1000) / budget → gives 1 decimal of percent
  const percentTimes10 = Math.floor((spentMinor * 1000) / budgetMinor);
  const percentUsed = percentTimes10 / 10;

  // Determine crossed thresholds
  const sortedThresholds = [...thresholds].sort((a, b) => a - b);
  const crossed = sortedThresholds.filter((t) => percentUsed >= t);

  // Determine level
  let level: BudgetLevel;
  const highest = sortedThresholds[sortedThresholds.length - 1] ?? 100;
  const lowest = sortedThresholds[0] ?? 80;

  if (percentUsed >= highest) {
    level = 'over';
  } else if (percentUsed >= lowest) {
    level = 'approaching';
  } else {
    level = 'ok';
  }

  return {
    hasBudget: true,
    spentMinor,
    budgetMinor,
    remainingMinor,
    percentUsed,
    level,
    crossed,
  };
}

// ── Validate thresholds ─────────────────────────────────────────────────────
export function validateThresholds(thresholds: number[]): string | null {
  if (thresholds.length === 0) return 'At least one threshold is required';
  if (thresholds.length > 3) return 'Maximum 3 thresholds allowed';
  for (const t of thresholds) {
    if (!Number.isInteger(t)) return 'Thresholds must be integers';
    if (t < 1 || t > 200) return 'Thresholds must be between 1 and 200';
  }
  // Must be ascending
  for (let i = 1; i < thresholds.length; i++) {
    if (thresholds[i] <= thresholds[i - 1]) return 'Thresholds must be in ascending order';
  }
  return null;
}
