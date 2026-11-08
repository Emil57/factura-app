"use client";

import { useCallback, useEffect, useState } from "react";
import { api, Catalogs } from "./api";

let catalogCache: Catalogs | null = null;

export function useCatalogs(): Catalogs | null {
  const [cats, setCats] = useState<Catalogs | null>(catalogCache);
  useEffect(() => {
    if (catalogCache) return;
    api<Catalogs>("/api/catalogos").then((c) => {
      catalogCache = c;
      setCats(c);
    });
  }, []);
  return cats;
}

/** Fetch a list endpoint and expose reload + error state. */
export function useList<T>(path: string | null) {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    try {
      setData(await api<T[]>(path));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload };
}

export function money(value: string | number | null | undefined, currency = "MXN") {
  const n = Number(value ?? 0);
  return n.toLocaleString("es-MX", { style: "currency", currency });
}

export function pct(rate: string | null) {
  if (rate === null) return "";
  if (rate === "exento") return "Exento";
  return `${(Number(rate) * 100).toLocaleString("es-MX", { maximumFractionDigits: 4 })}%`;
}

export function fecha(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
}
