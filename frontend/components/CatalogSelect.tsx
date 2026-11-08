"use client";

import type { CatalogEntry } from "@/lib/api";

type Props = {
  value: string;
  onChange: (v: string) => void;
  options: Record<string, string | CatalogEntry>;
  /** When set, only entries valid for this persona type are listed. */
  persona?: "fisica" | "moral" | null;
  required?: boolean;
};

export default function CatalogSelect({ value, onChange, options, persona, required }: Props) {
  const entries = Object.entries(options).filter(([, v]) =>
    !persona || typeof v === "string" ? true : v[persona],
  );
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} required={required}>
      <option value="">Selecciona…</option>
      {entries.map(([k, v]) => (
        <option key={k} value={k}>
          {k} · {typeof v === "string" ? v : v.descripcion}
        </option>
      ))}
    </select>
  );
}

export function personaFromRfc(rfc: string): "fisica" | "moral" | null {
  const clean = rfc.trim().toUpperCase();
  if (clean.length === 12) return "moral";
  if (clean.length === 13) return "fisica";
  return null;
}
