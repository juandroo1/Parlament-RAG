import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { de, type Messages } from "./de";
import {
  MESSAGES,
  readLanguage,
  saveLanguage,
  type Language,
} from "./language";

interface I18n {
  language: Language;
  t: Messages;
  setLanguage: (language: Language) => void;
}

const I18nContext = createContext<I18n>({
  language: "de",
  t: de,
  setLanguage: () => {},
});

/** Sprache der Oberfläche; setzt `<html lang>`, Titel und Beschreibung der Seite (AK-10.2). */
export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(readLanguage);
  const t = MESSAGES[language];

  useEffect(() => {
    document.documentElement.lang = language;
    document.title = t.pageTitle;
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute("content", t.pageDescription);
  }, [language, t]);

  const setLanguage = useCallback((next: Language) => {
    saveLanguage(next);
    setLanguageState(next);
  }, []);

  const value = useMemo(
    () => ({ language, t, setLanguage }),
    [language, t, setLanguage],
  );
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  return useContext(I18nContext);
}
