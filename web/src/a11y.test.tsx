// Barrierefreiheit (Spec 002, US-13): axe ohne Verstösse in allen Zuständen, Tastatur, Fokus und
// weniger Bewegung.
import { readFileSync } from "node:fs";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AskResponse } from "./api";
import App from "./App";
import { expectAccessible } from "./test/axe";
import { SPEECH } from "./test/fixtures";

const ANSWERED: AskResponse = {
  answer: "Rösti betonte den Winterstrom [1]. Unbekannt [7].",
  insufficient_context: false,
  insufficient_reason: null,
  sources: [SPEECH],
  usage: {
    model: "claude-haiku-5-5",
    backend: "api",
    input_tokens: 9100,
    output_tokens: 1300,
    cost_usd: 0.0016,
    cost_estimated: false,
    latency_ms: 6040,
  },
};
const INSUFFICIENT: AskResponse = {
  ...ANSWERED,
  answer: "Zu dieser Frage habe ich keine ausreichende Grundlage gefunden.",
  insufficient_context: true,
  insufficient_reason: "low_similarity",
  sources: [],
};

function respond(
  status: number,
  body: unknown,
  headers: Record<string, string> = {},
) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status < 300,
      status,
      headers: new Headers(headers),
      json: () => Promise.resolve(body),
    }),
  );
}

async function ask(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByRole("textbox"), "Was sagte Bundesrat Rösti?");
  await user.click(screen.getByRole("button", { name: /^(Fragen|Demander)$/ }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe.each(["de-CH", "fr-CH"])(
  "axe ohne Verstösse (%s, AK-13.1)",
  (language) => {
    const setup = () => {
      vi.spyOn(navigator, "languages", "get").mockReturnValue([language]);
      const user = userEvent.setup();
      render(<App />);
      return user;
    };

    it("Startseite mit offenen Filtern", async () => {
      const user = setup();
      await expectAccessible();
      await user.click(
        screen.getByRole("button", { name: /^(Filter|Filtres)/ }),
      );
      await expectAccessible();
    });

    it("Antwort mit Quellen", async () => {
      respond(200, ANSWERED);
      const user = setup();
      await ask(user);
      await screen.findByRole("link", { name: /^(Quelle|Source) 1$/ });
      await expectAccessible();
    });

    it("keine ausreichende Grundlage", async () => {
      respond(200, INSUFFICIENT);
      const user = setup();
      await ask(user);
      await screen.findByText(/keine ausreichende Grundlage gefunden/);
      await expectAccessible();
    });

    it("Fehler der API", async () => {
      respond(
        429,
        { detail: "Zu viele Fragen" },
        { "X-Error-Code": "rate_limit", "Retry-After": "600" },
      );
      const user = setup();
      await ask(user);
      await screen.findByRole("alert");
      await expectAccessible();
    });

    it("offener Dialog «So funktioniert's»", async () => {
      const user = setup();
      await user.click(
        screen.getByRole("button", {
          name: /^(So funktioniert's|Comment ça marche)$/,
        }),
      );
      await expectAccessible(screen.getByRole("dialog"));
    });
  },
);

describe("Tastatur (AK-13.2)", () => {
  it("erreicht alle Bedienelemente in sinnvoller Reihenfolge", async () => {
    const user = userEvent.setup();
    render(<App />);
    const order: string[] = [];
    for (let i = 0; i < 14; i++) {
      await user.tab();
      const element = document.activeElement as HTMLElement;
      order.push(
        element.getAttribute("aria-label") ??
          element.querySelector("img")?.getAttribute("alt") ??
          (element.tagName === "TEXTAREA"
            ? "Fragefeld"
            : (element.textContent?.trim().slice(0, 18) ?? "")),
      );
    }
    // Desktop- und Handy-Variante des Darstellungs-Umschalters liegen beide im DOM (CSS blendet eine aus).
    expect(order.slice(0, 10)).toEqual([
      "Frag das Parlament",
      "So funktioniert's",
      "Deutsch",
      "Français",
      "Hell",
      "Dunkel",
      "Wie System",
      "Darstellung: Wie System",
      "Fragefeld",
      "Was sagte Bundesra", // erste Beispielfrage
    ]);
    expect(order).toContain("Filter");
  });

  it("zeigt den Fokus sichtbar an", () => {
    const css = readFileSync(`${process.cwd()}/src/theme.css`, "utf-8");
    expect(css).toMatch(
      /:focus-visible\s*\{\s*outline:\s*3px solid var\(--fdp-accent\)/,
    );
  });
});

describe("Weniger Bewegung (AK-13.3)", () => {
  it("schaltet Animationen und Übergänge bei prefers-reduced-motion ab", () => {
    const css = readFileSync(`${process.cwd()}/src/theme.css`, "utf-8");
    const block = css.slice(
      css.indexOf("@media (prefers-reduced-motion: reduce)"),
    );
    expect(block).toMatch(/animation-duration:\s*0\.01ms !important/);
    expect(block).toMatch(/transition-duration:\s*0\.01ms !important/);
    expect(block).toMatch(/scroll-behavior:\s*auto !important/);
  });
});
