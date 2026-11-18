import { LANGUAGES } from "../i18n/language";
import { useI18n } from "../i18n/LanguageProvider";

// Name jeder Sprache in ihr selbst, damit man die eigene Sprache auch in der fremden Oberfläche findet.
const NAMES = { de: "Deutsch", fr: "Français" } as const;

/** Umschalter DE/FR in der Kopfzeile (AK-10.1). */
export function LanguageToggle() {
  const { language, setLanguage, t } = useI18n();
  return (
    <div
      role="group"
      aria-label={t.languageLabel}
      className="flex rounded-full border border-border p-0.5"
    >
      {LANGUAGES.map((code) => {
        const pressed = language === code;
        return (
          <button
            key={code}
            type="button"
            lang={code}
            aria-label={NAMES[code]}
            aria-pressed={pressed}
            title={NAMES[code]}
            onClick={() => setLanguage(code)}
            className={
              "h-11 min-w-11 rounded-full px-2 text-sm font-bold sm:h-10 sm:pointer-coarse:h-11 " +
              (pressed
                ? "bg-primary text-on-primary"
                : "text-muted hover:text-text")
            }
          >
            {code.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}
