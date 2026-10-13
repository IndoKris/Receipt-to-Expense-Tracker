# Known Limitations — Receipt-to-Expense Tracker (MVP)

> This document lists known limitations of the MVP release. They are not bugs — they are deliberate scope decisions documented honestly.

## Data & Privacy
- **Single device only.** All data is stored on-device. No cloud backup or sync. If the app is deleted, all data is lost.
- **No accounts.** There is no user authentication system. The app is for one local user.
- **App token is not a true secret.** The `EXPO_PUBLIC_APP_TOKEN` is bundled in the app and is extractable. It only deters casual abuse; it is not a security boundary.
- **Google processes your images.** Receipt/screenshot images are sent to Google's Gemini API for text extraction. See the in-app Privacy notice for details.

## Extraction & AI
- **Extraction can be wrong.** AI-suggested values may be inaccurate. Always review before saving.
- **No duplicate detection.** The app does not detect or warn about duplicate expenses.
- **No itemized extraction.** Only totals are extracted, not individual line items.
- **No line-item or per-product extraction.**

## Currency & Budget
- **No multi-currency conversion.** Expenses in currencies other than the base currency (default INR) are stored but excluded from totals and budget calculations.
- **Single monthly budget only.** No per-category or per-week budgets.

## Platform & Features
- **iOS only via Expo Go.** No Android support in MVP.
- **No CSV export or import.**
- **No Share Sheet integration.**
- **No widgets or Shortcuts.**
- **No custom categories.** Only the 8 default categories are available.
- **No recurring expense detection.**
- **No biometric lock.**
- **No bank or payment app integrations.**

## Technical
- **No on-device encryption beyond iOS defaults.** Data relies on iOS data protection (enabled by default).
- **Notifications are best-effort in Expo Go.** Local notifications may have limitations.
- **No locale comma-decimal handling.** Only dot-decimal format is supported (e.g., 1234.50).
- **Hermes `Intl` limitations.** Currency formatting may fall back to manual grouping if the locale is unsupported.
