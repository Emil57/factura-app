import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Factura App",
  description: "Emisión de CFDI 4.0 para cualquier contribuyente",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-MX">
      <body>{children}</body>
    </html>
  );
}
