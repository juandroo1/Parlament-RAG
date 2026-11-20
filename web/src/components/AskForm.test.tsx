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
  const toggle = screen.getByRole("button", { name: /^(Filter|Filtres)/ });
  const panel = screen.getByTestId("filter-panel");
  return { user, onSubmit, toggle, panel };
}

/** Der innere Bereich trägt «inert», solange die Filter zu sind. */
const content = (panel: HTMLElement) => panel.firstElementChild as HTMLElement;

describe("Filter (US-15)", () => {
  it("ist zugeklappt inert und klappt per Knopf auf und zu (AK-15.2)", async () => {
    const { user, toggle, panel } = setup();
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle).toHaveAttribute(
      "aria-controls",
      screen.getByRole("group", { name: "Filter", hidden: true }).id,
    );
    expect(content(panel)).toHaveAttribute("inert");
    expect(panel.className).toContain("grid-rows-[0fr]");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(content(panel)).not.toHaveAttribute("inert");
    expect(panel.className).toContain("grid-rows-[1fr]");
    expect(panel.className).toContain("transition-[grid-template-rows]");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(content(panel)).toHaveAttribute("inert");
  });

  it("nennt die Zahl der aktiven Filter im Knopf (AK-15.1)", async () => {
    const { user, toggle } = setup();
    expect(toggle).toHaveAccessibleName("Filter");

    await user.click(toggle);
    await user.selectOptions(screen.getByLabelText("Rat"), "NR");
    expect(toggle).toHaveAccessibleName("Filter (1 aktiv)");
    // Auf dem Handy sichtbar nur «(1)», damit der Knopf mit Pfeil einzeilig bleibt.
    const short = toggle.querySelector("span[aria-hidden='true']");
    expect(short).toHaveTextContent("(1)");
    expect(short).toHaveClass("sm:hidden");
    expect(toggle).toHaveClass("whitespace-nowrap");
    await user.selectOptions(screen.getByLabelText(/Fraktion/), "G");
    expect(toggle).toHaveAccessibleName("Filter (2 aktiv)");
    await user.selectOptions(screen.getByLabelText("Rat"), "");
    expect(toggle).toHaveAccessibleName("Filter (1 aktiv)");
  });

  it("nennt die aktiven Filter auch auf Französisch", async () => {
    const { user, toggle } = setup("fr-CH");
    await user.click(toggle);
    await user.selectOptions(screen.getByLabelText("Conseil"), "SR");
    expect(toggle).toHaveAccessibleName("Filtres (1 actif)");
  });

  it("steht neben «Fragen», mit Pfeil, und klappt darunter auf (AK-15.1, AK-15.3)", () => {
    const { toggle } = setup();
    const submit = screen.getByRole("button", { name: "Fragen" });
    expect(toggle.parentElement).toBe(submit.parentElement);
    // Der Filterbereich klappt unterhalb der Zeile mit Filter und «Fragen» auf.
    const fieldset = screen.getByRole("group", { name: "Filter", hidden: true });
    const after = Node.DOCUMENT_POSITION_FOLLOWING;
    expect(submit.compareDocumentPosition(fieldset) & after).toBeTruthy();
    // Handy eine Spalte, ab 640 px zwei.
    expect(fieldset.className).toMatch(/sm:grid-cols-2/);
    // Pfeil dreht beim Öffnen: Klasse am Wrapper des Symbols.
    expect(toggle.querySelector(".transition-transform")).not.toBeNull();
  });

  it("schickt die Filter mit, auch nach dem Zuklappen (AK-15.4)", async () => {
    const { user, toggle, onSubmit } = setup();
    await user.type(screen.getByLabelText(/Ihre Frage/), "Frage zur AHV?");
    await user.click(toggle);
    await user.selectOptions(screen.getByLabelText("Rat"), "SR");
    await user.click(toggle);
    await user.click(screen.getByRole("button", { name: "Fragen" }));
    expect(onSubmit).toHaveBeenCalledWith("Frage zur AHV?", { council: "SR" });
  });
});
