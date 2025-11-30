import { Injectable } from '@angular/core';

export interface AppSettings {
  theme: 'light' | 'dark';
  notifications: boolean;
  pushNotifications?: boolean; // Thêm push notifications
  aiModel: string;
  apiKey?: string;
}

const STORAGE_KEY = 'app_settings_v1';

const DEFAULTS: AppSettings = {
  theme: 'light',
  notifications: true,
  pushNotifications: false,
  aiModel: 'gpt-4',
  apiKey: ''
};

@Injectable({ providedIn: 'root' })
export class SettingsService {
  getSettings(): AppSettings {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) as AppSettings : DEFAULTS;
    } catch (e) {
      return DEFAULTS;
    }
  }

  saveSettings(s: AppSettings) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  }

  resetDefaults() {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULTS));
  }
}
