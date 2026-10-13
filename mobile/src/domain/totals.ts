// ── Totals computation (pure functions) ─────────────────────────────────────
// All totals use stored records, never LLM output.

import { CurrencyCode, CategoryId, CATEGORIES } from './types';

// ── Month helpers ───────────────────────────────────────────────────────────

/** Returns 'YYYY-MM-DD' for the first day of the given month string 'YYYY-MM' */
export function monthStart(month: string): string {
  return `${month}-01`;
}

/** Returns 'YYYY-MM-DD' for the first day of the next month */
export function monthEnd(month: string): string {
  const [y, m] = month.split('-').map(Number);
  const nextMonth = m === 12 ? 1 : m + 1;
  const nextYear = m === 12 ? y + 1 : y;
  return `${nextYear}-${String(nextMonth).padStart(2, '0')}-01`;
}

/** Returns current month as 'YYYY-MM' */
export function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

/** Returns previous month as 'YYYY-MM' */
export function prevMonth(month: string): string {
  const [y, m] = month.split('-').map(Number);
  const pm = m === 1 ? 12 : m - 1;
  const py = m === 1 ? y - 1 : y;
  return `${py}-${String(pm).padStart(2, '0')}`;
}

/** Returns next month as 'YYYY-MM' */
export function nextMonth(month: string): string {
  const [y, m] = month.split('-').map(Number);
  const nm = m === 12 ? 1 : m + 1;
  const ny = m === 12 ? y + 1 : y;
  return `${ny}-${String(nm).padStart(2, '0')}`;
}

/** Format month for display: 'October 2026' */
export function formatMonth(month: string): string {
  const [y, m] = month.split('-').map(Number);
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];
  return `${months[m - 1]} ${y}`;
}

// ── SQL query builders (return {sql, params} for expensesRepo) ──────────────

export interface MonthTotalQuery {
  sql: string;
  params: (string | number)[];
}

/** SQL to get total spending for a month in the base currency */
export function monthTotalQuery(month: string, baseCurrency: CurrencyCode): MonthTotalQuery {
  return {
    sql: `SELECT COALESCE(SUM(amount_minor), 0) as total FROM expenses WHERE currency = ? AND expense_date >= ? AND expense_date < ?`,
    params: [baseCurrency, monthStart(month), monthEnd(month)],
  };
}

/** SQL to get per-category totals for a month */
export function categoryTotalsQuery(month: string, baseCurrency: CurrencyCode): MonthTotalQuery {
  return {
    sql: `SELECT category_id, COALESCE(SUM(amount_minor), 0) as total FROM expenses WHERE currency = ? AND expense_date >= ? AND expense_date < ? GROUP BY category_id ORDER BY total DESC`,
    params: [baseCurrency, monthStart(month), monthEnd(month)],
  };
}

/** SQL to count expenses with non-base currencies in a month */
export function otherCurrencyCountQuery(month: string, baseCurrency: CurrencyCode): MonthTotalQuery {
  return {
    sql: `SELECT COUNT(*) as count FROM expenses WHERE currency != ? AND expense_date >= ? AND expense_date < ?`,
    params: [baseCurrency, monthStart(month), monthEnd(month)],
  };
}

// ── Category total computation helpers ──────────────────────────────────────

export interface CategoryTotal {
  categoryId: CategoryId;
  categoryName: string;
  totalMinor: number;
  percentage: number; // 0-100, rounded to 1 decimal
}

/** Compute percentages for category totals */
export function computeCategoryPercentages(
  rawTotals: { category_id: string; total: number }[],
  monthTotal: number
): CategoryTotal[] {
  return rawTotals.map((row) => {
    const cat = CATEGORIES.find((c) => c.id === row.category_id);
    const pct = monthTotal > 0 ? Math.round((row.total / monthTotal) * 1000) / 10 : 0;
    return {
      categoryId: row.category_id as CategoryId,
      categoryName: cat?.name ?? row.category_id,
      totalMinor: row.total,
      percentage: pct,
    };
  });
}
