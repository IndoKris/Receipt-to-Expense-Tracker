import { CurrencyCode, CategoryId, CATEGORIES, SUPPORTED_CURRENCIES } from './types';

export interface ValidationErrors {
  merchant?: string;
  amount?: string;
  date?: string;
  currency?: string;
  category?: string;
}

// ── Individual validators ───────────────────────────────────────────────────

export function validateMerchant(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return 'Merchant name is required';
  if (trimmed.length > 80) return 'Merchant name must be 80 characters or less';
  return null;
}

export function validateAmount(value: string): string | null {
  if (!value || !value.trim()) return 'Amount is required';
  const cleaned = value.replace(/[₹$€£¥\s,]/g, '').trim();
  if (!cleaned) return 'Amount is required';
  if (!/^\d+(\.\d+)?$/.test(cleaned)) return 'Enter a valid number';
  const num = parseFloat(cleaned);
  if (num <= 0) return 'Amount must be greater than zero';
  if (num > 1_000_000_000) return 'Amount is too large';
  return null;
}

export function validateDate(value: string): string | null {
  if (!value) return 'Date is required';

  // Must be YYYY-MM-DD format
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return 'Invalid date format';

  const date = new Date(value + 'T00:00:00');
  if (isNaN(date.getTime())) return 'Invalid date';

  // Check the parsed date matches the input (catches Feb 30, etc.)
  const [y, m, d] = value.split('-').map(Number);
  if (date.getFullYear() !== y || date.getMonth() + 1 !== m || date.getDate() !== d) {
    return 'Invalid date';
  }

  // Not before 2000-01-01
  if (date < new Date('2000-01-01T00:00:00')) return 'Date must be after January 1, 2000';

  // Not in the future beyond tomorrow
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(23, 59, 59, 999);
  if (date > tomorrow) return 'Date cannot be in the future';

  return null;
}

export function validateCurrency(value: string): string | null {
  if (!value) return 'Currency is required';
  if (!SUPPORTED_CURRENCIES.includes(value as CurrencyCode)) {
    return 'Unsupported currency';
  }
  return null;
}

export function validateCategory(value: string): string | null {
  if (!value) return 'Category is required';
  const ids = CATEGORIES.map((c) => c.id);
  if (!ids.includes(value as CategoryId)) return 'Invalid category';
  return null;
}

// ── Validate entire form ────────────────────────────────────────────────────

export interface FormData {
  merchant: string;
  amount: string;
  date: string;
  currency: string;
  category: string;
}

export function validateForm(data: FormData): ValidationErrors {
  const errors: ValidationErrors = {};

  const merchantErr = validateMerchant(data.merchant);
  if (merchantErr) errors.merchant = merchantErr;

  const amountErr = validateAmount(data.amount);
  if (amountErr) errors.amount = amountErr;

  const dateErr = validateDate(data.date);
  if (dateErr) errors.date = dateErr;

  const currencyErr = validateCurrency(data.currency);
  if (currencyErr) errors.currency = currencyErr;

  const categoryErr = validateCategory(data.category);
  if (categoryErr) errors.category = categoryErr;

  return errors;
}

export function isFormValid(errors: ValidationErrors): boolean {
  return Object.keys(errors).length === 0;
}
