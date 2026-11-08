"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import EstadoBadge from "@/components/EstadoBadge";
import { Factura } from "@/lib/api";
import { fecha, money, useList } from "@/lib/hooks";

const ESTADOS = ["", "Borrador", "Emitida", "Cancelación pendiente", "Cancelada"];

export default function FacturasPage() {
  const router = useRouter();
  const [estado, setEstado] = useState("");
  const [q, setQ] = useState("");
  const params = new URLSearchParams();
  if (estado) params.set("estado", estado);
  if (q) params.set("q", q);
  const { data, loading, error } = useList<Factura>(`/api/facturas?${params}`);

  return (
    <>
      <div className="page-head">
        <h1>Facturas</h1>
        <div className="row">
          <input placeholder="Cliente, RFC o UUID" value={q} onChange={(e) => setQ(e.target.value)} />
          <select value={estado} onChange={(e) => setEstado(e.target.value)}>
            {ESTADOS.map((e) => <option key={e} value={e}>{e || "Todos los estados"}</option>)}
          </select>
          <Link href="/facturas/nueva" className="btn primary">+ Nueva factura</Link>
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="card">
        {loading ? <p className="muted">Cargando…</p> : data.length === 0 ? (
          <p className="muted">No hay facturas. Registra un emisor y un cliente, luego crea tu primera factura.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Folio</th><th>Fecha</th><th>Emisor</th><th>Cliente</th><th>Estado</th><th className="num">Total</th></tr>
            </thead>
            <tbody>
              {data.map((f) => (
                <tr key={f.id} className="clickable" onClick={() => router.push(`/facturas/${f.id}`)}>
                  <td className="mono">{f.folio ? `${f.serie ?? ""}${f.folio}` : `Borrador #${f.id}`}</td>
                  <td>{fecha(f.fecha_emision ?? f.fecha_creacion)}</td>
                  <td>{f.emisor.rfc}</td>
                  <td>{f.cliente.razon_social}<div className="muted mono">{f.cliente.rfc}</div></td>
                  <td><EstadoBadge estado={f.estado} /></td>
                  <td className="num">{money(f.total, f.moneda)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
