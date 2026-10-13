// ── Core Types ──────────────────────────────────────────────────────────────

export type CategoryId =
  | 'food'
  | 'groceries'
  | 'transport'
  | 'shopping'
  | 'bills'
  | 'health'
  | 'education'
  | 'other';

export const CATEGORIES: { id: CategoryId; name: string; sortOrder: number }[] = [
  { id: 'food', name: 'Food', sortOrder: 1 },
  { id: 'groceries', name: 'Groceries', sortOrder: 2 },
  { id: 'transport', name: 'Transport', sortOrder: 3 },
  { id: 'shopping', name: 'Shopping', sortOrder: 4 },
  { id: 'bills', name: 'Bills', sortOrder: 5 },
  { id: 'health', name: 'Health', sortOrder: 6 },
  { id: 'education', name: 'Education', sortOrder: 7 },
  { id: 'other', name: 'Other', sortOrder: 8 },
];

export const CATEGORY_MAP = Object.fromEntries(
  CATEGORIES.map((c) => [c.id, c])
) as Record<CategoryId, (typeof CATEGORIES)[number]>;

export type PaymentMethod = 'upi' | 'card' | 'cash' | 'netbanking' | 'wallet' | 'other';
export const PAYMENT_METHODS: PaymentMethod[] = ['upi', 'card', 'cash', 'netbanking', 'wallet', 'other'];

export type SourceType = 'receipt' | 'payment_screenshot' | 'manual';
export type ScreenshotStatus = 'success' | 'pending' | 'failed' | 'unknown';
export type ProvenanceState = 'extracted' | 'edited' | 'manual';

export type CurrencyCode = 'INR' | 'USD' | 'EUR' | 'GBP' | 'AED' | 'SGD' | 'JPY' | 'AUD' | 'CAD';

export const SUPPORTED_CURRENCIES: CurrencyCode[] = [
  'INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD', 'JPY', 'AUD', 'CAD',
];

export interface Expense {
  id: string;
  merchant: string;
  amountMinor: number;
  currency: CurrencyCode;
  expenseDate: string; // YYYY-MM-DD
  categoryId: CategoryId;
  paymentMethod: PaymentMethod | null;
  taxMinor: number | null;
  discountMinor: number | null;
  transactionRef: string | null;
  sourceType: SourceType;
  screenshotStatus: ScreenshotStatus | null;
  imagePath: string | null;
  provenance: Record<string, ProvenanceState>;
  createdAt: string;
  updatedAt: string;
}

export interface ExpenseRow {
  id: string;
  merchant: string;
  amount_minor: number;
  currency: string;
  expense_date: string;
  category_id: string;
  payment_method: string | null;
  tax_minor: number | null;
  discount_minor: number | null;
  transaction_ref: string | null;
  source_type: string;
  screenshot_status: string | null;
  image_path: string | null;
  provenance: string; // JSON
  created_at: string;
  updated_at: string;
}

export function rowToExpense(row: ExpenseRow): Expense {
  return {
    id: row.id,
    merchant: row.merchant,
    amountMinor: row.amount_minor,
    currency: row.currency as CurrencyCode,
    expenseDate: row.expense_date,
    categoryId: row.category_id as CategoryId,
    paymentMethod: row.payment_method as PaymentMethod | null,
    taxMinor: row.tax_minor,
    discountMinor: row.discount_minor,
    transactionRef: row.transaction_ref,
    sourceType: row.source_type as SourceType,
    screenshotStatus: row.screenshot_status as ScreenshotStatus | null,
    imagePath: row.image_path,
    provenance: JSON.parse(row.provenance),
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}
