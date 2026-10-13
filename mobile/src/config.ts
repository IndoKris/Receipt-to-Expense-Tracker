import Constants from 'expo-constants';

const extra = Constants.expoConfig?.extra ?? {};

export const config = {
  apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  appToken: process.env.EXPO_PUBLIC_APP_TOKEN || 'change-me',
  useMock: process.env.EXPO_PUBLIC_USE_MOCK === '1',
};
