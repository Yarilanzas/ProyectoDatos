# Contrato: ubicación de las llaves en la fuente de datos

**FR**: FR-024, FR-025, FR-026, FR-028 | Contrato compartido (adaptadores de datos): avisar al grupo antes de cambiarlo.

## Servicio

`GET /criptas/<id>/llaves` (formato observado el 2026-11-09):

```json
{
  "llaves": [
    {"id": "llave_a", "sala": 2},
    {"id": "llave_b", "sala": 16, "enemigo": "e-8"}
  ]
}
```

| Campo | Tipo | Obligatorio | Significado |
|-------|------|-------------|-------------|
| `id` | texto | sí | identificador de la llave |
| `sala` | entero | sí | sala donde está, o donde inicia el enemigo que la suelta (FR-003) |
| `enemigo` | texto | no | instancia del enemigo que la suelta |

- Una llave puede aparecer varias veces (varias ubicaciones).
- Falta `llaves` → `RespuestaInvalidaError` (ya implementado).
- Una entrada sin `id` o sin `sala` → `RespuestaInvalidaError(ruta, "entrada de llave sin 'id' o 'sala'")`.
- Una `sala` que no existe en el esqueleto **no** es error de lectura: la verificación la reporta (Edge Cases).

## Interfaz común (red y offline, FR-028)

```python
FuenteDatos.obtener_llaves_cripta(id_cripta) -> list[UbicacionLlave]   # ya existe
```

Una solicitud por llamada; con red cuenta para `presupuesto_solicitudes` y respeta el límite también en los reintentos
(FR-026, `_hacer_solicitud`).

## Paquete offline

Archivo nuevo por cripta, con el mismo cuerpo que el servicio:

```text
<paquete>/
└── criptas/
    └── <id>/
        ├── salas.json
        ├── contenido.json
        ├── version.json
        └── llaves.json      ← nuevo
```

Si falta: `RuntimeError("Falta el archivo para /criptas/<id>/llaves: <ruta>")` (ya lo lanza `FuenteDatosOffline`),
informado con `! Error: ...` y código 1 (US5.3). Los generadores de paquetes de las pruebas
(`tests/utiles_niebla.py`, `tests/test_integracion.py` y cualquier otro que escriba `salas.json`) MUST escribir
también `llaves.json`, o las partidas nuevas de esas pruebas dejarán de iniciar (spec, Assumptions). El README
documenta el archivo (FR-031).

## Caché en disco

`GestorDatos.obtener_llaves(id_cripta) -> list[UbicacionLlave]`

```json
// datos_locales/llaves_<id>.json
{"formato": "CRIPTA-LLAVES", "version_formato": 1, "version": "<versión de la cripta>", "llaves": [{"id": "...", "sala": 2, "enemigo": null}]}
```

- Se usa solo si `formato`, `version_formato` y `version` coinciden con los actuales; si no, se pide a la fuente y se reescribe.
- Mismo manejo que `esqueleto_<id>.json` y `contenido_<id>.json` (`AlmacenamientoLocalApi`); a diferencia de ellos, lleva identificador y versión de formato (Principio VI).
- El resultado no depende de que haya caché (FR-013).

## Orden de solicitudes de una verificación

```text
1. detalles     GET /criptas/<id>              (memorizado por el gestor)
2. fijar presupuesto con detalles.presupuesto_solicitudes
3. versión      GET /criptas/<id>/version      (memorizada)
4. esqueleto    GET /criptas/<id>/salas?pagina=n   (0 solicitudes si hay caché válida)
5. llaves       GET /criptas/<id>/llaves           (0 solicitudes si hay caché válida)
```

Si la partida inicia después en el mismo proceso, `preparar_partida` reutiliza 1, 3 y 4.
