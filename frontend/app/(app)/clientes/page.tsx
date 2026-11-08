"use client";

import { FormEvent, useState } from "react";
import CatalogSelect, { personaFromRfc } from "@/components/CatalogSelect";
import Modal from "@/components/Modal";
import { api, Cliente } from "@/lib/api";
import { useCatalogs, useList } from "@/lib/hooks";

type Form = Omit<Cliente, "id" | "tipo_persona" | "activo">;
const EMPTY: Form = { rfc: "", razon_social: "", regimen_fiscal: "", uso_cfdi: "G03", codigo_postal: "", email: "" };
const GENERIC = ["XAXX010101000", "XEXX010101000"];

export default function ClientesPage() {
  const cats = useCatalogs();
  const [q, setQ] = useState("");
  const { data, loading, error, reload } = useList<Cliente>(`/api/clientes${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  const [editing, setEditing] = useState<{ id: number | null; form: Form } | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const persona = editing ? personaFromRfc(editing.form.rfc) : null;
  const set = (patch: Partial<Form>) => editing && setEditing({ ...editing, form: { ...editing.form, ...patch } });

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setFormError(null);
    try {
      const body = JSON.stringify({ ...editing.form, email: editing.form.email || null });
      if (editing.id) await api(`/api/clientes/${editing.id}`, { method: "PUT", body });
      else await api("/api/clientes", { method: "POST", body });
      setEditing(null);
      reload();
    } catch (err) {
      setFormError((err as Error).message);
    }
  }

  async function remove(c: Cliente) {
    if (!confirm(`¿Desactivar a ${c.razon_social}?`)) return;
    await api(`/api/clientes/${c.id}`, { method: "DELETE" });
    reload();
  }

  return (
    <>
      <div className="page-head">
        <h1>Clientes</h1>
        <div className="row">
          <input placeholder="Buscar por RFC o nombre" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="primary" onClick={() => { setFormError(null); setEditing({ id: null, form: EMPTY }); }}>
            + Nuevo cliente
          </button>
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="card">
        {loading ? <p className="muted">Cargando…</p> : data.length === 0 ? (
          <p className="muted">Aún no hay clientes. Para ventas de mostrador crea “PUBLICO EN GENERAL” con RFC XAXX010101000.</p>
        ) : (
          <table>
            <thead>
              <tr><th>RFC</th><th>Razón social</th><th>Persona</th><th>Régimen</th><th>Uso CFDI</th><th>CP</th><th /></tr>
            </thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.id}>
                  <td className="mono">{c.rfc}</td>
                  <td>{c.razon_social}</td>
                  <td>{c.tipo_persona === "moral" ? "Moral" : "Física"}</td>
                  <td>{c.regimen_fiscal}</td>
                  <td>{c.uso_cfdi}</td>
                  <td>{c.codigo_postal}</td>
                  <td className="num">
                    <button className="ghost" onClick={() => {
                      setFormError(null);
                      const { id, tipo_persona, activo, ...form } = c;
                      setEditing({ id, form });
                    }}>Editar</button>
                    <button className="ghost" onClick={() => remove(c)}>Desactivar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editing && cats && (
        <Modal title={editing.id ? "Editar cliente" : "Nuevo cliente"} onClose={() => setEditing(null)}>
          {formError && <div className="alert error">{formError}</div>}
          <p className="muted" style={{ marginTop: 0 }}>
            CFDI 4.0 exige que nombre, régimen y código postal coincidan con la Constancia de Situación Fiscal del cliente.
            Escribe la razón social sin el régimen societario (sin “S.A. de C.V.”).
          </p>
          <form onSubmit={save} className="grid">
            <label>
              RFC
              <input value={editing.form.rfc} maxLength={13} required
                onChange={(e) => {
                  const rfc = e.target.value.toUpperCase();
                  if (GENERIC.includes(rfc)) {
                    set({ rfc, regimen_fiscal: "616", uso_cfdi: "S01",
                      razon_social: rfc === "XAXX010101000" ? "PUBLICO EN GENERAL" : editing.form.razon_social });
                  } else set({ rfc });
                }} />
            </label>
            <label className="span2">
              Razón social / nombre
              <input value={editing.form.razon_social} required onChange={(e) => set({ razon_social: e.target.value })} />
            </label>
            <label className="span2">
              Régimen fiscal
              <CatalogSelect value={editing.form.regimen_fiscal} onChange={(v) => set({ regimen_fiscal: v })}
                options={cats.regimenes_fiscales} persona={persona} required />
            </label>
            <label>
              Código postal fiscal
              <input value={editing.form.codigo_postal} pattern="\d{5}" maxLength={5} required
                onChange={(e) => set({ codigo_postal: e.target.value })} />
            </label>
            <label className="span2">
              Uso de CFDI habitual
              <CatalogSelect value={editing.form.uso_cfdi} onChange={(v) => set({ uso_cfdi: v })}
                options={cats.usos_cfdi} persona={persona} required />
            </label>
            <label>
              Correo
              <input type="email" value={editing.form.email ?? ""} onChange={(e) => set({ email: e.target.value })} />
            </label>
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
