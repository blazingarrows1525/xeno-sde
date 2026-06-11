"use client";

import { useEffect, useRef, useState } from "react";

const prefersReduced = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Animates a number from 0 → `to` once on mount (and whenever `to` changes). */
export function CountUp({
  to,
  duration = 900,
  format = (n) => Math.round(n).toLocaleString("en-IN"),
}: {
  to: number;
  duration?: number;
  format?: (n: number) => string;
}) {
  const [val, setVal] = useState(prefersReduced() ? to : 0);
  const raf = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (prefersReduced()) {
      setVal(to);
      return;
    }
    let cancelled = false;
    const start = performance.now();
    const ease = (t: number) => 1 - Math.pow(1 - t, 3);
    const tick = (now: number) => {
      if (cancelled) return;
      const t = Math.min(1, (now - start) / duration);
      setVal(to * ease(t));
      if (t < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    // Guarantee the final value even where rAF is throttled (background/offscreen tabs).
    const safety = setTimeout(() => {
      if (!cancelled) setVal(to);
    }, duration + 150);
    return () => {
      cancelled = true;
      if (raf.current) cancelAnimationFrame(raf.current);
      clearTimeout(safety);
    };
  }, [to, duration]);

  return <>{format(val)}</>;
}
