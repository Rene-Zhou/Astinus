import React, { useRef, useEffect, useState } from "react";

export interface CollapsiblePanelProps {
  title: string;
  icon?: React.ReactNode;
  isOpen: boolean;
  onToggle: () => void;
  badge?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}

/**
 * Collapsible panel component for mobile layouts.
 * Supports smooth expand/collapse animation and optional badge notification.
 */
export const CollapsiblePanel: React.FC<CollapsiblePanelProps> = ({
  title,
  icon,
  isOpen,
  onToggle,
  badge,
  className = "",
  children,
}) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState<number>(0);

  useEffect(() => {
    if (contentRef.current) {
      setContentHeight(contentRef.current.scrollHeight);
    }
  }, [children]);

  return (
    <div
      className={[
        "rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {/* Header - Always visible */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 text-left text-sm font-semibold text-gray-900 hover:bg-gray-50 transition-colors"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          {icon}
          <span>{title}</span>
          {badge}
        </div>
        <svg
          className={[
            "h-5 w-5 text-gray-500 transition-transform duration-200",
            isOpen ? "rotate-180" : "",
          ].join(" ")}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Content - Collapsible */}
      <div
        style={{ maxHeight: isOpen ? contentHeight : 0 }}
        className="transition-[max-height] duration-300 ease-in-out overflow-hidden"
      >
        <div ref={contentRef} className="px-4 pb-4">
          {children}
        </div>
      </div>
    </div>
  );
};

export default CollapsiblePanel;
