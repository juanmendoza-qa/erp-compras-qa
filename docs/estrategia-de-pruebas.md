# Estrategia de pruebas: flujo de compras a pago en ERPNext

| | |
|---|---|
| Proyecto | erp-compras-qa |
| Sistema bajo prueba | ERPNext v16.55.0, instancia local en Docker |
| Autor | Juan Mendoza |
| Revisión | Khris |
| Estado | Borrador v0.1, 15-11-2026 |

## 1. Objetivo

Detectar, antes que el usuario, los defectos del flujo de compras que cuestan dinero o descuadran el inventario. La estrategia prioriza por riesgo de negocio: no busca probar todas las pantallas, sino las reglas que protegen el stock, la deuda con proveedores y la trazabilidad entre documentos.

## 2. Alcance

El flujo cubierto es **orden de compra → recepción → factura de compra → stock**, para una empresa (Compras QA SpA), una bodega (Stores - CQS), moneda CLP e ítems con control de stock.

Cada flecha del flujo es una regla de negocio que puede fallar:

- Orden → recepción: solo se recibe lo que se pidió, y lo pendiente sigue pendiente.
- Recepción → factura: solo se paga lo que se recibió, al precio acordado.
- Recepción → stock: lo que entra a bodega es exactamente lo recibido, y una anulación lo revierte.

## 3. Riesgos de negocio

Impacto y probabilidad en escala alta, media o baja. La prioridad ordena el trabajo de automatización.

| ID | Riesgo | Impacto en el negocio | Impacto | Prob. | Prioridad |
|---|---|---|---|---|---|
| R1 | Se recibe más de lo pedido sin control | Stock y deuda inflados; se paga mercadería no solicitada | Alto | Media | 1 |
| R2 | Una recepción parcial cierra la orden o pierde el saldo pendiente | Mercadería que nunca llega y nadie reclama | Alto | Media | 1 |
| R3 | Se factura distinto de lo recibido o de lo pedido (cantidad o precio) | Pago en exceso al proveedor | Alto | Media | 1 |
| R4 | El stock no coincide con la suma de sus movimientos | Inventario no confiable; quiebres o sobrecompra | Alto | Baja | 2 |
| R5 | Totales mal calculados (cantidad por precio, impuestos, redondeo en CLP) | Montos erróneos en órdenes y facturas | Alto | Baja | 2 |
| R6 | Anular un documento no revierte sus efectos | Stock o saldos fantasma tras una corrección | Medio | Media | 2 |
| R7 | Un borrador produce efectos, o un documento confirmado se puede alterar | Pérdida de trazabilidad y de control de aprobación | Medio | Baja | 3 |
| R8 | Se aceptan cantidades o precios inválidos (cero, negativos, fuera de rango) | Documentos sin sentido que contaminan reportes | Medio | Media | 3 |
| R9 | Una acción en compras modifica datos maestros sin aviso | Precios de lista alterados por una orden puntual | Bajo | Alta | 3 |

R9 nace de una observación real en esta instancia: al guardar la primera orden, el sistema creó precios en la lista "Standard Buying" para ambos ítems. Queda por decidir si es comportamiento esperado o hallazgo.

> **Por completar con experiencia propia:** para R1, R2 y R3, agregar un caso real de operación (qué pasó, cuánto costó, cómo se detectó). Es lo que distingue esta lista de una genérica.

## 4. Enfoque por nivel

La mayor parte de las pruebas va por API, pocas por interfaz y un grupo pequeño de consultas SQL verifica lo que ninguna de las dos ve.

| Nivel | Qué se prueba ahí | Por qué en ese nivel |
|---|---|---|
| API (pytest + requests) | Reglas de negocio R1 a R3, R5 a R8; validaciones de campos; contrato de las respuestas clave | Las reglas viven en el servidor, no en la pantalla. Es rápido, estable y permite muchos casos de datos |
| UI (Playwright) | Tres a cinco flujos críticos de punta a punta: crear orden, recibir, facturar, consultar stock | Confirma que un usuario puede completar el proceso. Es lento y frágil, por eso se limita a lo esencial |
| SQL | Consistencia R4: stock contra movimientos, montos de factura contra recepción | Verifica el estado real de los datos, incluso cuando API e interfaz responden bien |

Una regla ya cubierta por API no se repite en UI.

## 5. Casos priorizados

