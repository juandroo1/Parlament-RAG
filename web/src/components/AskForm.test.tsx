import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LanguageProvider } from "../i18n/LanguageProvider";
import { AskForm } from "./AskForm";

function setup(language = "de-CH") {
  vi.spyOn(navigator, "languages", "get").mockReturnValue([language]);
  const onSubmit = vi.fn();
  const user = userEvent.setup();
  render(
    <LanguageProvider>
      <AskForm loading={false} onSubmit={onSubmit} />
    </LanguageProvider>,
  );
  const pill = screen.getByRole("button", { name: /^(Filter|Filtres)/ });
  const panel = screen.getByTestId("filter-panel");
  return { user, onSubmit, pill, panel };
}

/** Der innere Bereich trägt «inert», solange die Filter zu sind. */
const content = (panel: HTMLElement) => panel.firstElementChild as HTMLElement;

describe("Filter nach Entwurf B (US-15)", () => {
  it("ist zugeklappt inert und klappt per Pille auf und zu (AK-15.2)", async () => {
    const { user, pill, panel } = setup();
    expect(pill).toHaveAttribute("aria-expanded", "false");
    expect(pill).toHaveAttribute(
      "aria-controls",
      screen.getByRole("group", { name: "Filter", hidden: true }).id,
    );
    expect(content(panel)).toHaveAttribute("inert");
    expect(panel.className).toContain("grid-rows-[0fr]");

    await user.click(pill);
    expect(pill).toHaveAttribute("aria-expanded", "true");
    expect(content(panel)).not.toHaveAttribute("inert");
    expect(panel.className).toContain("grid-rows-[1fr]");
    expect(panel.className).toContain("transition-[grid-template-rows]");

    await user.click(pill);
    expect(pill).toHaveAttribute("aria-expanded", "false");
    expect(content(panel)).toHaveAttribute("inert");
  });

  it("zeigt die Zahl der aktiven Filter auf der Pille (AK-15.1)", async () => {
    const { user, pill } = setup();
    expect(pill).toHaveAccessibleName("Filter");

    await user.click(pill);
    await user.selectOptions(screen.getByLabelText("Rat"), "NR");
    expect(pill).toHaveAccessibleName("Filter, 1 aktiv");
    await user.selectOptions(screen.getByLabelText(/Fraktion/), "G");
    expect(pill).toHaveAccessibleName("Filter, 2 aktiv");
    // Die Zahl ist sichtbar, für Screenreader zählt der Text «2 aktiv».
    expect(pill.querySelector("span[aria-hidden='true']")?.textContent).toBe("2");

    await user.selectOptions(screen.getByLabelText("Rat"), "");
    expect(pill).toHaveAccessibleName("Filter, 1 aktiv");
  });

  it("nennt die aktiven Filter auch auf Französisch", async () => {
    const { user, pill } = setup("fr-CH");
    await user.click(pill);
    await user.selectOptions(screen.getByLabelText("Conseil"), "SR");
    expect(pill).toHaveAccessibleName("Filtres, 1 actif");
  });

  it("steht zwischen Beispielen und «Fragen», mit vier Spalten ab Tablet-Breite (AK-15.1, AK-15.3)", () => {
    const { pill } = setup();
    const examples = screen.getAllByRole("button", { name: /Bundesrat/ });
    const submit = screen.getByRole("button", { name: "Fragen" });
    const after = Node.DOCUMENT_POSITION_FOLLOWING;
    expect(examples.at(-1)!.compareDocumentPosition(pill) & after).toBeTruthy();
    expect(pill.compareDocumentPosition(submit) & after).toBeTruthy();
    // Pille und Beispiele teilen sich einen Container (Pille neben «Beispiele:»).
    expect(pill.parentElement).toBe(examples[0].closest("ul")!.parentElement);
    // Handy eine Spalte, ab 640 px zwei, ab 768 px vier.
    const fieldset = screen.getByRole("group", { name: "Filter", hidden: true });
    expect(fieldset.className).toMatch(/sm:grid-cols-2/);
    expect(fieldset.className).toMatch(/md:grid-cols-\[(minmax[^\]]*){4}\]/);
    // Pfeil dreht beim Öffnen: Klasse am Wrapper des Symbols.
    expect(pill.querySelector(".transition-transform")).not.toBeNull();
  });

  it("schickt die Filter mit, auch nach dem Zuklappen (AK-15.4)", async () => {
    const { user, pill, onSubmit } = setup();
    await user.type(screen.getByLabelText(/Ihre Frage/), "Frage zur AHV?");
    await user.click(pill);
    await user.selectOptions(screen.getByLabelText("Rat"), "SR");
    await user.click(pill);
    await user.click(screen.getByRole("button", { name: "Fragen" }));
    expect(onSubmit).toHaveBeenCalledWith("Frage zur AHV?", { council: "SR" });
  });
});
