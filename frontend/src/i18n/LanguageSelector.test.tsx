import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import LanguageSelector from "./LanguageSelector";
import { I18nProvider } from "./I18nProvider";
import { DEFAULT_LOCALE, LOCALE_STORAGE_KEY, getLocale, setLocale } from "./index";

// React 18 requires this flag to silence the "not wrapped in act" warning.
(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  setLocale(DEFAULT_LOCALE, { persist: false });
  window.localStorage.clear();
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  window.localStorage.clear();
  setLocale(DEFAULT_LOCALE, { persist: false });
});

function render(): void {
  act(() => {
    root.render(<I18nProvider><LanguageSelector /></I18nProvider>);
  });
}

const trigger = () => container.querySelector<HTMLButtonElement>(".language-trigger");
const menu = () => container.querySelector<HTMLElement>(".language-menu");
const options = () => Array.from(container.querySelectorAll<HTMLButtonElement>(".language-option"));

function click(element: Element): void {
  act(() => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

function press(key: string, target: Element = trigger()!): void {
  act(() => {
    target.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
  });
}

describe("LanguageSelector", () => {
  it("shows the active language and lists all supported languages", () => {
    render();
    expect(trigger()?.textContent).toContain("简体中文");
    expect(trigger()?.getAttribute("aria-expanded")).toBe("false");

    click(trigger()!);

    expect(trigger()?.getAttribute("aria-expanded")).toBe("true");
    expect(trigger()?.getAttribute("aria-haspopup")).toBe("menu");
    expect(menu()).not.toBeNull();
    expect(options().map((option) => option.querySelector(".language-option-label")?.textContent)).toEqual([
      "English",
      "粵語",
      "简体中文",
    ]);
    const selected = options().filter((option) => option.getAttribute("aria-checked") === "true");
    expect(selected).toHaveLength(1);
    expect(selected[0].textContent).toContain("简体中文");
  });

  it("switches language, closes the menu and persists the choice", () => {
    render();
    click(trigger()!);
    click(options()[0]);

    expect(trigger()?.textContent).toContain("English");
    expect(getLocale()).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("en");
    expect(menu()).toBeNull();
  });

  it("starts from a previously selected language", () => {
    setLocale("yue", { persist: false });
    render();
    expect(trigger()?.textContent).toContain("粵語");
    expect(document.documentElement.lang).toBe("yue");
  });

  it("closes on Escape and returns focus to the trigger", () => {
    render();
    click(trigger()!);
    press("Escape", options()[0]);
    expect(menu()).toBeNull();
    expect(document.activeElement).toBe(trigger());
  });

  it("closes when the pointer goes outside", () => {
    render();
    click(trigger()!);
    act(() => {
      document.body.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    });
    expect(menu()).toBeNull();
  });

  it("supports arrow-key navigation and Home/End", () => {
    render();
    click(trigger()!);
    // The checked option receives focus when the menu opens.
    expect(document.activeElement).toBe(options()[2]);

    press("ArrowDown", document.activeElement!);
    expect(document.activeElement).toBe(options()[0]);

    press("End", document.activeElement!);
    expect(document.activeElement).toBe(options()[2]);

    press("Home", document.activeElement!);
    expect(document.activeElement).toBe(options()[0]);
  });
});
