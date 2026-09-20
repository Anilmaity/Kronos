/**
 * Central registry of localStorage keys used by the auth flow and UI.
 * Call sites keep their original localStorage semantics — this module only
 * removes the magic strings.
 */
export const STORAGE_KEYS = {
  token: "token",
  userEmail: "userEmail",
  password: "password",
  otpSent: "otpSent",
  otpTimestamp: "otpTimestamp",
  isSuperuser: "isSuperuser",
  authStep: "AUTH_STEP",
} as const;

export type StorageKey = (typeof STORAGE_KEYS)[keyof typeof STORAGE_KEYS];

/** SSR-safe read; returns null on the server. */
export const getStorageItem = (key: StorageKey): string | null =>
  typeof window === "undefined" ? null : window.localStorage.getItem(key);

/** SSR-safe write; no-op on the server. */
export const setStorageItem = (key: StorageKey, value: string): void => {
  if (typeof window !== "undefined") window.localStorage.setItem(key, value);
};

/** SSR-safe removal; no-op on the server. */
export const removeStorageItem = (key: StorageKey): void => {
  if (typeof window !== "undefined") window.localStorage.removeItem(key);
};
