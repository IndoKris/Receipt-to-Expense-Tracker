// ── Provenance tracking ─────────────────────────────────────────────────────
// Per-field state: 'extracted' | 'edited' | 'manual'

import { ProvenanceState } from './types';

export type FieldProvenance = Record<string, ProvenanceState>;

const TRACKED_FIELDS = [
  'merchant', 'amount', 'currency', 'date', 'category',
  'paymentMethod', 'tax', 'discount', 'transactionRef', 'paymentStatus',
];

/**
 * Initialize provenance for a new review form.
 * Fields with extracted values → 'extracted', blank/null → 'manual'
 */
export function initProvenance(
  extractedFields: Record<string, unknown> | null
): FieldProvenance {
  const prov: FieldProvenance = {};
  for (const field of TRACKED_FIELDS) {
    if (extractedFields && extractedFields[field] !== null && extractedFields[field] !== undefined && extractedFields[field] !== '') {
      prov[field] = 'extracted';
    } else {
      prov[field] = 'manual';
    }
  }
  return prov;
}

/**
 * Update provenance when a user changes a field value.
 * If the field was 'extracted' and the new value differs from the original, → 'edited'.
 * If the user reverts to the original extracted value, → 'extracted'.
 * If the field was 'manual', it stays 'manual'.
 */
export function updateProvenance(
  current: FieldProvenance,
  field: string,
  newValue: string | null,
  originalExtractedValue: string | null
): FieldProvenance {
  const updated = { ...current };

  if (current[field] === 'manual') {
    // Stays manual
    return updated;
  }

  // Field was extracted or edited
  if (newValue === originalExtractedValue) {
    // User reverted to original — restore to extracted
    updated[field] = 'extracted';
  } else {
    updated[field] = 'edited';
  }

  return updated;
}

/**
 * Get display label for provenance state.
 */
export function provenanceLabel(state: ProvenanceState): string {
  switch (state) {
    case 'extracted': return 'AI-suggested';
    case 'edited': return 'Edited';
    case 'manual': return 'Manual';
  }
}

/**
 * Get provenance color key.
 */
export function provenanceColor(state: ProvenanceState): string {
  switch (state) {
    case 'extracted': return 'info';
    case 'edited': return 'warning';
    case 'manual': return 'neutral';
  }
}
