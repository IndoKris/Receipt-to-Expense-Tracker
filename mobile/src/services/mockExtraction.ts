import { ExtractionService, ExtractionResult } from './extraction';

// ── Mock extraction service for dev/tests ───────────────────────────────────
// Only active when EXPO_PUBLIC_USE_MOCK=1

const MOCK_RECEIPT_RESULT: ExtractionResult = {
  requestId: 'mock-receipt-001',
  readable: true,
  documentType: 'receipt',
  fields: {
    merchant: { value: 'Chai Point', confidence: 0.92, needsReview: false },
    amount: { value: '250.00', confidence: 0.97, needsReview: false },
    currency: { value: 'INR', confidence: 0.95, needsReview: false },
    date: { value: '2026-10-12', confidence: 0.85, needsReview: false },
    category: { value: 'food', confidence: 0.8, needsReview: false },
    paymentMethod: { value: 'upi', confidence: 0.9, needsReview: false },
    tax: { value: null, confidence: 0, needsReview: false },
    discount: { value: null, confidence: 0, needsReview: false },
    transactionRef: { value: null, confidence: 0, needsReview: false },
    paymentStatus: { value: null, confidence: 0, needsReview: false },
  },
  warnings: [],
  model: 'mock',
};

const MOCK_UPI_RESULT: ExtractionResult = {
  requestId: 'mock-upi-001',
  readable: true,
  documentType: 'payment_screenshot',
  fields: {
    merchant: { value: 'Swiggy', confidence: 0.88, needsReview: false },
    amount: { value: '450.00', confidence: 0.95, needsReview: false },
    currency: { value: 'INR', confidence: 0.95, needsReview: false },
    date: { value: '2026-10-12', confidence: 0.7, needsReview: true },
    category: { value: 'food', confidence: 0.75, needsReview: false },
    paymentMethod: { value: 'upi', confidence: 0.98, needsReview: false },
    tax: { value: null, confidence: 0, needsReview: false },
    discount: { value: null, confidence: 0, needsReview: false },
    transactionRef: { value: '428193771204', confidence: 0.9, needsReview: false },
    paymentStatus: { value: 'success', confidence: 0.9, needsReview: false },
  },
  warnings: ['status_unverified'],
  model: 'mock',
};

export class MockExtractionService implements ExtractionService {
  async extract(params: {
    imageUri: string;
    hint: 'auto' | 'receipt' | 'payment_screenshot';
    signal?: AbortSignal;
  }): Promise<ExtractionResult> {
    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 1500));

    if (params.signal?.aborted) {
      throw new Error('Cancelled');
    }

    if (params.hint === 'payment_screenshot') {
      return { ...MOCK_UPI_RESULT };
    }

    return { ...MOCK_RECEIPT_RESULT };
  }
}
