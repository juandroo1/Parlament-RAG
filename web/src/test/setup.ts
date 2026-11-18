import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import { installDialog } from "./dialog";
import { installMatchMedia, systemTheme } from "./matchMedia";

// Tests mit `@vitest-environment node` haben kein window.
const browser = typeof window !== "undefined";
if (browser) {
  installMatchMedia();
  installDialog();
}

// Ohne `globals` räumt Testing Library nicht selbst auf. Danach Speicher, Systemeinstellung und
// data-theme zurücksetzen, damit Tests einander nicht beeinflussen.
afterEach(() => {
  if (!browser) return;
  cleanup();
  window.localStorage.clear();
  systemTheme.reset();
  document.documentElement.removeAttribute("data-theme");
});
