import type { JSX } from "react";
import type { ThemePreference } from "../theme/preference";
import { useTheme } from "../theme/useTheme";
import { MoonIcon, SunIcon, SystemIcon } from "./icons";

const OPTIONS: {
  value: ThemePreference;
  label: string;
  Icon: () => JSX.Element;
}[] = [
  { value: "light", label: "Hell", Icon: SunIcon },
  { value: "dark", label: "Dunkel", Icon: MoonIcon },
  { value: "system", label: "Wie System", Icon: SystemIcon },
];

// Handy: ein Knopf schaltet der Reihe nach durch.
const NEXT: Record<ThemePreference, ThemePreference> = {
  system: "light",
  light: "dark",
  dark: "system",
};

/** Umschalter für die Darstellung (AK-9.2): Desktop drei Knöpfe, Handy einer. */
export function ThemeToggle() {
  const { preference, setPreference } = useTheme();
  const current =
    OPTIONS.find((option) => option.value === preference) ?? OPTIONS[2];

  return (
    <>
      <div
        role="group"
        aria-label="Darstellung"
        className="hidden rounded-full border border-border p-0.5 sm:flex"
      >
        {OPTIONS.map(({ value, label, Icon }) => {
          const pressed = preference === value;
          return (
            <button
              key={value}
              type="button"
              aria-label={label}
              aria-pressed={pressed}
              title={label}
              onClick={() => setPreference(value)}
              className={
                "flex h-10 w-11 items-center justify-center rounded-full pointer-coarse:h-11 " +
                (pressed
                  ? "bg-primary text-on-primary"
                  : "text-muted hover:text-text")
              }
            >
              <Icon />
            </button>
          );
        })}
      </div>
      <button
        type="button"
        aria-label={`Darstellung: ${current.label}`}
        title={`Darstellung: ${current.label}`}
        onClick={() => setPreference(NEXT[preference])}
        className="flex size-11 items-center justify-center rounded-full border border-border text-text sm:hidden"
      >
        <current.Icon />
      </button>
    </>
  );
}
