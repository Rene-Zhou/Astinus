import React from "react";

export interface CardProps {
  title?: string;
  className?: string;
  children: React.ReactNode;
}

/**
 * Basic Card container with optional header.
 */
export const Card: React.FC<CardProps> = ({ title, className = "", children }) => {
  return (
    <div
      className={[
        "rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {title && (
        <div className="border-b border-gray-200 px-4 py-3 text-sm font-semibold text-gray-900 dark:border-gray-700 dark:text-gray-100">
          {title}
        </div>
      )}
      <div className="px-4 py-3 text-gray-800 dark:text-gray-200">{children}</div>
    </div>
  );
};

export interface LoadingProps {
  size?: "sm" | "md" | "lg";
  text?: string;
  className?: string;
}

/**
 * Loading indicator with optional descriptive text.
 */
export const Loading: React.FC<LoadingProps> = ({
  size = "md",
  text,
  className = "",
}) => {
  const sizeClass =
    size === "sm"
      ? "h-4 w-4"
      : size === "lg"
        ? "h-8 w-8"
        : "h-6 w-6";

  return (
    <div
      className={[
        "flex items-center gap-2 text-gray-600 dark:text-gray-300",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      role="status"
      aria-live="polite"
      aria-label={text}
    >
      <span
        className={[
          "animate-spin rounded-full border-2 border-gray-300 border-t-primary dark:border-gray-600 dark:border-t-primary-400",
          sizeClass,
        ].join(" ")}
      />
      {text && <span className="text-sm">{text}</span>}
    </div>
  );
};

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

/**
 * Accessible Modal dialog with overlay.
 */
export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  className = "",
}) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
    >
      <div
        className={[
          "w-full max-w-lg rounded-lg bg-white shadow-xl dark:bg-gray-800 dark:border dark:border-gray-700",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-gray-200 px-5 py-4 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
          <button
            type="button"
            aria-label="Close dialog"
            onClick={onClose}
            className="rounded-full p-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200"
          >
            ×
          </button>
        </header>

        <div className="px-5 py-4 text-gray-800 dark:text-gray-200">{children}</div>

        {footer && (
          <footer className="border-t border-gray-200 px-5 py-4 dark:border-gray-700">{footer}</footer>
        )}
      </div>
    </div>
  );
};

export default Card;
