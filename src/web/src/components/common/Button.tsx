import React from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "className"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

/**
 * Reusable button component with variant + size presets.
 * - Uses Tailwind utility classes and the custom theme colors (primary/secondary).
 * - Shows a small spinner when `loading` is true and disables interactions.
 */
export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  children,
  type = "button",
  ...rest
}) => {
  const base =
    "inline-flex items-center justify-center rounded-md font-medium transition focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed";
  const variantClass: Record<ButtonVariant, string> = {
    primary:
      "bg-primary text-white hover:brightness-95 focus:ring-primary border border-transparent",
    secondary:
      "bg-secondary text-white hover:brightness-110 focus:ring-secondary border border-transparent",
    ghost:
      "bg-transparent text-gray-900 hover:bg-gray-100 focus:ring-gray-300 border border-gray-300",
  };
  const sizeClass: Record<ButtonSize, string> = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2 text-sm",
    lg: "px-5 py-3 text-base",
  };

  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      className={[base, variantClass[variant], sizeClass[size]].join(" ")}
      disabled={isDisabled}
      aria-disabled={isDisabled}
      {...rest}
    >
      {loading && (
        <span
          aria-hidden="true"
          className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white/60 border-t-white"
        />
      )}
      <span className={loading ? "opacity-80" : undefined}>{children}</span>
    </button>
  );
};

export default Button;
