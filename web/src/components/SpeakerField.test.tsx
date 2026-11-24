// Feld «Person» (Spec 003, AK-18.1): Vorschläge, Tastatur, Auswahl, nur Namen aus der Liste.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LanguageProvider } from "../i18n/LanguageProvider";
import { SPEAKERS, apiMock } from "../test/fixtures";
import { SpeakerField, suggest } from "./SpeakerField";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function setup(initial?: string, language = "de-CH") {
  vi.spyOn(navigator, "languages", "get").mockReturnValue([language]);
  const fetchMock = apiMock();
  vi.stubGlobal("fetch", fetchMock);
  const changes: (string | undefined)[] = [];
  function Harness() {
    const [value, setValue] = useState(initial);
    return (
      <LanguageProvider>
        <SpeakerField
          className="field"
          value={value}
          onChange={(name) => {
            changes.push(name);
            setValue(name);
          }}
        />
        <button type="button">weiter</button>
      </LanguageProvider>
    );
  }
  render(<Harness />);
  const input = screen.getByRole("combobox", { name: /Person/ });
  return { user: userEvent.setup(), input, changes, fetchMock };
}

describe("SpeakerField", () => {
  it("lädt die Personen beim ersten Fokus, einmal", async () => {
    const { user, input, fetchMock } = setup();
    expect(fetchMock).not.toHaveBeenCalled();
    await user.click(input);
    await user.type(input, "mül");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/speakers");
  });

  it("schlägt passende Personen vor und wählt per Tastatur", async () => {
    const { user, input, changes } = setup();
    await user.type(input, "mül");
    const options = await screen.findAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual([
      "Müller Damian (RL, LU)",
      "Müller Leo (M-E, LU)",
    ]);
    expect(input).toHaveAttribute("aria-expanded", "true");
    expect(input).toHaveAttribute("aria-activedescendant", options[0].id);
    expect(options[0]).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{ArrowDown}");
    expect(input).toHaveAttribute("aria-activedescendant", options[1].id);
    await user.keyboard("{Enter}");
    expect(changes).toEqual(["Müller Leo"]);
    expect(input).toHaveValue("Müller Leo");
    expect(input).toHaveAttribute("aria-expanded", "false");
  });

  it("findet Namen ohne Akzente und Bundesratsmitglieder", async () => {
    const { user, input } = setup(undefined, "fr-CH");
    await user.type(input, "rosti");
    expect(await screen.findByRole("option")).toHaveTextContent(
      "Rösti Albert (Conseil fédéral)",
    );
  });

  it("schliesst mit Esc und verwirft freien Text beim Verlassen", async () => {
    const { user, input, changes } = setup();
    await user.type(input, "mül");
    await screen.findAllByRole("option");
    await user.keyboard("{Escape}");
    expect(input).toHaveAttribute("aria-expanded", "false");
    await user.click(screen.getByRole("button", { name: "weiter" }));
    expect(input).toHaveValue("");
    expect(changes).toEqual([]);
  });

  it("übernimmt einen genau getippten Namen und meldet fehlende Treffer", async () => {
    const { user, input, changes } = setup();
    await user.type(input, "xyz");
    expect(
      await screen.findByText("Keine passende Person mit Voten."),
    ).toBeInTheDocument();
    await user.clear(input);
    await user.type(input, "funiciello tamara");
    await user.click(screen.getByRole("button", { name: "weiter" }));
    expect(changes).toEqual(["Funiciello Tamara"]);
  });

  it("wählt per Maus und lässt sich wieder leeren", async () => {
    const { user, input, changes } = setup();
    await user.type(input, "schn");
    await user.click(
      await screen.findByRole("option", { name: /Schneider Meret/ }),
    );
    expect(changes).toEqual(["Schneider Meret"]);
    await user.click(screen.getByRole("button", { name: "Person entfernen" }));
    expect(changes).toEqual(["Schneider Meret", undefined]);
    expect(input).toHaveValue("");
  });

  it("zeigt einen Fehler, wenn die Liste nicht lädt", async () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["de-CH"]);
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue({
          ok: false,
          status: 503,
          json: () => Promise.resolve({}),
        }),
    );
    render(
      <LanguageProvider>
        <SpeakerField className="field" onChange={() => {}} />
      </LanguageProvider>,
    );
    const user = userEvent.setup();
    await user.type(screen.getByRole("combobox"), "mü");
    await waitFor(() =>
      expect(
        screen.getByText("Die Personen konnten nicht geladen werden."),
      ).toBeInTheDocument(),
    );
  });
});

describe("suggest", () => {
  it("bringt Treffer am Wortanfang nach vorne", () => {
    expect(suggest(SPEAKERS, "sch").map((s) => s.name)).toEqual([
      "Schneider Meret",
      "Aebischer Matthias",
    ]);
    expect(suggest(SPEAKERS, "  ")).toEqual([]);
    expect(suggest(SPEAKERS, "müller leo").map((s) => s.name)).toEqual([
      "Müller Leo",
    ]);
  });
});
