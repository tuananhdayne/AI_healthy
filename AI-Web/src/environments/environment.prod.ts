export const environment = {
  production: true,
  apiBaseUrl: typeof window !== 'undefined' && (window as any).__APP_API_URL__
    ? (window as any).__APP_API_URL__
    : 'https://your-api-domain.com'
};

