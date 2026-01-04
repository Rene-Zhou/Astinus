import type { Language, LocalizedString } from "../api/types";

export const DEFAULT_LANGUAGE: Language = "cn";
export const FALLBACK_LANGUAGE: Language = "cn";

export type LocalizedInput = LocalizedString | string | null | undefined;

const ensureLanguage = (lang?: string): Language => (lang === "en" ? "en" : "cn");

const isLocalizedString = (value: LocalizedInput): value is LocalizedString =>
  typeof value === "object" && value !== null && "cn" in value && "en" in value;

export function getLocalized(
  value: LocalizedInput,
  lang: Language = DEFAULT_LANGUAGE,
  fallback: Language = FALLBACK_LANGUAGE,
): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (!isLocalizedString(value)) return String(value);

  const primary = value[lang];
  if (primary && primary.trim().length > 0) return primary;

  const fb = value[fallback];
  if (fb && fb.trim().length > 0) return fb;

  const other = lang === "en" ? value.cn : value.en;
  return other ?? "";
}

export function makeTranslator(options?: {
  lang?: string;
  fallback?: string;
}): (value: LocalizedInput) => string {
  const lang = ensureLanguage(options?.lang);
  const fallback = ensureLanguage(options?.fallback ?? FALLBACK_LANGUAGE);
  return (value: LocalizedInput) => getLocalized(value, lang, fallback);
}

export function mergeLocalized(
  base: LocalizedString,
  override?: Partial<LocalizedString>,
): LocalizedString {
  if (!override) return base;
  return {
    cn: override.cn ?? base.cn,
    en: override.en ?? base.en,
  };
}

export function isLanguage(value: unknown): value is Language {
  return value === "cn" || value === "en";
}

export function normalizeLanguage(value?: string | null): Language {
  return ensureLanguage(value ?? DEFAULT_LANGUAGE);
}

export function withDefault<T>(value: T | null | undefined, defaultValue: T): T {
  return value === null || value === undefined ? defaultValue : value;
}

export default {
  DEFAULT_LANGUAGE,
  FALLBACK_LANGUAGE,
  getLocalized,
  makeTranslator,
  mergeLocalized,
  isLanguage,
  normalizeLanguage,
  withDefault,
};
