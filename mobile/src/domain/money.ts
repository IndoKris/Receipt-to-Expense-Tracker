import { CurrencyCode } from './types';

// ── Currency exponent table ─────────────────────────────────────────────────
const CURRENCY_EXPONENTS: Record<CurrencyCode, number> = {
  INR: 2, USD: 2, EUR: 2, GBP: 2, AED: 2, SGD: 2, AUD: 2, CAD: 2,
  JPY: 0,
};

export function currencyExponent(currency: CurrencyCode): number {
  return CURRENCY_EXPONENTS[currency] ?? 2;
}

// ── Parse amount string → integer minor units ───────────────────────────────
// Accepts: "1234", "1,234.50", "₹1,234.5", "1234.5"
// Rejects: empty, negative, zero, >2 decimals (for exp 2), non-numeric, > 1,000,000,000
export function parseAmount(input: string, currency: CurrencyCode): number | null {
  if (!input || typeof input !== 'string') return null;

  // Strip currency symbols, spaces, and leading/trailing whitespace
  let cleaned = input.replace(/[₹$€£¥\s]/g, '').trim();

  // Strip thousands commas
  cleaned = cleaned.replace(/,/g, '');

  // Reject empty after cleaning
  if (!cleaned) return null;

  // Must be digits with optional one decimal point
  if (!/^\d+(\.\d+)?$/.test(cleaned)) return null;

  const parts = cleaned.split('.');
  const intPart = parts[0];
  const decPart = parts[1] || '';

  const exp = currencyExponent(currency);

  // Check decimal places don't exceed currency exponent
  if (decPart.length > exp) return null;

  // Parse the major value
  const majorValue = parseFloat(cleaned);

  // Reject zero, negative, or absurdly large
  if (majorValue <= 0) return null;
  if (majorValue > 1_000_000_000) return null;

  // Convert to minor units
  const factor = Math.pow(10, exp);
  const minorUnits = Math.round(majorValue * factor);

  // Final sanity check
  if (minorUnits <= 0) return null;

  return minorUnits;
}

// ── Format minor units → display string ─────────────────────────────────────
export function formatMoney(
  minor: number,
  currency: CurrencyCode,
  locale: string = 'en-IN'
): string {
  const exp = currencyExponent(currency);
  const major = minor / Math.pow(10, exp);

  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits: exp,
      maximumFractionDigits: exp,
    }).format(major);
  } catch {
    // Fallback manual formatting for Hermes Intl limitations
    const fixed = major.toFixed(exp);
    const symbols: Partial<Record<CurrencyCode, string>> = {
      INR: '₹', USD: '$', EUR: '€', GBP: '£', JPY: '¥',
    };
    const sym = symbols[currency] || currency + ' ';

    // Simple Indian grouping for INR
    if (currency === 'INR') {
      const [intPart, decPart] = fixed.split('.');
      const lastThree = intPart.slice(-3);
      const rest = intPart.slice(0, -3);
      const grouped = rest
        ? rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + lastThree
        : lastThree;
      return `${sym}${grouped}${decPart ? '.' + decPart : ''}`;
    }

    // Western grouping
    const [intPart, decPart] = fixed.split('.');
    const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return `${sym}${grouped}${decPart ? '.' + decPart : ''}`;
  }
}

// ── Sum minor units (integer arithmetic only) ───────────────────────────────
export function sumMinor(amounts: number[]): number {
  let total = 0;
  for (const a of amounts) {
    total += a | 0; // Ensure integer
  }
  return total;
}

// ── Convert minor to major (for display calculations only) ──────────────────
export function minorToMajor(minor: number, currency: CurrencyCode): number {
  return minor / Math.pow(10, currencyExponent(currency));
}

// ── Convert major to minor ──────────────────────────────────────────────────
export function majorToMinor(major: number, currency: CurrencyCode): number {
  return Math.round(major * Math.pow(10, currencyExponent(currency)));
}
