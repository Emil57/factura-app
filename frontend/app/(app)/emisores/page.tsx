"use client";

import { FormEvent, useState } from "react";
import CatalogSelect, { personaFromRfc } from "@/components/CatalogSelect";
import Modal from "@/components/Modal";
import { hasRole, useUser } from "@/components/UserContext";
import { api, Emisor } from "@/lib/api";
import { useCatalogs, useList } from "@/lib/hooks";

type Form = Omit<Emisor, "id" | "csd_cargado" | "activo">;
const EMPTY: Form = {
  rfc: "", razon_social: "", regimen_fiscal: "", codigo_postal: "", email: "", telefono: "",
  direccion: "", logo_url: "", serie: "A", siguiente_folio: 1,
};

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export default function EmisoresPage() {
  const cats = useCatalogs();
  const user = useUser();
  const isAdmin = hasRole(user);
  const { data, loading, error, reload } = useList<Emisor>("/api/emisores");
  const [editing, setEditing] = useState<{ id: number | null; form: Form } | null>(null);
  const [csdFor, setCsdFor] = useState<Emisor | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const set = (patch: Partial<Form>) => editing && setEditing({ ...editing, form: { ...editing.form, ...patch } });

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setFormError(null);
    const f = editing.form;
    const body = JSON.stringify({
      ...f, email: f.email || null, telefono: f.telefono || null, direccion: f.direccion || null, logo_url: f.logo_url || null,
    });
    try {
      if (editing.id) await api(`/api/emisores/${editing.id}`, { method: "PUT", body });
      else await api("/api/emisores", { method: "POST", body });
      setEditing(null);
      reload();
    } catch (err) {
      setFormError((err as Error).message);
    }
  }

  async function uploadCsd(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!csdFor) return;
    setFormError(null);
    const fd = new FormData(e.currentTarget);
    try {
      await api(`/api/emisores/${csdFor.id}/csd`, {
        method: "POST",
        body: JSON.stringify({
          certificado_b64: await fileToBase64(fd.get("cer") as File),
          llave_b64: await fileToBase64(fd.get("key") as File),
          password: fd.get("password"),
        }),
      });
      setCsdFor(null);
      reload();
    } catch (err) {
      setFormError((err as Error).message);
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Emisores</h1>
        {isAdmin && (
          <button className="primary" onClick={() => { setFormError(null); setEditing({ id: null, form: EMPTY }); }}>
            + Nuevo emisor
          </button>
        )}
      </div>
      <p className="muted">
        Cada emisor es un contribuyente (persona física o moral, de cualquier régimen) que factura desde esta app.
        Para timbrar con Facturama, sube su Certificado de Sello Digital (CSD) una vez.
      </p>
      {error && <div className="alert error">{error}</div>}
      <div className="card">
        {loading ? <p className="muted">Cargando…</p> : data.length === 0 ? (
          <p className="muted">Registra tu primer emisor para empezar a facturar.</p>
        ) : (
          <table>
            <thead>
              <tr><th>RFC</th><th>Razón social</th><th>Régimen</th><th>Lugar exp.</th><th>Serie / folio</th><th>CSD</th><th /></tr>
            </thead>
            <tbody>
              {data.map((em) => (
                <tr key={em.id}>
                  <td className="mono">{em.rfc}</td>
                  <td>{em.razon_social}</td>
                  <td>{em.regimen_fiscal} · {cats?.regimenes_fiscales[em.regimen_fiscal]?.descripcion}</td>
                  <td>{em.codigo_postal}</td>
                  <td>{em.serie} · {em.siguiente_folio}</td>
                  <td>{em.csd_cargado ? <span className="badge Emitida">Cargado</span> : <span className="badge pendiente">Pendiente</span>}</td>
                  <td className="num">
                    {isAdmin && (
                      <>
                        <button className="ghost" onClick={() => { setFormError(null); setCsdFor(em); }}>CSD</button>
                        <button className="ghost" onClick={() => {
                          const { id, csd_cargado, activo, ...form } = em;
                          setFormError(null);
                          setEditing({ id, form });
                        }}>Editar</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editing && cats && (
        <Modal title={editing.id ? "Editar emisor" : "Nuevo emisor"} onClose={() => setEditing(null)}>
          {formError && <div className="alert error">{formError}</div>}
          <form onSubmit={save} className="grid">
            <label>
              RFC
              <input value={editing.form.rfc} maxLength={13} required onChange={(e) => set({ rfc: e.target.value.toUpperCase() })} />
            </label>
            <label className="span2">
              Razón social (como en la Constancia)
              <input value={editing.form.razon_social} required onChange={(e) => set({ razon_social: e.target.value })} />
            </label>
            <label className="span2">
              Régimen fiscal
              <CatalogSelect value={editing.form.regimen_fiscal} onChange={(v) => set({ regimen_fiscal: v })}
                options={cats.regimenes_fiscales} persona={personaFromRfc(editing.form.rfc)} required />
            </label>
            <label>
              CP lugar de expedición
              <input value={editing.form.codigo_postal} pattern="\d{5}" maxLength={5} required
                onChange={(e) => set({ codigo_postal: e.target.value })} />
            </label>
            <label>
              Serie
              <input value={editing.form.serie} maxLength={25} required onChange={(e) => set({ serie: e.target.value.toUpperCase() })} />
            </label>
            <label>
              Siguiente folio
              <input type="number" min={1} value={editing.form.siguiente_folio} required
                onChange={(e) => set({ siguiente_folio: Number(e.target.value) })} />
            </label>
            <label>
              Correo
              <input type="email" value={editing.form.email ?? ""} onChange={(e) => set({ email: e.target.value })} />
            </label>
            <label>
              Teléfono
              <input value={editing.form.telefono ?? ""} onChange={(e) => set({ telefono: e.target.value })} />
            </label>
            <label className="span2">
              Dirección
              <input value={editing.form.direccion ?? ""} onChange={(e) => set({ direccion: e.target.value })} />
            </label>
            <label className="span2">
              URL del logo (para el PDF)
              <input value={editing.form.logo_url ?? ""} onChange={(e) => set({ logo_url: e.target.value })} />
            </label>
            <div className="row span2" style={{ justifyContent: "flex-end", alignSelf: "end" }}>
              <button type="button" onClick={() => setEditing(null)}>Cancelar</button>
              <button className="primary">Guardar</button>
            </div>
          </form>
        </Modal>
      )}

      {csdFor && (
        <Modal title={`CSD de ${csdFor.rfc}`} onClose={() => setCsdFor(null)}>
          {formError && <div className="alert error">{formError}</div>}
          <p className="muted" style={{ marginTop: 0 }}>
            Los archivos se envían al PAC y no se guardan en esta base de datos. Usa el CSD (sello), no la e.firma.
          </p>
          <form onSubmit={uploadCsd} className="grid">
            <label className="span2">Certificado (.cer)<input name="cer" type="file" accept=".cer" required /></label>
            <label className="span2">Llave privada (.key)<input name="key" type="file" accept=".key" required /></label>
            <label className="span2">Contraseña de la llave<input name="password" type="password" required /></label>
            <div className="row span2" style={{ justifyContent: "flex-end" }}>
              <button type="button" onClick={() => setCsdFor(null)}>Cancelar</button>
              <button className="primary">Subir CSD</button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
