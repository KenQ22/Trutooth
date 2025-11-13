import { Dispatch, SetStateAction, useEffect, useState } from "react";

function readValue<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") {
    return fallback;
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) {
      return fallback;
    }
    return JSON.parse(raw) as T;
  } catch (error) {
    console.warn(`Failed to read persisted state for ${key}`, error);
    return fallback;
  }
}

export function usePersistedState<T>(key: string, defaultValue: T): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => readValue<T>(key, defaultValue));

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.warn(`Failed to persist state for ${key}`, error);
    }
  }, [key, value]);

  return [value, setValue];
}
