import { useEffect, useState, type RefObject } from "react";

/**
 * True while one of the landing page's dark stage sections ([data-stage] in main) is directly under the
 * header's bottom edge. The header then takes the stage color, so it does not sit as a cream bar over it.
 */
export function useHeaderOverStage(header: RefObject<HTMLElement | null>, active: boolean): boolean {
  const [over, setOver] = useState(false);
  useEffect(() => {
    setOver(false);
    const el = header.current;
    if (!active || el === null || typeof IntersectionObserver === "undefined") return;
    const stages = document.querySelectorAll("main [data-stage]");
    const under = new Set<Element>();
    let observer: IntersectionObserver | null = null;
    const watch = () => {
      observer?.disconnect();
      under.clear();
      const height = el.getBoundingClientRect().height;
      // A 1px line just under the header: the section crossing it is what the header sits on.
      observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) under.add(entry.target);
            else under.delete(entry.target);
          }
          setOver(under.size > 0);
        },
        { rootMargin: `-${height}px 0px -${Math.max(0, window.innerHeight - height - 1)}px 0px` },
      );
      stages.forEach((stage) => observer?.observe(stage));
    };
    watch();
    window.addEventListener("resize", watch);
    return () => {
      window.removeEventListener("resize", watch);
      observer?.disconnect();
    };
  }, [header, active]);
  return over;
}

/** True while the media query matches. */
export function useMediaQuery(query: string): boolean {
  const get = () => typeof window.matchMedia === "function" && window.matchMedia(query).matches;
  const [matches, setMatches] = useState(get);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia(query);
    const onChange = () => setMatches(media.matches);
    onChange();
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [query]);
  return matches;
}
