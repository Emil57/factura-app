"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = new URLSearchParams({ username: email, password });
      const res = await api<{ access_token: string }>("/api/auth/token", {
        method: "POST",
        body,
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      setToken(res.access_token);
      router.replace("/facturas");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <form className="card" onSubmit={submit}>
        <h1 style={{ marginBottom: "0.3rem" }}>Factura App</h1>
        <p className="muted" style={{ marginTop: 0, marginBottom: "1.4rem" }}>CFDI 4.0 para cualquier contribuyente</p>
        {error && <div className="alert error">{error}</div>}
        <div style={{ display: "grid", gap: "0.9rem" }}>
          <label>
            Correo
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
          </label>
          <label>
            Contraseña
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <button className="primary" disabled={busy} style={{ justifyContent: "center" }}>
            {busy ? "Entrando…" : "Entrar"}
          </button>
        </div>
      </form>
    </div>
  );
}
