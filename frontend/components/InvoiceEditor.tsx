"use client";

import { useEffect, useMemo, useState } from "react";
import CatalogSelect from "@/components/CatalogSelect";
import { api, Cliente, DetalleIn, Emisor, Factura, FacturaIn, Producto, Resumen } from "@/lib/api";
import { money, pct, useCatalogs, useList } from "@/lib/hooks";

type Suggestion = { ret_isr_tasa: string | null; ret_iva_tasa: string | null; motivo: string | null };

const NEW_LINE: DetalleIn = {
  producto_id: null, codigo: null, clave_prod_serv: "", clave_unidad: "E48", unidad: "Servicio", descripcion: "",
  cantidad: "1", precio_unitario: "0", descuento: "0", objeto_imp: "02", iva_tasa: "0.160000", ieps_tasa: null,
  ret_isr_tasa: null, ret_iva_tasa: null,
};

const RET_ISR = ["0.100000", "0.012500"];
const RET_IVA = ["0.106667", "0.040000", "0.060000", "0.160000"];

function fromFactura(f?: Factura): FacturaIn {
  if (!f) {
    return {
      emisor_id: 0, cliente_id: 0, tipo_comprobante: "I", uso_cfdi: "", forma_pago: "03", metodo_pago: "PUE",
      moneda: "MXN", tipo_cambio: null, exportacion: "01", condiciones_pago: null, observaciones: null,
      cfdi_relacionado_uuid: null, tipo_relacion: null, detalles: [{ ...NEW_LINE }],
    };
  }
  return {
    emisor_id: f.emisor_id, cliente_id: f.cliente_id, tipo_comprobante: f.tipo_comprobante, uso_cfdi: f.uso_cfdi,
    forma_pago: f.forma_pago, metodo_pago: f.metodo_pago, moneda: f.moneda, tipo_cambio: f.tipo_cambio,
    exportacion: f.exportacion, condiciones_pago: f.condiciones_pago, observaciones: f.observaciones,
    cfdi_relacionado_uuid: f.cfdi_relacionado_uuid, tipo_relacion: f.tipo_relacion,
    detalles: f.detalles.map(({ id, importe, total, ...d }) => ({
      ...d, cantidad: String(Number(d.cantidad)), precio_unitario: String(Number(d.precio_unitario)),
      descuento: String(Number(d.descuento)),
    })),
  };
}

