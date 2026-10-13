// ── Extraction service types & interface ─────────────────────────────────────
// Mirrors the backend API contract (TRD §3.7)

export type FieldState<T> = {
  value: T | null;
  confidence: number;
  needsReview: boolean;
};

export type ExtractionResult = {
  requestId: string;
  readable: boolean;
  documentType: 'receipt' | 'payment_screenshot' | 'unknown';
  fields: {
    merchant: FieldState<string>;
    amount: FieldState<string>;
    currency: FieldState<string>;
    date: FieldState<string>;
    category: FieldState<string>;
    paymentMethod: FieldState<string>;
    tax: FieldState<string>;
    discount: FieldState<string>;
    transactionRef: FieldState<string>;
    paymentStatus: FieldState<'success' | 'pending' | 'failed' | 'unknown'>;
  };
  warnings: string[];
  model: string;
};

export type ExtractionErrorCode =
  | 'offline'
  | 'timeout'
  | 'unreadable'
  | 'unsupported'
  | 'too_large'
  | 'rate_limited'
  | 'unauthorized'
  | 'server_error'
  | 'invalid_output'
  | 'cancelled';

export class ExtractionError extends Error {
  code: ExtractionErrorCode;
  retryable: boolean;

  constructor(code: ExtractionErrorCode, message: string, retryable: boolean = false) {
    super(message);
    this.name = 'ExtractionError';
    this.code = code;
    this.retryable = retryable;
  }
}

export const ERROR_MESSAGES: Record<ExtractionErrorCode, string> = {
  offline: "You're offline. Your photo is kept — retry when connected or enter manually.",
  timeout: 'That took too long. Please try again.',
  unreadable: "We couldn't read this image. Try a clearer, flatter, well-lit photo.",
  unsupported: "This file type isn't supported.",
  too_large: 'This image is too large. Try a smaller one.',
  rate_limited: 'Too many scans. Wait a minute and try again.',
  unauthorized: "The app isn't configured correctly. Please check settings.",
  server_error: 'The scanning service had a problem. Please try again.',
  invalid_output: 'The scan produced an unexpected result. Please try again or enter manually.',
  cancelled: 'Scan cancelled.',
};

export interface ExtractionService {
  extract(params: {
    imageUri: string;
    hint: 'auto' | 'receipt' | 'payment_screenshot';
    signal?: AbortSignal;
  }): Promise<ExtractionResult>;
}
