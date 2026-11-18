// axe-core in jsdom (AK-13.1). Farbkontraste kann jsdom nicht berechnen; die prüfen der Test der
// Design-Tokens (theme.test.ts) und Lighthouse im echten Browser.
import axe from "axe-core";
import { expect } from "vitest";

// axe misst Icons über <canvas>; jsdom hat keins und meldet das bei jedem Lauf. Ohne Canvas
// überspringt axe diese Prüfung.
HTMLCanvasElement.prototype.getContext = () => null;

export async function expectAccessible(
  context: Element | Document = document,
): Promise<void> {
  const results = await axe.run(context, {
    rules: { "color-contrast": { enabled: false } },
    resultTypes: ["violations"],
  });
  const violations = results.violations.map(
    (violation) =>
      `${violation.id} (${violation.impact}): ${violation.help}\n` +
      violation.nodes.map((node) => `  ${node.target.join(" ")}`).join("\n"),
  );
  expect(violations).toEqual([]);
}
