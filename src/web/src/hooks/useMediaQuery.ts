import { useState, useEffect } from "react";

/**
 * Hook to detect if a media query matches.
 * @param query - Media query string (e.g., "(max-width: 1023px)")
 * @returns boolean indicating if the query matches
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    setMatches(media.matches);

    const listener = (e: MediaQueryListEvent) => setMatches(e.matches);
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, [query]);

  return matches;
}

/**
 * Hook to detect if the viewport is mobile-sized (< lg breakpoint).
 * Uses Tailwind's lg breakpoint (1024px) as the threshold.
 * @returns boolean indicating if viewport is mobile-sized
 */
export function useIsMobile(): boolean {
  return useMediaQuery("(max-width: 1023px)");
}
