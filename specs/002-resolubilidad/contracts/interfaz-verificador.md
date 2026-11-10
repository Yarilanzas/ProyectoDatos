# Contrato: interfaz entre capas de la verificación

**FR**: FR-001 a FR-023 | Firmas públicas usadas por otras personas: avisar al grupo antes de cambiarlas.

## Modelo — `Modelo/Resolubilidad.py` (nuevo)

```python
def verificar(cripta_id: str,
              sala_inicial: int,
              sala_salida: int,
              llave_salida: str,
              esqueleto: list[SalaEsqueleto],
              ubicaciones: list[UbicacionLlave]) -> ResultadoVerificacion
```

- Pura: sin red, archivos, consola, `random` ni reloj (Principio II, FR-023). No modifica sus argumentos.
- Importa solo `DTOS/` (entradas y resultado), `Modelo/ordenamiento.merge_sort` y `Modelo/Estructuras.Queue`
  (Principio II: `Modelo/` no importa adaptadores; lo comprueba T016).
- Determinista: mismo contenido en cualquier orden → mismo resultado (FR-013).
- Lanza `ValueError` si un id de sala no es un entero no negativo.
- Complejidad: O(S + E + M log M) para el veredicto y el orden; más O(Σ zonas) para las dependencias cuando no es
  resoluble (ver [data-model.md](../data-model.md)).

Funciones auxiliares del mismo módulo, públicas para las pruebas y el bench (no para otras capas):

```python
class IndiceLlaves:      construir(menciones) / numero(id) / id_de(n) / cantidad()
class GrafoSalas:        desde(esqueleto, indice, ubicaciones)
def recorrer(grafo, indice, sala_inicial) -> EstadoRecorrido
def calcular_dependencias(grafo, indice, estado) -> list[int]      # depende_de
def hallar_ciclos(depende_de, no_obtenible) -> list[list[int]]
```

## DTO — `DTOS/ResultadoVerificacion.py` (nuevo)

Campos en [data-model.md §3](../data-model.md#3-resultado-dtosresultadoverificacionpy-nuevo). Solo datos; sin lógica de
juego.

## Gestor — `Gestor/PreparadorPartida.py`

```python
def verificar_cripta(cripta_id: str, gestor: GestorDatos) -> ResultadoVerificacion
```

1. `detalles = gestor.obtener_detalles(cripta_id)`
2. fijar el presupuesto en la fuente (mismo paso que `_crear_motor`, extraído a una función común)
3. `esqueleto = gestor.obtener_esqueleto(cripta_id)`
4. `ubicaciones = gestor.obtener_llaves(cripta_id)`
5. `return Resolubilidad.verificar(...)`

Propaga sin capturar los errores de la fuente (`ErrorCliente` y subclases, `RuntimeError` offline).

`GestorDatos.obtener_llaves(id_cripta) -> list[UbicacionLlave]`: ver [fuente-llaves.md](fuente-llaves.md).

## Controlador — `Controlador/ControladorPartida.py`

```python
class CriptaNoResoluble(Exception):
    resultado: ResultadoVerificacion      # mensaje: "La cripta <id> no es resoluble. Usa --forzar ..."

ControladorPartida.nueva_partida(cripta_id, semilla=None, forzar=False)
```

Orden obligatorio dentro de `nueva_partida`:

```text
resultado = verificar_cripta(...)          # errores de datos se propagan → código 1
si no forzar:
    si resultado.resoluble: vista.mostrar_verificacion(resultado)
    si no: raise CriptaNoResoluble(resultado)      # antes de crear motor y bitácora
motor = preparar_partida(...)
bitácora = BitacoraPartida(...)
```

`cargar(...)` no cambia y no verifica (FR-022).

## Vista — `Vista/VistaConsola.py`

```python
VistaConsola.mostrar_verificacion(resultado: ResultadoVerificacion) -> None
```

Solo da formato según [cli-verificacion.md](cli-verificacion.md). No ordena, no filtra, no decide.

## `main.py`

```text
argumentos nuevos: --verificar ID, --forzar (store_true)

si --verificar (después de --bench y --mostrar-puntajes):
    gestor = crear_gestor(...)
    try: resultado = verificar_cripta(id, gestor)
    except (ValueError, RuntimeError, OSError) as e: mostrar_error; return 1
    vista.mostrar_verificacion(resultado); return 0

partida nueva:
    controlador.nueva_partida(cripta_id, semilla, forzar=argumentos.forzar)
    except CriptaNoResoluble as e: mostrar_error(str(e)); mostrar_verificacion(e.resultado); return 1
```

`CriptaNoResoluble` no hereda de `ValueError`, `RuntimeError` ni `OSError`, para que nunca la capture el manejo
genérico.

## Bench — `tests/bench_resolubilidad.py` (nuevo)

```python
def correr_bench() -> None   # imprime y escribe resultados_bench_resolubilidad.txt
```

Llamado desde la rama `--bench` de `main.py`, después de los bench existentes.
