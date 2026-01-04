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
        "rounded-lg border border-gray-200 bg-white shadow-sm",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {title && (
        <div className="border-b border-gray-200 px-4 py-3 text-sm font-semibold text-gray-900">
          {title}
        </div>
      )}
      <div className="px-4 py-3 text-gray-800">{children}</div>
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
  text = "Loading...",
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
        "flex items-center gap-2 text-gray-600",
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
          "animate-spin rounded-full border-2 border-gray-300 border-t-primary",
          sizeClass,
        ].join(" ")}
      />
      <span className="text-sm">{text}</span>
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
    >
      <div
        className={[
          "w-full max-w-lg rounded-lg bg-white shadow-xl",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <button
            type="button"
            aria-label="Close dialog"
            onClick={onClose}
            className="rounded-full p-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800"
          >
            ×
          </button>
        </header>

        <div className="px-5 py-4 text-gray-800">{children}</div>

        {footer && (
          <footer className="border-t border-gray-200 px-5 py-4">{footer}</footer>
        )}
      </div>
    </div>
  );
};

export default Card;
