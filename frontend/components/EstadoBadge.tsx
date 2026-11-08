export default function EstadoBadge({ estado }: { estado: string }) {
  const cls = estado === "Cancelación pendiente" ? "pendiente" : estado;
  return <span className={`badge ${cls}`}>{estado}</span>;
}
