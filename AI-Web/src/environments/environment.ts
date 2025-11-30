const runtimeApiUrl =
  typeof window !== 'undefined' && (window as any).__APP_API_URL__
    ? (window as any).__APP_API_URL__
    : 'http://localhost:8000';

export const environment = {
  production: false,
  apiBaseUrl: runtimeApiUrl
};

