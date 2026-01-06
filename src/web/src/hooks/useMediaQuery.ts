import { useSyncExternalStore, useCallback } from "react";

/**
 * Hook to detect if a media query matches.
 * @param query - Media query string (e.g., "(max-width: 1023px)")
 * @returns boolean indicating if the query matches
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (callback: () => void) => {
      const media = window.matchMedia(query);
      media.addEventListener("change", callback);
      return () => media.removeEventListener("change", callback);
    },
    [query],
  );

  const getSnapshot = useCallback(() => {
    return window.matchMedia(query).matches;
  }, [query]);

  const getServerSnapshot = useCallback(() => false, []);

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/**
 * Hook to detect if the viewport is mobile-sized (< lg breakpoint).
 * Uses Tailwind's lg breakpoint (1024px) as the threshold.
 * @returns boolean indicating if viewport is mobile-sized
 */
export function useIsMobile(): boolean {
  return useMediaQuery("(max-width: 1023px)");
}
