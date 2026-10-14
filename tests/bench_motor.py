"""
CRIPTA | BENCHMARK INTEGRAL DE PERSONA A
========================================

Ejecución desde la raíz:
    python tests/bench_motor.py
    python tests/bench_motor.py --sizes 10,50,100,250 --repeats 7

Mide:
- Agenda: insertar, consultar mínimo, extraer, buscar identidad.
- Motor: programar eventos, cambio de velocidad, ejecutar eventos, avance de reloj.
- IA: decisiones guardian/errante/rastreador, salidas y rastros.
- Movimiento: jugador y enemigos (si las clases reales del proyecto se pueden construir).
- Combate: ataque y cancelación de evento por muerte (si se pueden construir actores reales).
- Trampas: activación y rearme (si hay fixtures/datos compatibles).
- Retroceso: coste de abrir/cerrar intervalos y deshacer (según API de Historial).
- Contenido y fichas: carga y búsqueda (requiere GestorDatos/configuración real).

El benchmark intenta usar clases reales del proyecto. Cuando una integración no puede
construirse sin datos específicos, la marca como NO EJECUTADA y muestra la razón:
no inventa resultados ni presenta micropruebas como pruebas de integración.

Nota: las pruebas de ciclo real necesitan constructores/datos de tu proyecto. Este script
descubre algunos constructores comunes, pero puede requerir adaptar la sección de fixtures
a las firmas exactas de Sala/Jugador/Enemigo/Contenido/GestorDatos de tu repositorio.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import statistics
import sys
import time
import traceback
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from Modelo.MotorSimulacion import MotorSimulacion
    from Modelo.Evento import Evento
    from Modelo.AgendaEventos import AgendaEventos
except Exception as exc:
    print("\n[ERROR] No se pudieron importar las clases base del proyecto.")
    print(f"Detalle: {type(exc).__name__}: {exc}")
    raise SystemExit(2)


# ───────────────────────── Utilidades de presentación ─────────────────────────

OK = "OK"
FAIL = "FALLO"
SKIP = "NO EJECUTADA"
RESULTADOS = []


def medir_ms(funcion: Callable[[], object], repeticiones: int = 5) -> float:
    valores = []
    for _ in range(repeticiones):
        inicio = time.perf_counter_ns()
        funcion()
        valores.append((time.perf_counter_ns() - inicio) / 1_000_000)
    return statistics.median(valores)


def medir_us(funcion: Callable[[], object], repeticiones: int = 5) -> float:
    return medir_ms(funcion, repeticiones) * 1000


def seccion(titulo: str) -> None:
    print(f"\n{titulo}")


def metrica(nombre: str, valor: str) -> None:
    print(f"  {nombre:<34} {valor:>14}")


def pie() -> None:
    pass


def registrar(nombre: str, estado: str, detalle: str = "") -> None:
    RESULTADOS.append((nombre, estado, detalle))
    simbolo = {"OK": "✓", "FALLO": "✗", "NO EJECUTADA": "–"}.get(estado, "·")
    extra = f" — {detalle}" if detalle else ""
    print(f"  [{simbolo}] {nombre}: {estado}{extra}")


@contextlib.contextmanager
def silencioso():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield


# ───────────────────────── Fixtures simples para micropruebas ─────────────────

class SalaBench:
    def __init__(self, id_sala):
        self.id = str(id_sala)
        self.salidas = {}
        self.rastro = None


class SalidaBench:
    def __init__(self, destino, cerrada=False):
        self.sala_destino = str(destino)
        self.cerrada = cerrada


class ActorBench:
    def __init__(self, identificador, velocidad=100, vida=100, sala=None):
        self.id = str(identificador)
        self.velocidad = velocidad
        self.vida = vida
        self.vivo = True
        self.sala = sala
        self.tiempo_siguiente = 0
        self.evento_actual = None
        self.activo = False
        self.comportamiento = "guardian"
        self.ataque = 10
        self.defensa = 0
        self.tipo_id = None
        self.inventario = None

    def esta_vivo(self):
        return self.vivo and self.vida > 0

    def recibir_dano(self, dano):
        self.vida = max(0, self.vida - dano)
        if self.vida == 0:
            self.vivo = False


def try_import(module_name, class_name):
    try:
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


# ───────────────────────── Agenda y motor base ────────────────────────────────

def bench_agenda(n: int, repeticiones: int) -> None:
    def insertar_agenda():
        agenda = AgendaEventos()
        actor = ActorBench("agenda")
        for i in range(n):
            agenda.agregar(Evento(i, i, "BENCH", actor))
        return agenda

    def insertar_lista():
        actor = ActorBench("agenda")
        return [Evento(i, i, "BENCH", actor) for i in range(n)]

    t_ah = medir_ms(insertar_agenda, repeticiones)
    t_li = medir_ms(insertar_lista, repeticiones)
    agenda, eventos = insertar_agenda(), insertar_lista()
    t_mh = medir_us(agenda.siguiente, repeticiones)
    t_ml = medir_us(lambda: min((e for e in eventos if not e.cancelado), default=None), repeticiones)

    def extraer_agenda():
        a = insertar_agenda()
        while a.extraer() is not None:
            pass

    def extraer_lista():
        l = insertar_lista()
        while l:
            l.remove(min(l))

    t_eh = medir_ms(extraer_agenda, repeticiones)
    t_el = medir_ms(extraer_lista, repeticiones)
    objetivo_a, objetivo_l = agenda.heap[n // 2], eventos[n // 2]
    t_bh = medir_us(lambda: agenda.contiene(objetivo_a), repeticiones)
    t_bl = medir_us(lambda: any(e is objetivo_l for e in eventos), repeticiones)

    seccion(f"AGENDA DE EVENTOS · N={n}")
    metrica("Insertar todos · AgendaEventos", f"{t_ah:.3f} ms")
    metrica("Insertar todos · lista", f"{t_li:.3f} ms")
    metrica("Consultar mínimo · AgendaEventos", f"{t_mh:.3f} µs")
    metrica("Consultar mínimo · lista", f"{t_ml:.3f} µs")
    metrica("Extraer todos · AgendaEventos", f"{t_eh:.3f} ms")
    metrica("Extraer todos · lista", f"{t_el:.3f} ms")
    metrica("Buscar identidad · AgendaEventos", f"{t_bh:.3f} µs")
    metrica("Buscar identidad · lista", f"{t_bl:.3f} µs")
    pie()


def bench_motor_base(n: int, repeticiones: int) -> None:
    def programar():
        motor = MotorSimulacion(semilla=123)
        actor = ActorBench("actor")
        for i in range(n):
            motor.programar_evento(i + 1, "BENCH", actor)

    def cambiar_velocidad():
        motor = MotorSimulacion(semilla=123)
        actor = ActorBench("actor")
        actor.tiempo_siguiente = 1000
        actor.evento_actual = motor.programar_evento(1000, "ACCION_ACTOR", actor)
        for v in (125, 80, 150, 100):
            motor.cambiar_velocidad(actor, v)

    def ciclo():
        motor = MotorSimulacion(semilla=123)
        actor = ActorBench("jugador")
        for i in range(n):
            motor.programar_evento(i + 1, "BENCH", actor)
        with silencioso():
            for _ in range(min(n, 10)):
                if not motor.ejecu_sig_evento():
                    break

    seccion(f"PROGRAMACIÓN Y CICLO SINTÉTICO · N={n}")
    metrica(f"Programar {n} eventos", f"{medir_ms(programar, repeticiones):.3f} ms")
    metrica("Cuatro cambios de velocidad", f"{medir_ms(cambiar_velocidad, repeticiones):.3f} ms")
    metrica(f"Ejecutar hasta {min(n, 10)} eventos", f"{medir_ms(ciclo, repeticiones):.3f} ms")
    metrica("Incluye", "agenda + reloj + historial")
    metrica("No equivale a", "turno real completo")
    pie()


def bench_ia_busqueda(n: int, repeticiones: int) -> None:
    motor = MotorSimulacion(semilla=123)
    cantidad = max(2, n)
    salas = [SalaBench(i) for i in range(cantidad)]
    for i in range(cantidad - 1):
        salas[i].salidas["E"] = SalidaBench(i + 1)
        salas[i + 1].salidas["O"] = SalidaBench(i)
    motor.salas = salas
    enemigo = ActorBench("enemigo", sala=salas[0])
    enemigo.comportamiento = "errante"
    jugador = ActorBench("jugador", sala=salas[-1])
    motor.jugador = jugador
    motor.reloj = cantidad
    for i, sala in enumerate(salas):
        sala.rastro = i

    seccion(f"BÚSQUEDAS E IA · {cantidad} SALAS")
    metrica("Buscar sala", f"{medir_us(lambda: motor.buscar_sala(salas, str(cantidad - 1)), repeticiones):.3f} µs/op")
    metrica("Obtener salidas abiertas", f"{medir_us(lambda: motor.salidas_abiertas(salas[0]), repeticiones):.3f} µs/op")
    metrica("Decisión errante", f"{medir_us(lambda: motor.salida_errante(enemigo), repeticiones):.3f} µs/op")
    metrica("Búsqueda de rastro", f"{medir_us(lambda: motor.salida_rastro(enemigo), repeticiones):.3f} µs/op")
    metrica("Decisión de comportamiento", f"{medir_us(lambda: motor.accion_enemigo(enemigo, jugador), repeticiones):.3f} µs/op")
    # Guardian y ataque en misma sala: mide únicamente la selección de acción.
    enemigo.comportamiento = "guardian"
    enemigo.sala = jugador.sala
    metrica("Decisión guardian/ataque", f"{medir_us(lambda: motor.accion_enemigo(enemigo, jugador), repeticiones):.3f} µs/op")
    pie()


# ───────────────────────── Pruebas de integración con modelos reales ───────────

def intentar_modelos_reales():
    candidatos = {
        "Jugador": ("Modelo.Jugador", "Jugador"),
        "Enemigo": ("Modelo.Enemigo", "Enemigo"),
        "SalaEsqueleto": ("DTOS.SalaEsqueleto", "SalaEsqueleto"),
        "Salida": ("DTOS.Salida", "Salida"),
        "ContenidoSala": ("DTOS.ContenidoSala", "ContenidoSala"),
        "TrampaInstancia": ("DTOS.TrampaInstancia", "TrampaInstancia"),
        "GestorDatos": ("Gestor.GestorDatos", "GestorDatos"),
        "NodoInventario": ("Modelo.Inventario", "NodoInventario"),
        "Historial": ("Modelo.retroceso", "Historial"),
        "FichaCatalogo": ("DTOS.FichaCatalogo", "FichaCatalogo"),
    }
    clases, errores = {}, {}
    for nombre, (modulo, clase) in candidatos.items():
        clases[nombre], error = try_import(modulo, clase)
        if error:
            errores[nombre] = error
    return clases, errores


class FuenteBench:
    """Fuente determinista para probar GestorDatos sin red ni datos externos."""
    def __init__(self, SalaEsqueleto, Salida, ContenidoSala, TrampaInstancia,
                 FichaArma, FichaTrampa):
        self.solicitudes_realizadas = 0
        self.SalaEsqueleto = SalaEsqueleto
        self.Salida = Salida
        self.ContenidoSala = ContenidoSala
        self.TrampaInstancia = TrampaInstancia
        self.fichas = {
            "arma-bench": FichaArma("arma-bench", "arma", "Espada bench", 2, 15, 4),
            "trampa-bench": FichaTrampa("trampa-bench", "trampa", "Dardos bench", 7, 5),
        }

    def obtener_version_catalogo(self):
        self.solicitudes_realizadas += 1
        return "catalogo-bench-v1"

    def obtener_version_cripta(self, id_cripta):
        self.solicitudes_realizadas += 1
        return f"{id_cripta}-v1"

    def obtener_esqueleto_cripta(self, id_cripta):
        self.solicitudes_realizadas += 1
        a = self.SalaEsqueleto(1, "Entrada bench", {})
        b = self.SalaEsqueleto(2, "Sala trampa bench", {})
        a.salidas["E"] = self.Salida(2, False, None, None)
        b.salidas["O"] = self.Salida(1, False, None, None)
        return [a, b]

    def obtener_contenido_sala(self, id_cripta, ids_salas):
        self.solicitudes_realizadas += 1
        resultados = []
        for id_sala in ids_salas:
            if id_sala == 1:
                resultados.append(self.ContenidoSala(
                    1, [], [self.TrampaInstancia("trampa-inst-bench", "trampa-bench")],
                    ["arma-bench"]
                ))
            else:
                resultados.append(self.ContenidoSala(id_sala, [], [], []))
        return resultados

    def obtener_fichas_catalogo(self, ids_fichas):
        self.solicitudes_realizadas += 1
        return [self.fichas[i] for i in ids_fichas if i in self.fichas]


def bench_integracion(repeticiones: int) -> None:
    import tempfile
    from pathlib import Path

    clases, errores = intentar_modelos_reales()
    seccion("INTEGRACIÓN CON CLASES REALES")
    for nombre in ("Jugador", "Enemigo", "SalaEsqueleto", "Salida", "ContenidoSala",
                   "TrampaInstancia", "GestorDatos", "Historial", "NodoInventario"):
        registrar(f"Importación de {nombre}", OK if clases.get(nombre) else FAIL,
                  errores.get(nombre, "") if not clases.get(nombre) else "")

    Jugador = clases.get("Jugador")
    Enemigo = clases.get("Enemigo")
    Sala = clases.get("SalaEsqueleto")
    Salida = clases.get("Salida")
    ContenidoSala = clases.get("ContenidoSala")
    TrampaInstancia = clases.get("TrampaInstancia")
    GestorDatos = clases.get("GestorDatos")
    Nodo = clases.get("NodoInventario")
    retroceso_mod, _ = try_import("Modelo.retroceso", "recoger_reversible")
    FichaArma, _ = try_import("DTOS.FichaCatalogo", "FichaArma")
    FichaTrampa, _ = try_import("DTOS.FichaCatalogo", "FichaTrampa")

    necesarias = (Jugador, Sala, Salida, Nodo)
    if all(necesarias):
        def crear_mundo(gestor=None):
            a = Sala(1, "Entrada", {})
            b = Sala(2, "Cámara", {})
            a.salidas["E"] = Salida(2, False, None, None)
            b.salidas["O"] = Salida(1, False, None, None)
            motor = MotorSimulacion(semilla=777, gestor_datos=gestor)
            jugador = Jugador("J1", 100, 100, 20, 5, 100, a)
            motor.salas = [a, b]
            motor.jugador = jugador
            return motor, jugador, a, b

        # 1. Turno real: inicio de partida y movimiento con agenda.
        try:
            def turno_real():
                motor, jugador, a, b = crear_mundo()
                with silencioso():
                    motor.iniciar_partida(jugador, [a, b], [])
                    assert motor.mover_jugador("E") is True
                assert jugador.sala is b
                assert motor.reloj >= 1
                assert motor.agenda.siguiente() is not None or motor.agenda.esta_vacia()
            t = medir_ms(turno_real, repeticiones)
            registrar("Turno real: iniciar + mover + avanzar eventos", OK, f"{t:.3f} ms/op")
        except Exception as exc:
            registrar("Turno real: iniciar + mover + avanzar eventos", FAIL,
                      f"{type(exc).__name__}: {exc}")

        # 2. Inventario real y ficha activa.
        try:
            def inventario_real():
                motor, jugador, a, _ = crear_mundo()
                objeto = Nodo("obj-1", "arma-bench", "Espada", 2, 20, "arma", 5, 0)
                motor.objetos_suelo = [[a.id, [objeto]]]
                with silencioso():
                    assert motor.recoger_objeto(objeto) is True
                    assert objeto in list(jugador.inventario)
                    assert motor.equipar_objeto() is objeto
                assert jugador.inventario.arma_equipada() is objeto
                assert motor.es_ficha_activa("arma-bench") is True
                with silencioso():
                    soltado = motor.soltar_objeto()
                assert soltado is objeto
                assert objeto not in list(jugador.inventario)
                assert objeto in motor.obtener_objetos_suelo(jugador.sala)
                assert motor.es_ficha_activa("arma-bench") is True
            t = medir_ms(inventario_real, repeticiones)
            registrar("Inventario real: recoger + equipar + soltar", OK, f"{t:.3f} ms/op")
        except Exception as exc:
            registrar("Inventario real: recoger + equipar + soltar", FAIL,
                      f"{type(exc).__name__}: {exc}")

        # 3. Historial real: deshacer la recogida y restaurar suelo/inventario.
        try:
            def retroceso_real():
                motor, jugador, a, _ = crear_mundo()
                objeto = Nodo("obj-2", "gema-bench", "Gema", 1, 10, "tesoro")
                motor.objetos_suelo = [[a.id, [objeto]]]
                with silencioso():
                    assert motor.recoger_objeto(objeto) is True
                assert objeto in list(jugador.inventario)
                assert motor.historial.puede_deshacer()
                assert motor.historial.deshacer_ultimo() is True
                assert objeto not in list(jugador.inventario)
                assert objeto in motor.obtener_objetos_suelo(a)
            t = medir_ms(retroceso_real, repeticiones)
            registrar("Historial real: deshacer recogida", OK, f"{t:.3f} ms/op")
        except Exception as exc:
            registrar("Historial real: deshacer recogida", FAIL,
                      f"{type(exc).__name__}: {exc}")

        # 4. Combate real.
        if Enemigo:
            try:
                def combate_real():
                    motor, jugador, a, _ = crear_mundo()
                    enemigo = Enemigo("E1", 100, 100, 8, 2, 80, "guardian", a, "enemigo-bench")
                    with silencioso():
                        dano = motor.atacar(jugador, enemigo)
                    assert dano >= 1
                    assert enemigo.vida < 100
                t = medir_ms(combate_real, repeticiones)
                registrar("Combate con Jugador/Enemigo reales", OK, f"{t:.3f} ms/op")
            except Exception as exc:
                registrar("Combate con Jugador/Enemigo reales", FAIL,
                          f"{type(exc).__name__}: {exc}")

        # 5. Carga real de contenido + caché + almacenamiento local.
        if all((GestorDatos, ContenidoSala, TrampaInstancia, FichaArma, FichaTrampa)):
            try:
                def gestor_real():
                    with tempfile.TemporaryDirectory(prefix="cripta_bench_") as carpeta:
                        GestorDatos._instancia = None
                        fuente = FuenteBench(Sala, Salida, ContenidoSala, TrampaInstancia,
                                             FichaArma, FichaTrampa)
                        gestor = GestorDatos(fuente, ruta_base=carpeta, cache_size=10)
                        esqueleto = gestor.iniciar_cripta("cripta-bench")
                        assert len(esqueleto) == 2
                        contenido = gestor.asegurar_sala(1)
                        assert contenido is not None and contenido.id_sala == 1
                        assert len(contenido.objetos) == 1
                        llamadas_antes = fuente.solicitudes_realizadas
                        assert gestor.asegurar_sala(1) is contenido
                        # La sala ya está en memoria: no debe pedirla otra vez.
                        assert fuente.solicitudes_realizadas == llamadas_antes
                        ficha = gestor.obtener_ficha("arma-bench")
                        assert ficha is not None and ficha.id == "arma-bench"
                        # La segunda consulta debe salir de caché.
                        fallos = gestor.fallos_cache
                        assert gestor.obtener_ficha("arma-bench") is ficha
                        assert gestor.fallos_cache == fallos
                        GestorDatos._instancia = None
                t = medir_ms(gestor_real, repeticiones)
                registrar("GestorDatos real: precarga + contenido + caché/disco", OK,
                          f"{t:.3f} ms/op")
            except Exception as exc:
                try:
                    GestorDatos._instancia = None
                except Exception:
                    pass
                registrar("GestorDatos real: precarga + contenido + caché/disco", FAIL,
                          f"{type(exc).__name__}: {exc}")

            # 6. Trampa real del catálogo: daño, desarme y rearme por evento.
            try:
                def trampa_real():
                    with tempfile.TemporaryDirectory(prefix="cripta_trampa_bench_") as carpeta:
                        GestorDatos._instancia = None
                        fuente = FuenteBench(Sala, Salida, ContenidoSala, TrampaInstancia,
                                             FichaArma, FichaTrampa)
                        gestor = GestorDatos(fuente, ruta_base=carpeta, cache_size=10)
                        motor, jugador, a, b = crear_mundo(gestor)
                        contenido = ContenidoSala(2, [],
                            [TrampaInstancia("trampa-inst-bench", "trampa-bench")], [])
                        motor.contenidos_salas = [contenido]
                        motor._estado_trampas["trampa-inst-bench"] = True
                        vida_antes = jugador.vida
                        motor.accion_jugador()
                        motor.activar_trampas_de_sala(b)
                        assert jugador.vida == vida_antes - 7
                        assert motor._estado_trampas["trampa-inst-bench"] is False
                        evento = motor.agenda.siguiente()
                        assert evento is not None and evento.tipo == "REARMAR_TRAMPA"
                        assert motor.ejecu_sig_evento() is True
                        assert motor._estado_trampas["trampa-inst-bench"] is True
                        assert jugador.vida == vida_antes - 7
                        GestorDatos._instancia = None
                t = medir_ms(trampa_real, repeticiones)
                registrar("Trampa real: activar + daño + rearme", OK, f"{t:.3f} ms/op")
            except Exception as exc:
                try:
                    GestorDatos._instancia = None
                except Exception:
                    pass
                registrar("Trampa real: activar + daño + rearme", FAIL,
                          f"{type(exc).__name__}: {exc}")

            # 7. Cargar contenido en MotorSimulacion y comprobar fichas activas.
            try:
                def contenido_motor_real():
                    with tempfile.TemporaryDirectory(prefix="cripta_motor_bench_") as carpeta:
                        GestorDatos._instancia = None
                        fuente = FuenteBench(Sala, Salida, ContenidoSala, TrampaInstancia,
                                             FichaArma, FichaTrampa)
                        gestor = GestorDatos(fuente, ruta_base=carpeta, cache_size=10)
                        motor, jugador, a, b = crear_mundo(gestor)
                        motor.cargar_contenido_salas("cripta-bench", [1, 2])
                        assert any(entrada[0] == 1 for entrada in motor.objetos_suelo)
                        assert motor.es_ficha_activa("arma-bench") is True
                        assert motor.es_ficha_activa("trampa-bench") is True
                        GestorDatos._instancia = None
                t = medir_ms(contenido_motor_real, repeticiones)
                registrar("Motor real: cargar contenido + es_ficha_activa", OK,
                          f"{t:.3f} ms/op")
            except Exception as exc:
                try:
                    GestorDatos._instancia = None
                except Exception:
                    pass
                registrar("Motor real: cargar contenido + es_ficha_activa", FAIL,
                          f"{type(exc).__name__}: {exc}")
    else:
        registrar("Integración con modelos reales", FAIL,
                  "No se pudieron importar los modelos requeridos")

def imprimir_resumen() -> None:
    seccion("RESUMEN DE PRUEBAS DE INTEGRACIÓN")
    total_ok = sum(1 for _, estado, _ in RESULTADOS if estado == OK)
    total_fallo = sum(1 for _, estado, _ in RESULTADOS if estado == FAIL)
    total_skip = sum(1 for _, estado, _ in RESULTADOS if estado == SKIP)
    metrica("Pruebas correctas", str(total_ok))
    metrica("Pruebas fallidas", str(total_fallo))
    metrica("Pruebas no ejecutadas", str(total_skip))
    pie()
    if total_fallo:
        print("  Revisar las pruebas fallidas.")
    if total_skip:
        print("  Pendientes: requieren modelos o datos reales compatibles.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark integral de Persona A - CRIPTA")
    parser.add_argument("--sizes", default="10,50,100,250",
                        help="Tamaños separados por comas (por defecto: 10,50,100,250)")
    parser.add_argument("--repeats", type=int, default=5,
                        help="Repeticiones por medición (por defecto: 5)")
    args = parser.parse_args()
    try:
        sizes = [int(x.strip()) for x in args.sizes.split(",") if x.strip()]
        if not sizes or any(x < 1 for x in sizes):
            raise ValueError
    except ValueError:
        parser.error("--sizes debe contener enteros positivos separados por comas")
    if args.repeats < 1:
        parser.error("--repeats debe ser al menos 1")

    print("\n" + "=" * 48)
    print(" CRIPTA | BENCHMARK PERSONA A")
    print(f" Repeticiones: {args.repeats} | N: {', '.join(map(str, sizes))}")
    print("=" * 48)

    for n in sizes:
        bench_agenda(n, args.repeats)
        bench_motor_base(n, args.repeats)
        bench_ia_busqueda(n, args.repeats)

    bench_integracion(args.repeats)
    imprimir_resumen()
    print("\nObjetivo <20 ms: validar con un turno real completo.")
    print("=" * 48 + "\n")


if __name__ == "__main__":
    main()
