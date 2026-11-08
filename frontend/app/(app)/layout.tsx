"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { UserContext } from "@/components/UserContext";
import { api, getToken, setToken, Usuario } from "@/lib/api";

const NAV = [
  { href: "/facturas", label: "Facturas" },
  { href: "/clientes", label: "Clientes" },
  { href: "/productos", label: "Productos" },
  { href: "/emisores", label: "Emisores" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<Usuario | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<Usuario>("/api/auth/me").then(setUser).catch(() => router.replace("/login"));
  }, [router]);

  if (!user) return <div className="main muted">Cargando…</div>;

  return (
    <UserContext.Provider value={user}>
      <div className="shell">
        <nav className="sidebar">
          <div className="logo">Factura App</div>
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className={pathname.startsWith(n.href) ? "active" : ""}>
              {n.label}
            </Link>
          ))}
          <div className="user">
            {user.nombre}
            <br />
            {user.role_names.join(", ")}
            <br />
            <button
              className="ghost"
              style={{ padding: 0, marginTop: "0.4rem", color: "#9fb0a8" }}
              onClick={() => {
                setToken(null);
                router.replace("/login");
              }}
            >
              Cerrar sesión
            </button>
          </div>
        </nav>
        <main className="main">{children}</main>
      </div>
    </UserContext.Provider>
  );
}
