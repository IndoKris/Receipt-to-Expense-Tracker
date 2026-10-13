// ── Transaction query builder ───────────────────────────────────────────────
// Builds {sql, params} from filter criteria. Pure function.

import { CategoryId } from './types';

export interface FilterCriteria {
  q?: string;          // search by merchant (substring, case-insensitive)
  from?: string;       // inclusive start date (YYYY-MM-DD)
  to?: string;         // inclusive end date (YYYY-MM-DD)
  categoryId?: CategoryId;
  limit?: number;      // default 50
  offset?: number;     // default 0
}

export interface FilterQuery {
  sql: string;
  countSql: string;
  params: (string | number)[];
  countParams: (string | number)[];
}

/**
 * Escape special LIKE characters: % _ \
 */
function escapeLike(s: string): string {
  return s.replace(/\\/g, '\\\\').replace(/%/g, '\\%').replace(/_/g, '\\_');
}

export function buildFilterQuery(criteria: FilterCriteria): FilterQuery {
  const conditions: string[] = [];
  const params: (string | number)[] = [];

  if (criteria.q && criteria.q.trim()) {
    conditions.push(`merchant LIKE ? ESCAPE '\\'`);
    params.push(`%${escapeLike(criteria.q.trim())}%`);
  }

  if (criteria.from) {
    conditions.push(`expense_date >= ?`);
    params.push(criteria.from);
  }

  if (criteria.to) {
    conditions.push(`expense_date <= ?`);
    params.push(criteria.to);
  }

  if (criteria.categoryId) {
    conditions.push(`category_id = ?`);
    params.push(criteria.categoryId);
  }

  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
  const limit = criteria.limit ?? 50;
  const offset = criteria.offset ?? 0;

  const sql = `SELECT * FROM expenses ${whereClause} ORDER BY expense_date DESC, created_at DESC LIMIT ? OFFSET ?`;
  const countSql = `SELECT COUNT(*) as count FROM expenses ${whereClause}`;

  return {
    sql,
    countSql,
    params: [...params, limit, offset],
    countParams: [...params],
  };
}

// ── Active filter helpers ───────────────────────────────────────────────────

export interface ActiveFilter {
  type: 'search' | 'dateFrom' | 'dateTo' | 'category';
  label: string;
  value: string;
}

export function getActiveFilters(criteria: FilterCriteria): ActiveFilter[] {
  const filters: ActiveFilter[] = [];

  if (criteria.q && criteria.q.trim()) {
    filters.push({ type: 'search', label: `"${criteria.q.trim()}"`, value: criteria.q.trim() });
  }
  if (criteria.from) {
    filters.push({ type: 'dateFrom', label: `From: ${criteria.from}`, value: criteria.from });
  }
  if (criteria.to) {
    filters.push({ type: 'dateTo', label: `To: ${criteria.to}`, value: criteria.to });
  }
  if (criteria.categoryId) {
    filters.push({ type: 'category', label: criteria.categoryId, value: criteria.categoryId });
  }

  return filters;
}
