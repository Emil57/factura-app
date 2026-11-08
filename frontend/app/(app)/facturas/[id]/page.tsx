"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import EstadoBadge from "@/components/EstadoBadge";
import InvoiceEditor from "@/components/InvoiceEditor";
import Modal from "@/components/Modal";
import { hasRole, useUser } from "@/components/UserContext";
import { api, download, Factura, Resumen } from "@/lib/api";
import { fecha, money, pct, useCatalogs } from "@/lib/hooks";

export default function FacturaPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const user = useUser();
  const cats = useCatalogs();
  const [factura, setFactura] = useState<Factura | null>(null);
  const [resumen, setResumen] = useState<Resumen | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [motivo, setMotivo] = useState("02");
  const [sustituto, setSustituto] = useState("");

  const load = useCallback(async () => {
    const f = await api<Factura>(`/api/facturas/${id}`);
    setFactura(f);
    setResumen(await api<Resumen>(`/api/facturas/${id}/resumen`));
    if (f.estado === "Borrador") {
      setErrors((await api<{ errores: string[] }>(`/api/facturas/${id}/validar`, { method: "POST" })).errores);
    } else setErrors([]);
  }, [id]);

  useEffect(() => {
    load().catch((e) => setMessage((e as Error).message));
  }, [load]);

  async function run(fn: () => Promise<unknown>, ok?: string) {
    setBusy(true);
    setMessage(null);
    try {
      await fn();
      if (ok) setMessage(ok);
      await load();
    } catch (e) {
      setErrors([(e as Error).message]);
    } finally {
      setBusy(false);
    }
  }

  if (!factura || !cats) return <p className="muted">{message ?? "Cargando…"}</p>;

  if (editing) {
    return (
      <>
        <div className="page-head">
          <h1>Editar borrador #{factura.id}</h1>
          <button onClick={() => setEditing(false)}>Volver</button>
        </div>
        <InvoiceEditor initial={factura} onSaved={() => { setEditing(false); load(); }} />
      </>
    );
  }

  const nombreArchivo = `${factura.serie ?? ""}${factura.folio ?? factura.id}_${factura.uuid ?? "borrador"}`;
  const canEmit = hasRole(user, "Usuario");
  const canCancel = hasRole(user, "Contador");

  return (
    <>
      <div className="page-head">
        <div>
          <Link href="/facturas" className="muted">← Facturas</Link>
          <h1 style={{ marginTop: "0.3rem" }}>
            {factura.folio ? `Factura ${factura.serie ?? ""}${factura.folio}` : `Borrador #${factura.id}`}{" "}
            <EstadoBadge estado={factura.estado} />
          </h1>
        </div>
        <div className="row">
          {factura.estado === "Borrador" && canEmit && (
            <>
              <button onClick={() => setEditing(true)}>Editar</button>
              <button onClick={() => run(async () => {
                if (!confirm("¿Eliminar este borrador?")) return;
                await api(`/api/facturas/${factura.id}`, { method: "DELETE" });
                router.replace("/facturas");
              })}>Eliminar</button>
              <button onClick={() => download(`/api/facturas/${factura.id}/xml`, `${nombreArchivo}.xml`)}>Vista previa XML</button>
              <button className="primary" disabled={busy || errors.length > 0}
                onClick={() => run(() => api(`/api/facturas/${factura.id}/timbrar`, { method: "POST" }), "Factura timbrada correctamente")}>
                {busy ? "Timbrando…" : "Timbrar"}
              </button>
            </>
          )}
          {factura.uuid && (
            <>
              <button onClick={() => download(`/api/facturas/${factura.id}/xml`, `${nombreArchivo}.xml`).catch((e) => setErrors([e.message]))}>XML</button>
              <button onClick={() => download(`/api/facturas/${factura.id}/pdf`, `${nombreArchivo}.pdf`).catch((e) => setErrors([e.message]))}>PDF</button>
            </>
          )}
          {(factura.estado === "Emitida" || factura.estado === "Cancelación pendiente") && canCancel && (
            <button className="danger" onClick={() => setCancelOpen(true)}>
              {factura.estado === "Emitida" ? "Cancelar" : "Reintentar cancelación"}
            </button>
          )}
        </div>
      </div>

      {message && <div className="alert info">{message}</div>}
      {errors.length > 0 && (
        <div className="alert error">
          {factura.estado === "Borrador" ? "Corrige antes de timbrar:\n" : ""}
          {errors.map((e) => `• ${e}`).join("\n")}
        </div>
      )}
      {factura.estado === "Cancelación pendiente" && (
        <div className="alert warn">El receptor debe aceptar la cancelación en el buzón tributario (tiene 72 horas).</div>
      )}

      <div className="grid" style={{ marginBottom: "1rem" }}>
        <div className="card" style={{ margin: 0 }}>
          <h2>Emisor</h2>
          <div className="mono">{factura.emisor.rfc}</div>
          <div>{factura.emisor.razon_social}</div>
          <div className="muted">Régimen {factura.emisor.regimen_fiscal} · CP {factura.emisor.codigo_postal}</div>
        </div>
        <div className="card" style={{ margin: 0 }}>
          <h2>Receptor</h2>
          <div className="mono">{factura.cliente.rfc}</div>
          <div>{factura.cliente.razon_social}</div>
          <div className="muted">Régimen {factura.cliente.regimen_fiscal} · CP {factura.cliente.codigo_postal} · Uso {factura.uso_cfdi}</div>
        </div>
        <div className="card" style={{ margin: 0 }}>
          <h2>Comprobante</h2>
          <div className="muted">{cats.tipos_comprobante[factura.tipo_comprobante]} · {factura.metodo_pago} · Forma {factura.forma_pago} · {factura.moneda}</div>
          <div className="muted">Emisión: {fecha(factura.fecha_emision)}</div>
          {factura.uuid && <div className="mono" style={{ wordBreak: "break-all" }}>UUID {factura.uuid}</div>}
          {factura.motivo_cancelacion && <div className="muted">Motivo cancelación: {factura.motivo_cancelacion}</div>}
        </div>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr><th>Clave</th><th>Descripción</th><th className="num">Cant.</th><th className="num">V. unitario</th><th>Impuestos</th><th className="num">Importe</th></tr>
          </thead>
          <tbody>
            {factura.detalles.map((d) => (
              <tr key={d.id}>
                <td className="mono">{d.clave_prod_serv}<div className="muted">{d.clave_unidad}</div></td>
                <td>{d.descripcion}</td>
                <td className="num">{Number(d.cantidad)}</td>
                <td className="num">{money(d.precio_unitario, factura.moneda)}</td>
                <td className="muted">
                  {d.objeto_imp !== "02" ? `Objeto ${d.objeto_imp}` : [
                    d.iva_tasa && `IVA ${pct(d.iva_tasa)}`, d.ieps_tasa && `IEPS ${pct(d.ieps_tasa)}`,
                    d.ret_isr_tasa && `Ret ISR ${pct(d.ret_isr_tasa)}`, d.ret_iva_tasa && `Ret IVA ${pct(d.ret_iva_tasa)}`,
                  ].filter(Boolean).join(" · ")}
                </td>
                <td className="num">{money(d.importe, factura.moneda)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {resumen && (
          <div className="totals" style={{ marginTop: "1rem" }}>
            <div><span>Subtotal</span><span>{money(resumen.subtotal, factura.moneda)}</span></div>
            {Number(resumen.descuento) > 0 && <div><span>Descuento</span><span>−{money(resumen.descuento, factura.moneda)}</span></div>}
            {resumen.traslados.map((t, i) => (
              <div key={`t${i}`}><span>{t.impuesto} {t.tipo_factor === "Exento" ? "exento" : pct(t.tasa)}</span><span>{money(t.importe, factura.moneda)}</span></div>
            ))}
            {resumen.retenciones.map((t, i) => (
              <div key={`r${i}`}><span>Ret. {t.impuesto} {pct(t.tasa)}</span><span>−{money(t.importe, factura.moneda)}</span></div>
            ))}
            <div className="grand"><span>Total</span><span>{money(resumen.total, factura.moneda)}</span></div>
          </div>
        )}
      </div>

      {cancelOpen && (
        <Modal title="Cancelar factura" onClose={() => setCancelOpen(false)}>
          <div className="grid">
            <label className="span2">
              Motivo
              <select value={motivo} onChange={(e) => setMotivo(e.target.value)}>
                {Object.entries(cats.motivos_cancelacion).map(([k, v]) => <option key={k} value={k}>{k} · {v}</option>)}
              </select>
            </label>
            {motivo === "01" && (
              <label className="span2">
                UUID de la factura que la sustituye
                <input className="mono" value={sustituto} onChange={(e) => setSustituto(e.target.value)} />
              </label>
            )}
            <div className="row span2" style={{ justifyContent: "flex-end" }}>
              <button onClick={() => setCancelOpen(false)}>Volver</button>
              <button className="danger" disabled={busy || (motivo === "01" && !sustituto)} onClick={() => {
                setCancelOpen(false);
                run(() => api(`/api/facturas/${factura.id}/cancelar`, {
                  method: "POST", body: JSON.stringify({ motivo, uuid_sustitucion: motivo === "01" ? sustituto : null }),
                }), "Solicitud de cancelación enviada");
              }}>Confirmar cancelación</button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
