import { useCallback, useEffect, useState } from "react";
import {
  applyTheme,
  DARK_QUERY,
  readPreference,
  resolveTheme,
  savePreference,
  systemPrefersDark,
  type ThemePreference,
} from "./preference";

/** Wahl System/Hell/Dunkel; folgt bei `system` auch einem Wechsel im laufenden Betrieb (AK-9.1). */
export function useTheme() {
  const [preference, setPreferenceState] =
    useState<ThemePreference>(readPreference);
  const [systemDark, setSystemDark] = useState(systemPrefersDark);

  useEffect(() => {
    const query = window.matchMedia?.(DARK_QUERY);
    if (!query) return;
    const onChange = (event: MediaQueryListEvent) =>
      setSystemDark(event.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const theme = resolveTheme(preference, systemDark);

  useEffect(() => applyTheme(preference, theme), [preference, theme]);

  const setPreference = useCallback((next: ThemePreference) => {
    savePreference(next);
    setPreferenceState(next);
  }, []);

  return { preference, theme, setPreference };
}
