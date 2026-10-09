"use client";

import { useEffect, useState } from "react";
import { useReducedMotion } from "./useReducedMotion";

interface CountUpOptions {
  end: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
  decimals?: number;
  delay?: number;
  startWhen?: boolean;
}

export function useCountUp(options: CountUpOptions): string {
  const {
    end,
    duration = 800,
    suffix = "",
    prefix = "",
    decimals = 0,
    delay = 0,
    startWhen = true,
  } = options;

  const reducedMotion = useReducedMotion();
  const [value, setValue] = useState<number>(startWhen && !reducedMotion ? 0 : end);

  useEffect(() => {
    if (!startWhen) return;

    if (reducedMotion) {
      setValue(end);
      return;
    }

    let animationFrameId: number;
    let startTimestamp: number | null = null;

    const timeoutId = setTimeout(() => {
      const step = (timestamp: number) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        
        // easeOutCubic
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        const currentValue = easeProgress * end;

        setValue(currentValue);

        if (progress < 1) {
          animationFrameId = requestAnimationFrame(step);
        } else {
          setValue(end);
        }
      };

      animationFrameId = requestAnimationFrame(step);
    }, delay);

    return () => {
      clearTimeout(timeoutId);
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
    };
  }, [end, duration, delay, startWhen, reducedMotion]);

  const formattedNumber = value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  return `${prefix}${formattedNumber}${suffix}`;
}
