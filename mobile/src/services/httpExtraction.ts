import { config } from '../config';
import {
  ExtractionService,
  ExtractionResult,
  ExtractionError,
  FieldState,
} from './extraction';

// ── Map backend snake_case to camelCase ─────────────────────────────────────

interface ApiFieldResponse {
  value: string | null;
  confidence: number;
  needs_review: boolean;
}

interface ApiResponse {
  request_id: string;
  readable: boolean;
  document_type: string;
  fields: Record<string, ApiFieldResponse>;
  warnings: string[];
  model: string;
}

function mapField<T>(api: ApiFieldResponse | undefined): FieldState<T> {
  if (!api) {
    return { value: null, confidence: 0, needsReview: true };
  }
  return {
    value: api.value as T | null,
    confidence: api.confidence,
    needsReview: api.needs_review,
  };
}

function mapResponse(api: ApiResponse): ExtractionResult {
  return {
    requestId: api.request_id,
    readable: api.readable,
    documentType: api.document_type as ExtractionResult['documentType'],
    fields: {
      merchant: mapField(api.fields.merchant),
      amount: mapField(api.fields.amount),
      currency: mapField(api.fields.currency),
      date: mapField(api.fields.date),
      category: mapField(api.fields.category),
      paymentMethod: mapField(api.fields.payment_method),
      tax: mapField(api.fields.tax),
      discount: mapField(api.fields.discount),
      transactionRef: mapField(api.fields.transaction_ref),
      paymentStatus: mapField(api.fields.payment_status),
    },
    warnings: api.warnings || [],
    model: api.model,
  };
}

// ── Map HTTP errors to ExtractionError ──────────────────────────────────────

function mapHttpError(status: number, body: any): ExtractionError {
  const code = body?.error?.code;
  const message = body?.error?.message;

  switch (status) {
    case 401:
      return new ExtractionError('unauthorized', message || 'Unauthorized', false);
    case 413:
      return new ExtractionError('too_large', message || 'Image too large', false);
    case 415:
      return new ExtractionError('unsupported', message || 'Unsupported file type', false);
    case 429:
      return new ExtractionError('rate_limited', message || 'Rate limited', true);
    case 502:
      return new ExtractionError('server_error', message || 'Server error', true);
    case 504:
      return new ExtractionError('timeout', message || 'Request timeout', true);
    case 422:
      return new ExtractionError('invalid_output', message || 'Invalid output', true);
    default:
      return new ExtractionError('server_error', message || `HTTP ${status}`, true);
  }
}

// ── HTTP Extraction Service ─────────────────────────────────────────────────

export class HttpExtractionService implements ExtractionService {
  private baseUrl: string;
  private appToken: string;

  constructor(baseUrl?: string, appToken?: string) {
    this.baseUrl = baseUrl || config.apiBaseUrl;
    this.appToken = appToken || config.appToken;
  }

  async extract(params: {
    imageUri: string;
    hint: 'auto' | 'receipt' | 'payment_screenshot';
    signal?: AbortSignal;
  }): Promise<ExtractionResult> {
    const { imageUri, hint, signal } = params;

    // Create form data
    const formData = new FormData();

    // Read the image file and add to form
    const filename = imageUri.split('/').pop() || 'image.jpg';
    const match = /\.(\w+)$/.exec(filename);
    const type = match ? `image/${match[1] === 'jpg' ? 'jpeg' : match[1]}` : 'image/jpeg';

    formData.append('image', {
      uri: imageUri,
      name: filename,
      type,
    } as any);

    formData.append('hint', hint);

    // Set up timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);

    // Combine with external signal
    if (signal) {
      signal.addEventListener('abort', () => controller.abort());
    }

    try {
      const response = await fetch(`${this.baseUrl}/v1/extract`, {
        method: 'POST',
        headers: {
          'X-App-Token': this.appToken,
        },
        body: formData,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let body: any = {};
        try {
          body = await response.json();
        } catch {}
        throw mapHttpError(response.status, body);
      }

      const data: ApiResponse = await response.json();

      // Check if readable
      if (!data.readable) {
        throw new ExtractionError('unreadable', "Couldn't read this image", false);
      }

      return mapResponse(data);
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof ExtractionError) throw error;

      if (error instanceof TypeError && error.message.includes('Network')) {
        throw new ExtractionError('offline', 'Network error', true);
      }

      if (error instanceof DOMException && error.name === 'AbortError') {
        if (signal?.aborted) {
          throw new ExtractionError('cancelled', 'Cancelled by user', false);
        }
        throw new ExtractionError('timeout', 'Request timed out', true);
      }

      throw new ExtractionError('server_error', 'Unexpected error', true);
    }
  }
}
