import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { STORAGE_KEY } from "../theme/preference";
import { systemTheme } from "../test/matchMedia";
import { ThemeToggle } from "./ThemeToggle";

const html = () => document.documentElement;

describe("ThemeToggle", () => {
  it("folgt ohne Wahl dem System, auch bei einem Wechsel im Betrieb (AK-9.1)", () => {
    render(<ThemeToggle />);
    expect(html().dataset.theme).toBe("light");
    const group = screen.getByRole("group", { name: "Darstellung" });
    expect(
      within(group).getByRole("button", { name: "Wie System" }),
    ).toHaveAttribute("aria-pressed", "true");
    act(() => systemTheme.setDark(true));
    expect(html().dataset.theme).toBe("dark");
  });

  it("setzt und speichert die Wahl am Desktop (AK-9.2)", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    const group = screen.getByRole("group", { name: "Darstellung" });

    await user.click(within(group).getByRole("button", { name: "Dunkel" }));
    expect(html().dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("dark");
    expect(
      within(group).getByRole("button", { name: "Dunkel" }),
    ).toHaveAttribute("aria-pressed", "true");

    // Eine feste Wahl überstimmt das System.
    act(() => systemTheme.setDark(false));
    expect(html().dataset.theme).toBe("dark");

    await user.click(within(group).getByRole("button", { name: "Hell" }));
    expect(html().dataset.theme).toBe("light");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("light");
  });

  it("übernimmt die gespeicherte Wahl beim Laden", () => {
    window.localStorage.setItem(STORAGE_KEY, "dark");
    render(<ThemeToggle />);
    expect(html().dataset.theme).toBe("dark");
    expect(
      screen.getByRole("button", { name: "Darstellung: Dunkel" }),
    ).toBeInTheDocument();
  });

  it("schaltet auf dem Handy mit einem Knopf durch: System, Hell, Dunkel", async () => {
    const user = userEvent.setup();
    act(() => systemTheme.setDark(true));
    render(<ThemeToggle />);

    await user.click(
      screen.getByRole("button", { name: "Darstellung: Wie System" }),
    );
    expect(html().dataset.theme).toBe("light");
    await user.click(screen.getByRole("button", { name: "Darstellung: Hell" }));
    expect(html().dataset.theme).toBe("dark");
    await user.click(
      screen.getByRole("button", { name: "Darstellung: Dunkel" }),
    );
    expect(
      screen.getByRole("button", { name: "Darstellung: Wie System" }),
    ).toBeInTheDocument();
    expect(html().dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});
