// Steuerbares window.matchMedia für jsdom (kennt es nicht): `systemTheme.setDark(true)` simuliert
// einen Wechsel der Systemeinstellung, auch im laufenden Betrieb (AK-9.1).

type Listener = (event: MediaQueryListEvent) => void;

const listeners = new Set<Listener>();
let dark = false;

export const systemTheme = {
  setDark(value: boolean) {
    dark = value;
    for (const listener of listeners)
      listener({ matches: value } as MediaQueryListEvent);
  },
  reset() {
    dark = false;
    listeners.clear();
  },
};

export function installMatchMedia() {
  window.matchMedia = (query: string) =>
    ({
      media: query,
      get matches() {
        return query.includes("prefers-color-scheme: dark") ? dark : false;
      },
      onchange: null,
      addEventListener: (_type: string, listener: Listener) => {
        if (query.includes("prefers-color-scheme")) listeners.add(listener);
      },
      removeEventListener: (_type: string, listener: Listener) =>
        listeners.delete(listener),
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}
