# Roadmap

Estado actual (MVP): emisores, clientes, productos, facturas CFDI 4.0 (borrador → timbrado → XML/PDF → cancelación), motor de impuestos con retenciones, PAC simulado y Facturama Multiemisor.

## 1. Antes de usarla en producción

- [ ] **Prueba de punta a punta**: `docker compose up`, flujo completo con el PAC simulado y después timbrado en el sandbox de Facturama. Confirmar:
  - [ ] Ruta de descarga del PDF en Multiemisor (`/cfdi/pdf/issuedLite/{id}`).
  - [ ] Cómo se envía el IVA exento (hoy `"IVA Exento"`).
- [ ] **Pagos y Complemento de Recepción de Pagos 2.0**: obligatorio para facturas PPD. Implementar las tablas `Pagos` y `MetodosPago` de `docs/db.txt`, registrar parcialidades y saldo insoluto, y timbrar el REP.
- [ ] **Catálogos SAT completos**: buscador de ClaveProdServ (~52,000 claves) y ClaveUnidad, en lugar de texto libre.
- [ ] **Migraciones con Alembic**: hoy las tablas se crean al iniciar la app.
- [ ] **Seguridad**: `JWT_SECRET` y contraseña de admin reales, límite de intentos de login, HTTPS, credenciales del PAC en un gestor de secretos.

## 2. Importante

- [ ] **Notas de crédito**: botón "Crear nota de crédito" desde una factura emitida, con la relación (tipo 01) llenada automáticamente.
- [ ] **Factura global configurable**: periodicidad diaria, semanal, quincenal, mensual o bimestral (hoy siempre mensual).
- [ ] **Envío por correo** del XML y PDF al cliente al timbrar.
- [ ] **PDF propio** con logo y diseño personalizado, que funcione también con el PAC simulado.
- [ ] **Pantalla de usuarios y roles** (la API ya lo soporta).
- [ ] **Avisos de vencimiento del CSD** (vigencia de 4 años).

## 3. Después

- [ ] **Dashboard**: facturado por mes, pagos pendientes, IVA y retenciones por declarar.
- [ ] **Complementos adicionales**: comercio exterior (exportación 02), Carta Porte, nómina.
- [ ] **Pruebas de integración** de la API y CI con GitHub Actions.
- [ ] **Alta de clientes desde la Constancia de Situación Fiscal** (lectura del PDF).
- [ ] **Multiempresa**: que cada cuenta vea solo sus propios emisores y facturas.

## 4. Funcionalidades por agregar

**Facturación**
- [ ] Duplicar una factura existente como nuevo borrador.
- [ ] Facturas recurrentes (rentas, igualas, suscripciones) generadas automáticamente cada mes.
- [ ] Cotizaciones que se convierten en factura con un clic.
- [ ] Autofacturación: portal donde el cliente captura su ticket y sus datos fiscales.
- [ ] CFDI de Retenciones e información de pagos (constancias de retenciones).
- [ ] Anticipos (factura de anticipo + aplicación con nota de crédito).

**Clientes y productos**
- [ ] Importación masiva de clientes y productos desde CSV/Excel.
- [ ] Verificación del RFC del cliente en la lista de contribuyentes del SAT (LCO) y aviso si aparece en la lista 69-B.
- [ ] Pantalla de categorías e inventario: descontar `stock` al timbrar y avisar cuando se agote.
- [ ] Historial por cliente: facturas, pagos y saldo pendiente.

**Cobranza y reportes**
- [ ] Estado de cuenta por cliente y antigüedad de saldos.
- [ ] Recordatorios de pago por correo para facturas vencidas.
- [ ] Exportar facturas y reportes a Excel/CSV.
- [ ] Tipo de cambio automático del DOF/Banxico para facturas en USD o EUR.
- [ ] Descarga masiva de XML en ZIP por periodo.

**Plataforma**
- [ ] Bitácora visible en la app (quién hizo qué y cuándo).
- [ ] Recuperación de contraseña por correo.
- [ ] Modo oscuro y vista móvil optimizada.
- [ ] Segundo PAC (Finkok) como respaldo si Facturama no responde.

## Orden sugerido

1. Prueba de punta a punta.
2. Pagos y Complemento de Pago.
3. Catálogos SAT y migraciones.

Con esos tres puntos la app queda lista para facturar en real.
