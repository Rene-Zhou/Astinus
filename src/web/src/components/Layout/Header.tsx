import React from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

export interface HeaderProps {
  rightSlot?: React.ReactNode;
}

export const Header: React.FC<HeaderProps> = ({ rightSlot }) => {
  const location = useLocation();
  const { t } = useTranslation();

  const navLinks = [
    { to: "/", label: t("nav.menu") },
    { to: "/character", label: t("nav.character") },
    { to: "/game", label: t("nav.game") },
    { to: "/settings", label: t("nav.settings") },
  ];

  return (
    <header className="sticky top-0 z-30 border-b border-gray-200 bg-white/95 backdrop-blur dark:border-gray-700 dark:bg-gray-800/95">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-lg font-semibold text-primary dark:text-primary-400">
          <span className="h-9 w-9 rounded-lg bg-primary/10 text-center text-xl leading-9 text-primary dark:bg-primary/20 dark:text-primary-300">
            A
          </span>
          <span>{t("app.title")}</span>
        </Link>

        <nav className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.to;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive: navActive }) =>
                  [
                    "rounded-md px-3 py-2 transition",
                    navActive || isActive
                      ? "bg-primary/10 text-primary dark:bg-primary/20 dark:text-primary-300"
                      : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700",
                  ].join(" ")
                }
              >
                {link.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">{rightSlot}</div>
      </div>
    </header>
  );
};

export interface FooterProps {
  leftText?: string;
  rightText?: string;
}

export const Footer: React.FC<FooterProps> = ({
  leftText,
  rightText = "参见 docs/WEB_FRONTEND_PLAN.md 获取路线图",
}) => {
  return (
    <footer className="border-t border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-3 text-sm text-gray-500 dark:text-gray-400 sm:flex-row sm:items-center sm:justify-between">
        <span>{leftText || "Astinus Web Frontend"}</span>
        <span className="text-xs sm:text-sm">{rightText}</span>
      </div>
    </footer>
  );
};

export interface LayoutProps {
  children: React.ReactNode;
  headerSlot?: React.ReactNode;
  footerSlot?: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children, headerSlot, footerSlot }) => {
  return (
    <div className="flex min-h-screen flex-col bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-gray-100">
      <Header rightSlot={headerSlot} />
      <main className="flex-1">{children}</main>
      <Footer rightText={typeof footerSlot === "string" ? footerSlot : undefined} />
    </div>
  );
};

export default Layout;
