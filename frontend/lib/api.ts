export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "factura_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable */
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** Turns FastAPI error bodies (string, list of strings, pydantic errors, {mensaje}) into text. */
function errorMessage(detail: unknown): string {
  if (!detail) return "Error inesperado";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === "string" ? d : `${(d.loc ?? []).slice(1).join(".")}: ${d.msg}`))
      .join("\n");
  }
  if (typeof detail === "object" && detail && "mensaje" in detail) {
    const d = detail as { mensaje: string; detalle?: unknown };
    const extra = d.detalle && typeof d.detalle === "object" ? `\n${JSON.stringify(d.detalle)}` : "";
    return d.mensaje + extra;
  }
  return JSON.stringify(detail);
}

export async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof URLSearchParams) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/api/auth/token")) {
    setToken(null);
    window.location.href = "/login";
  }
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, errorMessage(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function download(path: string, filename: string) {
  const res = await fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, errorMessage(detail));
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------- Types ----------
export type CatalogEntry = { descripcion: string; fisica: boolean; moral: boolean };
export type Catalogs = {
  regimenes_fiscales: Record<string, CatalogEntry>;
  usos_cfdi: Record<string, CatalogEntry>;
  formas_pago: Record<string, string>;
  metodos_pago: Record<string, string>;
  objetos_impuesto: Record<string, string>;
  tipos_comprobante: Record<string, string>;
  monedas: Record<string, string>;
  exportacion: Record<string, string>;
  motivos_cancelacion: Record<string, string>;
  tasas_iva: string[];
  tasas_ieps: string[];
};

export type Emisor = {
  id: number;
  rfc: string;
  razon_social: string;
  regimen_fiscal: string;
  codigo_postal: string;
  email: string | null;
  telefono: string | null;
  direccion: string | null;
  logo_url: string | null;
  serie: string;
  siguiente_folio: number;
  csd_cargado: boolean;
  activo: boolean;
};

export type Cliente = {
  id: number;
  rfc: string;
  razon_social: string;
  tipo_persona: "fisica" | "moral";
  regimen_fiscal: string;
  uso_cfdi: string;
  codigo_postal: string;
  email: string | null;
  activo: boolean;
};

export type Producto = {
  id: number;
  categoria_id: number | null;
  codigo: string | null;
  nombre: string;
  descripcion: string | null;
  clave_prod_serv: string;
  clave_unidad: string;
  unidad: string | null;
  precio_unitario: string;
  objeto_imp: string;
  iva_tasa: string | null;
  ieps_tasa: string | null;
  stock: number | null;
  activo: boolean;
};

export type DetalleIn = {
  producto_id: number | null;
  codigo: string | null;
  clave_prod_serv: string;
  clave_unidad: string;
  unidad: string | null;
  descripcion: string;
  cantidad: string;
  precio_unitario: string;
  descuento: string;
  objeto_imp: string;
  iva_tasa: string | null;
  ieps_tasa: string | null;
  ret_isr_tasa: string | null;
  ret_iva_tasa: string | null;
};

export type FacturaIn = {
  emisor_id: number;
  cliente_id: number;
  tipo_comprobante: string;
  uso_cfdi: string;
  forma_pago: string;
  metodo_pago: string;
  moneda: string;
  tipo_cambio: string | null;
  exportacion: string;
  condiciones_pago: string | null;
  observaciones: string | null;
  cfdi_relacionado_uuid: string | null;
  tipo_relacion: string | null;
  detalles: DetalleIn[];
};

export type Factura = Omit<FacturaIn, "detalles"> & {
  id: number;
  serie: string | null;
  folio: number | null;
  estado: "Borrador" | "Emitida" | "Cancelación pendiente" | "Cancelada";
  uuid: string | null;
  fecha_emision: string | null;
  fecha_creacion: string;
  fecha_timbrado: string | null;
  motivo_cancelacion: string | null;
  fecha_cancelacion: string | null;
  subtotal: string;
  descuento: string;
  total_traslados: string;
  total_retenciones: string;
  total: string;
  emisor: Emisor;
  cliente: Cliente;
  detalles: (DetalleIn & { id: number; importe: string; total: string })[];
};

export type Resumen = {
  subtotal: string;
  descuento: string;
  total_traslados: string;
  total_retenciones: string;
  total: string;
  traslados: { impuesto: string; tipo_factor: string; tasa: string | null; base: string; importe: string }[];
  retenciones: { impuesto: string; tipo_factor: string; tasa: string | null; base: string; importe: string }[];
};

export type Usuario = { id: number; email: string; nombre: string; role_names: string[] };
