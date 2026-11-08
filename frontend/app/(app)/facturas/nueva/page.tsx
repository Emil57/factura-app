"use client";

import { useRouter } from "next/navigation";
import InvoiceEditor from "@/components/InvoiceEditor";

export default function NuevaFacturaPage() {
  const router = useRouter();
  return (
    <>
      <div className="page-head"><h1>Nueva factura</h1></div>
      <InvoiceEditor onSaved={(f) => router.push(`/facturas/${f.id}`)} />
    </>
  );
}
