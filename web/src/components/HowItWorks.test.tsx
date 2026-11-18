import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";

afterEach(() => vi.restoreAllMocks());

function openDialog() {
  const user = userEvent.setup();
  render(<App />);
  return user;
}

describe("So funktioniert's", () => {
  it("öffnet mit Titel, fünf Abschnitten und Links (AK-12.1)", async () => {
    const user = openDialog();
    const button = within(screen.getByRole("banner")).getByRole("button", {
      name: "So funktioniert's",
    });
    expect(button).toHaveAttribute("aria-haspopup", "dialog");

    await user.click(button);
    const dialog = screen.getByRole("dialog", { name: "So funktioniert's" });
    expect(dialog).toHaveAttribute("open");
    const sections = within(dialog)
      .getAllByRole("heading", { level: 3 })
      .map((h) => h.textContent);
    expect(sections).toEqual([
      "Was die Seite macht",
      "Woher die Daten stammen",
      "Wie eine Antwort entsteht",
      "Grenzen",
      "Datenschutz und Grenzen der Demo",
    ]);
    expect(
      within(dialog).getByText(/Sessionen von Dezember 2023 bis Oktober 2026/),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(/Massgebend ist immer die Originalstelle/),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(/Ihre Fragen werden nicht gespeichert/),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByRole("link", { name: "Code auf GitHub" }),
    ).toHaveAttribute("href", "https://github.com/juandroo1/Parlament-RAG");
    expect(
      within(dialog).getByRole("link", { name: "Eval-Ergebnisse" }),
    ).toHaveAttribute(
      "href",
      "https://github.com/juandroo1/Parlament-RAG#ergebnisse",
    );
  });

  it("schliesst mit Esc und gibt den Fokus an den Knopf zurück (AK-12.2)", async () => {
    const user = openDialog();
    const button = screen.getByRole("button", { name: "So funktioniert's" });
    await user.click(button);
    const dialog = screen.getByRole("dialog");
    expect(
      within(dialog).getByRole("button", { name: "Schliessen" }),
    ).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(dialog).not.toHaveAttribute("open");
    expect(button).toHaveFocus();
  });

  it("schliesst mit dem Knopf und per Klick auf den Hintergrund", async () => {
    const user = openDialog();
    const button = screen.getByRole("button", { name: "So funktioniert's" });
    await user.click(button);
    await user.click(screen.getByRole("button", { name: "Schliessen" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(button).toHaveFocus();

    await user.click(button);
    const dialog = screen.getByRole("dialog");
    await user.click(dialog); // Ziel ist das <dialog> selbst: der Hintergrund
    expect(dialog).not.toHaveAttribute("open");
    // Ein Klick in den Inhalt schliesst nicht.
    await user.click(button);
    await user.click(within(screen.getByRole("dialog")).getByText("Grenzen"));
    expect(screen.getByRole("dialog")).toHaveAttribute("open");
  });

  it("zeigt den Inhalt auf Französisch (AK-12.3)", async () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["fr-CH"]);
    const user = openDialog();
    await user.click(screen.getByRole("button", { name: "Comment ça marche" }));
    const dialog = screen.getByRole("dialog", { name: "Comment ça marche" });
    expect(
      within(dialog).getByRole("heading", { name: "Limites" }),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(/Vos questions ne sont pas enregistrées/),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByRole("link", { name: "Résultats des évaluations" }),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByRole("button", { name: "Fermer" }),
    ).toBeInTheDocument();
  });
});