| Caso | Riesgo | Qué verifica | Técnica de diseño | Nivel |
|---|---|---|---|---|
| C01 | R1 | Recepción por la cantidad exacta, una unidad más y muy por encima de lo pedido | Valores límite | API |
| C02 | R2 | Recepción parcial deja la orden abierta con el saldo correcto; la segunda recepción la completa | Transición de estados | API |
| C03 | R3 | Factura por más cantidad que la recibida | Valores límite | API |
| C04 | R3 | Factura con precio distinto al de la orden | Clases de equivalencia | API |
| C05 | R5 | Total de la orden con una y varias líneas, precios altos y cantidades grandes, sin decimales en CLP | Clases de equivalencia y valores límite | API |
| C06 | R8 | Cantidad cero, negativa y no numérica; precio negativo. Un solo campo inválido por caso | Clases de equivalencia | API |
| C07 | R7 | Orden en borrador no permite recepción; orden confirmada no admite cambio de cantidades | Transición de estados | API |
| C08 | R6 | Anular una recepción devuelve el stock y reabre el saldo de la orden | Transición de estados | API + SQL |
| C09 | R4 | Tras cada flujo, el stock del ítem es igual a la suma de sus movimientos | Conciliación | SQL |
| C10 | R1 a R3 | Flujo completo orden, recepción y factura desde la interfaz | Caso de uso | UI |
| C11 | R9 | Guardar una orden con precio nuevo y revisar la lista de precios | Exploratoria, luego regresión | API |

Los casos negativos cambian un solo campo respecto del caso válido, para que una falla tenga una única causa posible.

## 6. Datos y ambiente

- **Ambiente:** ERPNext local con `docker compose`, reproducible desde cero con un comando. El pipeline de GitHub Actions levanta su propia instancia.
- **Datos maestros base:** un proveedor y dos ítems (`TORN-M8`, `TUER-M8`), creados por fixtures si no existen.
- **Datos transaccionales:** cada prueba crea sus propios documentos y los limpia al terminar. Ninguna prueba depende de otra ni del orden de ejecución.
- **Limpieza:** un documento confirmado debe anularse antes de borrarse; el procedimiento exacto se confirma en la instancia durante la semana 2.
- **Configuración:** URL y credenciales por variables de entorno, con `.env.example` en el repo y `.env` fuera de él.

## 7. Defectos y criterios de salida

- Cada hallazgo es un issue en GitHub con pasos, resultado esperado y obtenido, severidad y riesgo asociado. Su prueba queda marcada como `xfail` con el enlace al issue.
- Antes de reportar, se contrasta con la configuración: varias reglas de ERPNext son parametrizables y un comportamiento permisivo puede ser un ajuste, no un defecto.

La suite se considera lista para publicar (semana 6) cuando:

1. Los riesgos de prioridad 1 y 2 tienen al menos un caso automatizado cada uno.
2. El pipeline corre en verde, o en rojo solo por defectos documentados como `xfail`.
3. Un tercero puede clonar el repo, levantar el sistema y ejecutar la suite siguiendo el README.

## 8. Fuera del alcance

| Qué queda fuera | Por qué |
|---|---|
| Pagos, conciliación bancaria y contabilidad detallada | Amplía el dominio más allá de las seis semanas; el riesgo de pago se cubre en la factura |
| Permisos y roles | Riesgo real, pero de otra naturaleza; se evalúa después del proyecto 1 |
| Rendimiento y carga | Se aborda en el proyecto 2 con k6 |
| Multimoneda, multiempresa, lotes y series | La instancia usa una empresa, CLP e ítems simples |
| Impuestos chilenos y documentos tributarios | Requiere configuración fiscal que no es objetivo del proyecto |
| Módulos de ventas, manufactura y proyectos | No pertenecen al flujo de compras |

## 9. Supuestos por confirmar en la instancia

Estos puntos condicionan los resultados esperados de C01, C03, C04 y C08. Se confirman en la semana 1 recorriendo el flujo a mano.

- Tolerancia de sobre-recepción y sobre-facturación: existe como porcentaje configurable por ítem y a nivel global. Falta registrar el valor vigente.
- Si el sistema exige recepción antes de facturar o permite facturar directo desde la orden.
- Si el stock negativo está permitido o bloqueado.
- Cómo trata el sistema un precio de factura distinto al de la orden: lo bloquea, lo advierte o lo acepta.
- Estados exactos por los que pasa la orden entre confirmada, recibida y facturada.
