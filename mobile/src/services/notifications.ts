import * as Notifications from 'expo-notifications';
import { budgetStatus } from '../domain/budget';

// ── Budget notifications service ────────────────────────────────────────────
// Fire after save only, once per threshold per month, only with permission.

/**
 * Check and send budget notifications after an expense save.
 * @param spentMinor Total spent this month
 * @param budgetMinor Monthly budget (null = no budget)
 * @param thresholds Warning thresholds [80, 100]
 * @param month Current month string 'YYYY-MM'
 * @param isEnabled Whether notifications are enabled
 * @param getNotified Callback to check if a threshold was already notified
 * @param markNotified Callback to mark a threshold as notified
 */
export async function checkBudgetNotifications(params: {
  spentMinor: number;
  budgetMinor: number | null;
  thresholds: number[];
  month: string;
  isEnabled: boolean;
  getNotified: (month: string, threshold: number) => Promise<boolean>;
  markNotified: (month: string, threshold: number) => Promise<void>;
}): Promise<void> {
  const { spentMinor, budgetMinor, thresholds, month, isEnabled, getNotified, markNotified } = params;

  if (!isEnabled || budgetMinor === null) return;

  // Check permission
  const { status } = await Notifications.getPermissionsAsync();
  if (status !== 'granted') return;

  const status_ = budgetStatus(spentMinor, budgetMinor, thresholds);

  for (const threshold of status_.crossed) {
    const alreadyNotified = await getNotified(month, threshold);
    if (alreadyNotified) continue;

    // Schedule immediate local notification
    let title: string;
    let body: string;

    if (threshold >= 100) {
      title = '🚨 Over Budget';
      body = `You've spent more than your monthly budget. Based on expenses recorded in this app.`;
    } else {
      title = `⚠️ ${threshold}% of Budget Used`;
      body = `You've used ${threshold}% of your monthly budget. Based on expenses recorded in this app.`;
    }

    await Notifications.scheduleNotificationAsync({
      content: { title, body },
      trigger: null, // Immediate
    });

    await markNotified(month, threshold);
  }
}

/**
 * Request notification permission (only called when user toggles on).
 * Returns true if granted.
 */
export async function requestNotificationPermission(): Promise<boolean> {
  const { status: existing } = await Notifications.getPermissionsAsync();
  if (existing === 'granted') return true;

  const { status } = await Notifications.requestPermissionsAsync();
  return status === 'granted';
}
