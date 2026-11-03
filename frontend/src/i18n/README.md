# i18n architecture

The frontend supports three UI languages:

| Locale    | Language            | Notes                                      |
| --------- | ------------------- | ------------------------------------------ |
| `en`      | English (Hong Kong) | International staff/students               |
| `yue`     | 粵語 (Cantonese)     | Written Cantonese, Traditional characters  |
| `zh-Hans` | 简体中文             | Source language, also the safe default     |

## Layers

```
i18n/
  config.ts          locale catalogue, metadata, detection, storage helpers
  localeStore.ts     framework-agnostic store (get/set/subscribe + <html lang>)
  translate.ts       typed lookup, interpolation, fallback, missing-key warnings
  format.ts          Intl date/number formatting bound to a locale
  I18nProvider.tsx   React provider + useI18n() hook
  LanguageSelector   accessible header dropdown
  messages/
    <namespace>.ts   one file per product surface, all three locales together
    index.ts         aggregate + canonical English key shape
```

`main.tsx` calls `initLocale()` before the first render (stored choice → browser
language → `zh-Hans`). `<html lang>` is kept in sync on every change.

## Using copy in components

```tsx
import { useI18n } from "../../i18n";

function Example() {
  const { t, locale, formatDate } = useI18n();
  return <h1>{t("courses.list.title")}</h1>;
}
```

- Keys are **typed dot paths** derived from the English bundle; a typo fails `tsc`.
- Interpolation uses named braces: `t("courses.selected", { count: 3 })`.
- For English plural pairs add `key.one` / `key.other` and pick by `count`.
- For non-React helpers use `translate(key)` (active locale, not reactive) or
  accept a `Translator` argument with a default of `createTranslator(DEFAULT_LOCALE)`.
- Never translate data returned by the backend (course names, user names, room
  names, assignment titles). Only translate UI chrome, labels, help text,
  empty states, validation and error copy.

## Adding a message key

Keys live in one namespace file per surface, e.g. `messages/courses.ts`:

```ts
const en = { listTitle: "Courses" };            // canonical shape
export type CoursesMessages = typeof en;
const zhHans: CoursesMessages = { listTitle: "课程" };
const yue: CoursesMessages = { listTitle: "課程" };
export const courses = { en, "zh-Hans": zhHans, yue };
```

Add the key to `en` first, then mirror it in `zh-Hans` and `yue`; TypeScript
rejects a missing or extra key. New namespaces are registered once in
`messages/index.ts`.

## Adding a language

1. Add the locale code to `LOCALES` and a `LocaleMeta` entry in `config.ts`.
2. Add the locale to every namespace bundle (start by copying `en` and the type
   checker will guide you).
3. Register it in `messages/index.ts` and `MessageBundle`.
4. The language selector and persistence pick it up automatically.

## Conventions

- English: sentence case, HK spelling (`organise`, `colour` is not used here).
- Simplified Chinese: keep the existing copy byte-for-byte where it already
  exists (zero UX regression), full-width punctuation.
- Cantonese: Traditional characters + written Cantonese grammar/vocabulary
  (`係`, `唔`, `嘅`, `咗`, `喺`, `啲`, `冇`, `睇`, `揀`, `攞`, `俾`, `緊`), HK terms
  (`課室`, `檔案`, `影片`, `登入`, `儲存`, `搜尋`, `留言`, `發佈`).
- Keep brand/technical tokens untranslated: `HKU`, `The University of Hong Kong`,
  `PPT Agent`, `AI`, `Zoom`, `Panopto`, `Provider`, `Base URL`, `API Key`.
- Existing English eyebrow labels (`TEACHER WORKSPACE`, `TODAY`, `COURSE
  DISCUSSION`, …) stay English in every locale — they are design tokens.
- Accessibility text (`aria-label`, `title`, `alt`, placeholders) is copy too.

See [GLOSSARY.md](./GLOSSARY.md) for the shared terminology table.
