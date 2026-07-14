"use client";

/**
 * components/NumberField.tsx — the one input the whole product hangs off.
 *
 * The field has to do two things at once: track the world (the number counts up on
 * its own while the chapter sweeps) and belong to the user the moment they type.
 *
 * DERIVED, NOT SYNCED. `draft` is null until the user touches the field, and while
 * it is null the input simply renders the live value. Typing takes ownership;
 * committing hands it back. The obvious alternative — holding a draft in state and
 * useEffect-ing it back in sync with the prop — is a cascading-render bug waiting
 * to happen (and React's own lint rule says so). There is no effect here at all.
 */

import { useRef, useState } from "react";

type Props = {
  value: number;
  min: number;
  max: number;
  onCommit: (n: number) => void;
  size?: "hero" | "dock";
  label: string;
  autoFocus?: boolean;
};

export default function NumberField({ value, min, max, onCommit, size = "dock", label, autoFocus }: Props) {
  /** null = the field is following the world. A string = the user is typing. */
  const [draft, setDraft] = useState<string | null>(null);
  const ref = useRef<HTMLInputElement | null>(null);

  const shown = draft ?? String(value);

  const commit = () => {
    const n = Number.parseInt((draft ?? "").replace(/[^\d]/g, ""), 10);
    setDraft(null); // hand the field back to the world
    if (Number.isFinite(n)) onCommit(Math.min(max, Math.max(min, n)));
  };

  const hero = size === "hero";

  return (
    <label className="group relative flex items-baseline gap-3">
      <span
        className={[
          "font-mono uppercase tracking-[0.22em] text-muted-2",
          hero ? "text-[11px]" : "text-[9px]",
        ].join(" ")}
      >
        {label}
      </span>
      <input
        ref={ref}
        // Not type="number": the spinners are ugly and it fights `inputMode`.
        inputMode="numeric"
        autoComplete="off"
        spellCheck={false}
        autoFocus={autoFocus}
        aria-label={label}
        value={shown}
        onFocus={(e) => e.currentTarget.select()}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            commit();
            ref.current?.blur();
          }
          if (e.key === "Escape") {
            setDraft(null);
            ref.current?.blur();
          }
        }}
        className={[
          "tnum w-full min-w-0 border-b bg-transparent font-mono text-parchment outline-none transition-colors",
          "border-rope-2 focus:border-gold",
          hero
            ? "pb-1 text-[64px] leading-none tracking-tight sm:text-[80px]"
            : "pb-0.5 text-[22px] leading-none",
        ].join(" ")}
      />
    </label>
  );
}
