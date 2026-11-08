"use client";

import { FormEvent, useState } from "react";
import CatalogSelect from "@/components/CatalogSelect";
import Modal from "@/components/Modal";
import { api, Producto } from "@/lib/api";
import { money, pct, useCatalogs, useList } from "@/lib/hooks";

type Form = Omit<Producto, "id" | "activo">;
const EMPTY: Form = {
  categoria_id: null, codigo: "", nombre: "", descripcion: "", clave_prod_serv: "", clave_unidad: "E48",
  unidad: "Servicio", precio_unitario: "0", objeto_imp: "02", iva_tasa: "0.160000", ieps_tasa: null, stock: null,
};

export default function ProductosPage() {
  const cats = useCatalogs();
  const [q, setQ] = useState("");
  const { data, loading, error, reload } = useList<Producto>(`/api/productos${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  const [editing, setEditing] = useState<{ id: number | null; form: Form } | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const set = (patch: Partial<Form>) => editing && setEditing({ ...editing, form: { ...editing.form, ...patch } });

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setFormError(null);
    const f = editing.form;
    const body = JSON.stringify({
      ...f, codigo: f.codigo || null, descripcion: f.descripcion || null, unidad: f.unidad || null,
      iva_tasa: f.objeto_imp === "02" ? f.iva_tasa : null, ieps_tasa: f.objeto_imp === "02" ? f.ieps_tasa : null,
    });
    try {
      if (editing.id) await api(`/api/productos/${editing.id}`, { method: "PUT", body });
      else await api("/api/productos", { method: "POST", body });
      setEditing(null);
      reload();
    } catch (err) {
      setFormError((err as Error).message);
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Productos y servicios</h1>
        <div className="row">
          <input placeholder="Buscar" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="primary" onClick={() => { setFormError(null); setEditing({ id: null, form: EMPTY }); }}>
            + Nuevo producto
          </button>
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="card">
        {loading ? <p className="muted">Cargando…</p> : data.length === 0 ? (
          <p className="muted">Sin productos. También puedes capturar conceptos libres directamente en la factura.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Código</th><th>Nombre</th><th>Clave SAT</th><th>Unidad</th><th>Impuestos</th><th className="num">Precio</th><th /></tr>
            </thead>
            <tbody>
              {data.map((p) => (
                <tr key={p.id}>
                  <td className="mono">{p.codigo ?? "—"}</td>
                  <td>{p.nombre}</td>
                  <td className="mono">{p.clave_prod_serv}</td>
                  <td>{p.clave_unidad} {p.unidad}</td>
                  <td>
                    {p.objeto_imp !== "02" ? `Objeto ${p.objeto_imp}` :
                      [p.iva_tasa && `IVA ${pct(p.iva_tasa)}`, p.ieps_tasa && `IEPS ${pct(p.ieps_tasa)}`].filter(Boolean).join(" + ")}
                  </td>
                  <td className="num">{money(p.precio_unitario)}</td>
                  <td className="num">
                    <button className="ghost" onClick={() => {
                      const { id, activo, ...form } = p;
                      setFormError(null);
                      setEditing({ id, form });
                    }}>Editar</button>
                    <button className="ghost" onClick={async () => {
                      if (confirm(`¿Desactivar ${p.nombre}?`)) {
                        await api(`/api/productos/${p.id}`, { method: "DELETE" });
                        reload();
                      }
                    }}>Desactivar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editing && cats && (
        <Modal title={editing.id ? "Editar producto" : "Nuevo producto"} onClose={() => setEditing(null)}>
          {formError && <div className="alert error">{formError}</div>}
          <form onSubmit={save} className="grid">
            <label className="span2">
              Nombre (descripción en la factura)
              <input value={editing.form.nombre} required onChange={(e) => set({ nombre: e.target.value })} />
            </label>
            <label>
              Código interno
              <input value={editing.form.codigo ?? ""} onChange={(e) => set({ codigo: e.target.value })} />
            </label>
            <label>
              ClaveProdServ SAT
              <input value={editing.form.clave_prod_serv} pattern="\d{8}" maxLength={8} required placeholder="80111600"
                onChange={(e) => set({ clave_prod_serv: e.target.value })} />
            </label>
            <label>
              ClaveUnidad SAT
              <input value={editing.form.clave_unidad} maxLength={3} required placeholder="E48, H87, ACT…"
                onChange={(e) => set({ clave_unidad: e.target.value.toUpperCase() })} />
            </label>
            <label>
              Unidad (texto)
              <input value={editing.form.unidad ?? ""} onChange={(e) => set({ unidad: e.target.value })} />
            </label>
            <label>
              Precio unitario (sin IVA)
              <input type="number" step="0.000001" min="0" value={editing.form.precio_unitario} required
                onChange={(e) => set({ precio_unitario: e.target.value })} />
            </label>
            <label className="span2">
              Objeto de impuesto
              <CatalogSelect value={editing.form.objeto_imp} onChange={(v) => set({ objeto_imp: v })}
                options={cats.objetos_impuesto} required />
            </label>
            {editing.form.objeto_imp === "02" && (
              <>
                <label>
                  IVA
                  <select value={editing.form.iva_tasa ?? ""} onChange={(e) => set({ iva_tasa: e.target.value || null })}>
                    <option value="">Sin IVA</option>
                    {cats.tasas_iva.map((t) => <option key={t} value={t}>{pct(t)}</option>)}
                  </select>
                </label>
                <label>
                  IEPS
                  <select value={editing.form.ieps_tasa ?? ""} onChange={(e) => set({ ieps_tasa: e.target.value || null })}>
                    <option value="">Sin IEPS</option>
                    {cats.tasas_ieps.map((t) => <option key={t} value={t}>{pct(t)}</option>)}
                  </select>
                </label>
              </>
            )}
            <div className="row span2" style={{ justifyContent: "flex-end", alignSelf: "end" }}>
              <button type="button" onClick={() => setEditing(null)}>Cancelar</button>
              <button className="primary">Guardar</button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