export default function InvoiceEditor({ initial, onSaved }: { initial?: Factura; onSaved: (f: Factura) => void }) {
  const cats = useCatalogs();
  const emisores = useList<Emisor>("/api/emisores");
  const clientes = useList<Cliente>("/api/clientes");
  const productos = useList<Producto>("/api/productos");
  const [form, setForm] = useState<FacturaIn>(() => fromFactura(initial));
  const [resumen, setResumen] = useState<Resumen | null>(null);
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const cliente = clientes.data.find((c) => c.id === form.cliente_id) ?? null;
  const set = (patch: Partial<FacturaIn>) => setForm((f) => ({ ...f, ...patch }));
  const setLine = (i: number, patch: Partial<DetalleIn>) =>
    setForm((f) => ({ ...f, detalles: f.detalles.map((d, j) => (j === i ? { ...d, ...patch } : d)) }));

  // Default to the first issuer when there is only one.
  useEffect(() => {
    if (!form.emisor_id && emisores.data.length === 1) set({ emisor_id: emisores.data[0].id });
  }, [emisores.data, form.emisor_id]);

  // Suggested withholdings depend on issuer régimen and receiver persona type.
  useEffect(() => {
    if (!form.emisor_id || !form.cliente_id) return setSuggestion(null);
    api<Suggestion>(`/api/catalogos/retenciones-sugeridas?emisor_id=${form.emisor_id}&cliente_id=${form.cliente_id}`)
      .then(setSuggestion)
      .catch(() => setSuggestion(null));
  }, [form.emisor_id, form.cliente_id]);

  // Live totals (debounced). Placeholders keep the API happy while keys are still being typed.
  const linesKey = JSON.stringify(form.detalles);
  useEffect(() => {
    const valid = form.detalles.every((d) => Number(d.cantidad) > 0 && Number(d.precio_unitario) >= 0);
    if (!valid) return;
    const t = setTimeout(() => {
      const body: FacturaIn = {
        ...form, tipo_cambio: null, emisor_id: form.emisor_id || 1, cliente_id: form.cliente_id || 1, uso_cfdi: form.uso_cfdi || "G03",
        detalles: form.detalles.map((d) => ({
          ...d, clave_prod_serv: "01010101", clave_unidad: "H87", descripcion: "x", descuento: d.descuento || "0",
        })),
      };
      api<Resumen>("/api/facturas/calcular", { method: "POST", body: JSON.stringify(body) })
        .then((r) => { setResumen(r); setError(null); })
        .catch((e) => setError((e as Error).message));
    }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linesKey]);

  const hasRetenciones = useMemo(() => form.detalles.some((d) => d.ret_isr_tasa || d.ret_iva_tasa), [form.detalles]);

  function applySuggestion() {
    if (!suggestion) return;
    setForm((f) => ({
      ...f,
      detalles: f.detalles.map((d) => d.objeto_imp === "02"
        ? { ...d, ret_isr_tasa: suggestion.ret_isr_tasa, ret_iva_tasa: suggestion.ret_iva_tasa } : d),
    }));
  }

  function pickProduct(i: number, id: string) {
    const p = productos.data.find((x) => x.id === Number(id));
    if (!p) return setLine(i, { producto_id: null });
    setLine(i, {
      producto_id: p.id, codigo: p.codigo, clave_prod_serv: p.clave_prod_serv, clave_unidad: p.clave_unidad,
      unidad: p.unidad, descripcion: p.descripcion || p.nombre, precio_unitario: String(Number(p.precio_unitario)),
      objeto_imp: p.objeto_imp, iva_tasa: p.iva_tasa, ieps_tasa: p.ieps_tasa,
    });
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const body = JSON.stringify({
        ...form,
        tipo_cambio: form.moneda === "MXN" ? null : form.tipo_cambio,
        condiciones_pago: form.condiciones_pago || null,
        observaciones: form.observaciones || null,
        cfdi_relacionado_uuid: form.cfdi_relacionado_uuid || null,
        detalles: form.detalles.map((d) => ({
          ...d, descuento: d.descuento || "0",
          iva_tasa: d.objeto_imp === "02" ? d.iva_tasa : null,
          ieps_tasa: d.objeto_imp === "02" ? d.ieps_tasa : null,
          ret_isr_tasa: d.objeto_imp === "02" ? d.ret_isr_tasa : null,
          ret_iva_tasa: d.objeto_imp === "02" ? d.ret_iva_tasa : null,
        })),
      });
      const saved = initial
        ? await api<Factura>(`/api/facturas/${initial.id}`, { method: "PUT", body })
        : await api<Factura>("/api/facturas", { method: "POST", body });
      onSaved(saved);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!cats) return <p className="muted">Cargando catálogos…</p>;

  const showSuggestion = suggestion?.motivo && !hasRetenciones;

  return (
    <>
      {error && <div className="alert error">{error}</div>}

      <div className="card">
        <h2>Emisor y receptor</h2>
        <div className="grid">
          <label className="span2">
            Emisor
            <select value={form.emisor_id || ""} onChange={(e) => set({ emisor_id: Number(e.target.value) })}>
              <option value="">Selecciona…</option>
              {emisores.data.map((em) => <option key={em.id} value={em.id}>{em.rfc} · {em.razon_social}</option>)}
            </select>
          </label>
          <label className="span2">
            Cliente
            <select value={form.cliente_id || ""} onChange={(e) => {
              const c = clientes.data.find((x) => x.id === Number(e.target.value));
              set({ cliente_id: Number(e.target.value), uso_cfdi: c?.uso_cfdi ?? form.uso_cfdi });
            }}>
              <option value="">Selecciona…</option>
              {clientes.data.map((c) => <option key={c.id} value={c.id}>{c.rfc} · {c.razon_social}</option>)}
            </select>
          </label>
          <label className="span2">
            Uso de CFDI
            <CatalogSelect value={form.uso_cfdi} onChange={(v) => set({ uso_cfdi: v })} options={cats.usos_cfdi}
              persona={cliente?.tipo_persona ?? null} required />
          </label>
          <label>
            Tipo
            <select value={form.tipo_comprobante} onChange={(e) => set({ tipo_comprobante: e.target.value })}>
              {Object.entries(cats.tipos_comprobante).map(([k, v]) => <option key={k} value={k}>{k} · {v}</option>)}
            </select>
          </label>
        </div>
      </div>

      <div className="card">
        <h2>Pago</h2>
        <div className="grid">
          <label>
            Método de pago
            <select value={form.metodo_pago} onChange={(e) => {
              const m = e.target.value;
              set({ metodo_pago: m, forma_pago: m === "PPD" ? "99" : form.forma_pago === "99" ? "03" : form.forma_pago });
            }}>
              {Object.entries(cats.metodos_pago).map(([k, v]) => <option key={k} value={k}>{k} · {v}</option>)}
            </select>
          </label>
          <label className="span2">
            Forma de pago
            <CatalogSelect value={form.forma_pago} onChange={(v) => set({ forma_pago: v })} options={cats.formas_pago} required />
          </label>
          <label>
            Moneda
            <select value={form.moneda} onChange={(e) => set({ moneda: e.target.value })}>
              {Object.entries(cats.monedas).map(([k, v]) => <option key={k} value={k}>{k} · {v}</option>)}
            </select>
          </label>
          {form.moneda !== "MXN" && (
            <label>
              Tipo de cambio
              <input type="number" step="0.000001" min="0" value={form.tipo_cambio ?? ""} required
                onChange={(e) => set({ tipo_cambio: e.target.value })} />
            </label>
          )}
          <label>
            Condiciones de pago
            <input value={form.condiciones_pago ?? ""} placeholder="Ej. Crédito a 30 días"
              onChange={(e) => set({ condiciones_pago: e.target.value })} />
          </label>
          {form.tipo_comprobante === "E" && (
            <label className="span2">
              UUID de la factura relacionada
              <input value={form.cfdi_relacionado_uuid ?? ""} className="mono"
                onChange={(e) => set({ cfdi_relacionado_uuid: e.target.value, tipo_relacion: "01" })} />
            </label>
          )}
        </div>
      </div>

      <div className="card">
        <div className="page-head" style={{ marginBottom: "0.75rem" }}>
          <h2 style={{ margin: 0 }}>Conceptos</h2>
          <button onClick={() => set({
            detalles: [...form.detalles, { ...NEW_LINE, ret_isr_tasa: suggestion?.ret_isr_tasa ?? null,
              ret_iva_tasa: suggestion?.ret_iva_tasa ?? null }],
          })}>+ Agregar concepto</button>
        </div>

        {showSuggestion && (
          <div className="alert warn row" style={{ justifyContent: "space-between" }}>
            <span>{suggestion?.motivo}</span>
            <button onClick={applySuggestion}>Aplicar retenciones</button>
          </div>
        )}

        {form.detalles.map((d, i) => (
          <div className="line" key={i}>
            <div className="line-grid">
              <label>
                Descripción
                <input value={d.descripcion} required onChange={(e) => setLine(i, { descripcion: e.target.value })} />
              </label>
              <label>
                Producto
                <select value={d.producto_id ?? ""} onChange={(e) => pickProduct(i, e.target.value)}>
                  <option value="">Concepto libre</option>
                  {productos.data.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                </select>
              </label>
              <label>
                ClaveProdServ
                <input value={d.clave_prod_serv} maxLength={8} placeholder="8 dígitos"
                  onChange={(e) => setLine(i, { clave_prod_serv: e.target.value })} />
              </label>
              <label>
                ClaveUnidad
                <input value={d.clave_unidad} maxLength={3} onChange={(e) => setLine(i, { clave_unidad: e.target.value.toUpperCase() })} />
              </label>
              <label>
                Cantidad
                <input type="number" step="any" min="0" value={d.cantidad} onChange={(e) => setLine(i, { cantidad: e.target.value })} />
              </label>
              <label>
                Valor unitario
                <input type="number" step="any" min="0" value={d.precio_unitario}
                  onChange={(e) => setLine(i, { precio_unitario: e.target.value })} />
              </label>
            </div>
            <div className="line-grid taxes">
              <label>
                Objeto imp.
                <select value={d.objeto_imp} onChange={(e) => setLine(i, { objeto_imp: e.target.value })}>
                  {Object.entries(cats.objetos_impuesto).map(([k, v]) => <option key={k} value={k} title={v}>{k} · {v}</option>)}
                </select>
              </label>
              <label>
                IVA trasladado
                <select disabled={d.objeto_imp !== "02"} value={d.iva_tasa ?? ""}
                  onChange={(e) => setLine(i, { iva_tasa: e.target.value || null })}>
                  <option value="">—</option>
                  {cats.tasas_iva.map((t) => <option key={t} value={t}>{pct(t)}</option>)}
                </select>
              </label>
              <label>
                Ret. ISR
                <select disabled={d.objeto_imp !== "02"} value={d.ret_isr_tasa ?? ""}
                  onChange={(e) => setLine(i, { ret_isr_tasa: e.target.value || null })}>
                  <option value="">—</option>
                  {RET_ISR.map((t) => <option key={t} value={t}>{pct(t)}</option>)}
                </select>
              </label>
              <label>
                Ret. IVA
                <select disabled={d.objeto_imp !== "02"} value={d.ret_iva_tasa ?? ""}
                  onChange={(e) => setLine(i, { ret_iva_tasa: e.target.value || null })}>
                  <option value="">—</option>
                  {RET_IVA.map((t) => <option key={t} value={t}>{t === "0.106667" ? "2/3 (10.6667%)" : pct(t)}</option>)}
                </select>
              </label>
              <label>
                Descuento
                <input type="number" step="0.01" min="0" value={d.descuento} onChange={(e) => setLine(i, { descuento: e.target.value })} />
              </label>
              <button className="ghost" disabled={form.detalles.length === 1}
                onClick={() => set({ detalles: form.detalles.filter((_, j) => j !== i) })}>Quitar</button>
            </div>
          </div>
        ))}

        {resumen && (
          <div className="totals">
            <div><span>Subtotal</span><span>{money(resumen.subtotal, form.moneda)}</span></div>
            {Number(resumen.descuento) > 0 && <div><span>Descuento</span><span>−{money(resumen.descuento, form.moneda)}</span></div>}
            {resumen.traslados.map((t, i) => (
              <div key={`t${i}`}><span>{t.impuesto} {t.tipo_factor === "Exento" ? "exento" : pct(t.tasa)}</span>
                <span>{money(t.importe, form.moneda)}</span></div>
            ))}
            {resumen.retenciones.map((t, i) => (
              <div key={`r${i}`}><span>Ret. {t.impuesto} {pct(t.tasa)}</span><span>−{money(t.importe, form.moneda)}</span></div>
            ))}
            <div className="grand"><span>Total</span><span>{money(resumen.total, form.moneda)}</span></div>
          </div>
        )}
      </div>

      <div className="card">
        <label>
          Observaciones (solo aparecen en el PDF)
          <textarea rows={2} value={form.observaciones ?? ""} onChange={(e) => set({ observaciones: e.target.value })} />
        </label>
      </div>

      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="primary" onClick={save} disabled={saving || !form.emisor_id || !form.cliente_id}>
          {saving ? "Guardando…" : "Guardar borrador"}
        </button>
      </div>
    </>
  );
}
