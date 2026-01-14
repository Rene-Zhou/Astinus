import "@testing-library/jest-dom";
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import cn from "./locales/cn.json";
import en from "./locales/en.json";

i18n.use(initReactI18next).init({
  lng: "cn",
  fallbackLng: "en",
  resources: {
    cn: { translation: cn },
    en: { translation: en },
  },
  interpolation: {
    escapeValue: false,
  },
});
