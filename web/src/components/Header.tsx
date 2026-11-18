import logoDarkPng from "../assets/logo-dark.png";
import logoDarkWebp from "../assets/logo-dark.webp";
import logoLightPng from "../assets/logo-light.png";
import logoLightWebp from "../assets/logo-light.webp";
import { useI18n } from "../i18n/LanguageProvider";
import { HowItWorks } from "./HowItWorks";
import { ShieldIcon } from "./icons";
import { LanguageToggle } from "./LanguageToggle";
import { ThemeToggle } from "./ThemeToggle";

// Logo-Dateien: 276 × 104 px, angezeigt mit 52 px (Desktop) bzw. 38 px Höhe (Handy).
const LOGO = "h-[38px] w-auto sm:h-[52px]";

/** Kopfzeile mit Logo (hell/dunkel), Umschaltern und dem Hinweis «Privates Projekt» (AK-8.1, AK-8.2). */
export function Header() {
  const { t } = useI18n();
  return (
    <header>
      <div className="border-b border-border">
        <div className="mx-auto flex max-w-[1120px] items-center justify-between gap-4 px-4 py-2.5 sm:px-6 sm:py-3.5">
          <a
            href="#top"
            className="flex min-h-11 shrink-0 items-center rounded-md"
          >
            <picture className="block dark:hidden">
              <source srcSet={logoLightWebp} type="image/webp" />
              <img
                src={logoLightPng}
                alt="Frag das Parlament"
                width={276}
                height={104}
                className={LOGO}
              />
            </picture>
            <picture className="hidden dark:block">
              <source srcSet={logoDarkWebp} type="image/webp" />
              <img
                src={logoDarkPng}
                alt="Frag das Parlament"
                width={276}
                height={104}
                className={LOGO}
              />
            </picture>
          </a>
          <div className="flex items-center gap-1.5 sm:gap-2.5">
            <HowItWorks />
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </div>
      </div>
      <div className="mx-auto max-w-[760px] px-4 pt-3 sm:px-6 sm:pt-5">
        <p className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-xs text-muted sm:text-[13px]">
          <ShieldIcon />
          {t.notice}
        </p>
      </div>
    </header>
  );
}
