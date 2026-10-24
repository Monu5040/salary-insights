import "@testing-library/jest-dom/vitest";
import { cleanup, configure } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// findBy… waits up to 3 s rather than 1 s, for the same reason as testTimeout in vite.config.ts.
configure({ asyncUtilTimeout: 3000 });

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// Ant Design's responsive helpers read matchMedia, which jsdom doesn't implement.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Ant Design measures scrollbars through a pseudo-element, which jsdom can't style; it would
// log "Not implemented" on every table and select.
const getComputedStyle = window.getComputedStyle.bind(window);
window.getComputedStyle = (element: Element) => getComputedStyle(element);

// jsdom doesn't lay pages out, so it has no scrollIntoView; "Open in the explorer" calls it.
Element.prototype.scrollIntoView = () => {};
