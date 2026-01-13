import React, { useRef, useLayoutEffect } from "react";

export interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  maxHeight?: string;
}

/**
 * Bottom sheet component for mobile layouts.
 * Slides up from the bottom with an overlay backdrop.
 * Click on the backdrop to close.
 */
export const BottomSheet: React.FC<BottomSheetProps> = ({
  isOpen,
  onClose,
  title,
  children,
  maxHeight = "70vh",
}) => {
  const overlayRef = useRef<HTMLDivElement>(null);
  const sheetRef = useRef<HTMLDivElement>(null);

  // Handle animation via refs to avoid setState in effects
  useLayoutEffect(() => {
    if (!overlayRef.current || !sheetRef.current) return;

    if (isOpen) {
      // Trigger animation on next frame
      requestAnimationFrame(() => {
        if (overlayRef.current) overlayRef.current.style.opacity = "1";
        if (sheetRef.current) sheetRef.current.style.transform = "translateY(0)";
      });
    } else {
      overlayRef.current.style.opacity = "0";
      sheetRef.current.style.transform = "translateY(100%)";
    }
  }, [isOpen]);

  // Note: Body scroll is managed by the parent page (e.g., GamePage)
  // to avoid conflicts when multiple components try to control body overflow.

  // Don't render if not open (no animation needed for initial state)
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        ref={overlayRef}
        className="absolute inset-0 bg-black/40 transition-opacity duration-300"
        style={{ opacity: 0 }}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sheet */}
      <div
        ref={sheetRef}
        className="absolute bottom-0 left-0 right-0 bg-white dark:bg-gray-800 rounded-t-2xl shadow-xl transition-transform duration-300 ease-out"
        style={{ maxHeight, transform: "translateY(100%)" }}
      >
        {/* Handle bar */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="h-1 w-10 rounded-full bg-gray-300 dark:bg-gray-600" />
        </div>

        {/* Header */}
        {title && (
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 px-4 pb-3">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
            <button
              onClick={onClose}
              className="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:text-gray-500 dark:hover:bg-gray-700 dark:hover:text-gray-300 transition-colors"
              aria-label="Close"
            >
              <svg
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        )}

        {/* Content */}
        <div className="overflow-y-auto p-4" style={{ maxHeight: `calc(${maxHeight} - 60px)` }}>
          {children}
        </div>
      </div>
    </div>
  );
};

export default BottomSheet;
