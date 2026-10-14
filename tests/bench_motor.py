"""
CRIPTA | Benchmark del motor (Persona A)

    python tests/bench_motor.py
    python tests/bench_motor.py --sizes 10,50,100,250 --repeats 7
    python tests/bench_motor.py --enemigos 100,300,500 --ciclos 60

Tablas: agenda (heap propio vs lista), motor, IA y búsquedas, integración con
las clases reales y ciclo completo de eventos (límite de 20 ms, §5.2).
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


ANCHO = 74


def titulo(texto: str, nota: str = "") -> None:
    print(f"\n{texto}" + (f"  ·  {nota}" if nota else ""))
    print("─" * ANCHO)


def fmt_t(ms: float) -> str:
    """Tiempo legible: µs si es menor a 1 ms."""
    if ms < 0.001:
        return f"{ms * 1000:.2f} µs"
    if ms < 1:
        return f"{ms * 1000:.1f} µs"
    return f"{ms:.2f} ms"


def tabla(encabezado, filas) -> None:
    """Columnas auto-ajustadas: la primera a la izquierda, el resto a la derecha."""
    cols = len(encabezado)
    anchos = [max(len(str(r[c])) for r in [encabezado] + filas) for c in range(cols)]

    def linea(fila):
        celdas = [str(fila[0]).ljust(anchos[0])]
        celdas += [str(fila[c]).rjust(anchos[c]) for c in range(1, cols)]
        return "  " + "   ".join(celdas)

    print(linea(encabezado))
    print("  " + "   ".join("─" * a for a in anchos))
    for fila in filas:
        print(linea(fila))


def registrar(nombre: str, estado: str, detalle: str = "") -> None:
    RESULTADOS.append((nombre, estado, detalle))


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

def bench_agenda(n: int, repeticiones: int) -> dict:
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

    return {
        "Insertar todos": (t_ah, t_li),
        "Consultar mínimo": (t_mh / 1000, t_ml / 1000),
        "Extraer todos": (t_eh, t_el),
        "Buscar un evento": (t_bh / 1000, t_bl / 1000),
    }


def bench_motor_base(n: int, repeticiones: int) -> dict:
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

    return {
        "Programar N eventos": medir_ms(programar, repeticiones),
        "4 cambios de velocidad": medir_ms(cambiar_velocidad, repeticiones),
        "Ejecutar 10 eventos": medir_ms(ciclo, repeticiones),
    }


def bench_ia_busqueda(n: int, repeticiones: int) -> dict:
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

    resultados = {
        "Buscar sala": medir_ms(lambda: motor.buscar_sala(salas, str(cantidad - 1)), repeticiones),
        "Salidas abiertas": medir_ms(lambda: motor.salidas_abiertas(salas[0]), repeticiones),
        "Decisión errante": medir_ms(lambda: motor.salida_errante(enemigo), repeticiones),
        "Decisión rastreador": medir_ms(lambda: motor.salida_rastro(enemigo), repeticiones),
        "Elegir acción (movimiento)": medir_ms(lambda: motor.accion_enemigo(enemigo, jugador), repeticiones),
    }
    # Guardián en la misma sala del jugador: solo la selección de acción.
    enemigo.comportamiento = "guardian"
    enemigo.sala = jugador.sala
    resultados["Elegir acción (ataque)"] = medir_ms(lambda: motor.accion_enemigo(enemigo, jugador), repeticiones)
    return resultados


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
                    motor._salas_contenido_cargado.append(b.id)  # contenido ya cargado
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
                        motor._guardar_estado_trampa("trampa-inst-bench", True)
                        vida_antes = jugador.vida
                        motor.accion_jugador()
                        motor.activar_trampas_de_sala(b)
                        assert jugador.vida == vida_antes - 7
                        assert motor._obtener_estado_trampa("trampa-inst-bench") is False
                        evento = motor.agenda.siguiente()
                        assert evento is not None and evento.tipo == "REARMAR_TRAMPA"
                        assert motor.ejecu_sig_evento() is True
                        assert motor._obtener_estado_trampa("trampa-inst-bench") is True
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

def bench_ciclo_real(tamanos, ciclos: int) -> list:
    """Ciclo completo de eventos entre dos decisiones del jugador (§5.2)."""
    import random
    Jugador, _ = try_import("Modelo.Jugador", "Jugador")
    Enemigo, _ = try_import("Modelo.Enemigo", "Enemigo")
    Sala, _ = try_import("DTOS.SalaEsqueleto", "SalaEsqueleto")
    Salida, _ = try_import("DTOS.Salida", "Salida")
    if not all((Jugador, Enemigo, Sala, Salida)):
        return []

    filas = []
    for k in tamanos:
        salas = [Sala(i, f"s{i}", {}) for i in range(1, 201)]
        for i in range(199):
            salas[i].salidas["E"] = Salida(salas[i + 1].id, False, None, None)
            salas[i + 1].salidas["O"] = Salida(salas[i].id, False, None, None)
        azar = random.Random(2)
        jugador = Jugador("J", 10**9, 10**9, 1, 0, 100, salas[100])
        enemigos = [Enemigo(f"e{i:05d}", 10, 10, 1, 0, azar.choice((80, 100, 150)),
                            azar.choice(("errante", "rastreador", "guardian")),
                            sala=salas[azar.randrange(200)]) for i in range(k)]
        motor = MotorSimulacion(semilla=1)
        tiempos = []
        with silencioso():
            motor.iniciar_partida(jugador, salas, enemigos)
            for e in enemigos:
                motor.activar_enemigo(e)
            for _ in range(ciclos):
                inicio = time.perf_counter_ns()
                motor.ejecutar_accion("esperar")
                tiempos.append((time.perf_counter_ns() - inicio) / 1_000_000)
        tiempos.sort()
        mediana = statistics.median(tiempos)
        p95 = tiempos[min(len(tiempos) - 1, int(len(tiempos) * 0.95))]
        estado = "✓" if p95 < 20 else ("~" if mediana < 20 else "✗")
        filas.append((k, mediana, p95, estado))
    return filas


def imprimir_integracion() -> None:
    importaciones = [r for r in RESULTADOS if r[0].startswith("Importación")]
    pruebas = [r for r in RESULTADOS if not r[0].startswith("Importación")]
    fallos_imp = [r for r in importaciones if r[1] != OK]

    titulo("INTEGRACIÓN CON CLASES REALES")
    if not fallos_imp:
        print(f"  Importaciones: {len(importaciones)}/{len(importaciones)} ✓\n")
    else:
        for nombre, _, detalle in fallos_imp:
            print(f"  ✗ {nombre}: {detalle}")
        print()

    simbolo = {OK: "✓", FAIL: "✗", SKIP: "–"}
    filas = []
    for nombre, estado, detalle in pruebas:
        tiempo = detalle if estado == OK else detalle[:34]
        filas.append((nombre.split(":")[0], simbolo.get(estado, "·"), tiempo.replace(" ms/op", " ms")))
    tabla(("Prueba", "", "Tiempo / error"), filas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark del motor (Persona A) - CRIPTA")
    parser.add_argument("--sizes", default="10,50,100,250",
                        help="Tamaños N separados por comas (por defecto: 10,50,100,250)")
    parser.add_argument("--repeats", type=int, default=5,
                        help="Repeticiones por medición (por defecto: 5)")
    parser.add_argument("--enemigos", default="100,300,500,1000",
                        help="Enemigos activos para el ciclo completo (por defecto: 100,300,500,1000)")
    parser.add_argument("--ciclos", type=int, default=60,
                        help="Ciclos medidos por tamaño (por defecto: 60)")
    args = parser.parse_args()
    try:
        sizes = [int(x.strip()) for x in args.sizes.split(",") if x.strip()]
        enemigos = [int(x.strip()) for x in args.enemigos.split(",") if x.strip()]
        if not sizes or any(x < 1 for x in sizes) or not enemigos or any(x < 1 for x in enemigos):
            raise ValueError
    except ValueError:
        parser.error("--sizes y --enemigos deben contener enteros positivos separados por comas")
    if args.repeats < 1 or args.ciclos < 1:
        parser.error("--repeats y --ciclos deben ser al menos 1")

    print("\n" + "═" * ANCHO)
    print("  CRIPTA · Benchmark del motor (Persona A)")
    print(f"  {args.repeats} repeticiones · N = {', '.join(map(str, sizes))} · mediana")
    print("═" * ANCHO)

    agenda = [bench_agenda(n, args.repeats) for n in sizes]
    base = [bench_motor_base(n, args.repeats) for n in sizes]
    ia = [bench_ia_busqueda(n, args.repeats) for n in sizes]
    columnas = [f"N={n}" for n in sizes]

    titulo("AGENDA DE EVENTOS", "heap propio vs lista · menor es mejor")
    filas = []
    for op in agenda[0]:
        heap = [fmt_t(r[op][0]) for r in agenda]
        lista = [fmt_t(r[op][1]) for r in agenda]
        razon = agenda[-1][op][1] / agenda[-1][op][0] if agenda[-1][op][0] else 1
        ventaja = f"heap {razon:.1f}×" if razon >= 1 else f"lista {1 / razon:.1f}×"
        filas.append([op, "heap", *heap, ventaja])
        filas.append(["", "lista", *lista, ""])
    tabla(["Operación", "", *columnas, f"ventaja @N={sizes[-1]}"], filas)

    titulo("MOTOR", "eventos sintéticos: agenda + reloj + historial")
    tabla(["Operación", *columnas],
          [[op, *[fmt_t(r[op]) for r in base]] for op in base[0]])

    titulo("IA Y BÚSQUEDAS", "por decisión · columnas = salas de la cripta")
    tabla(["Operación", *[f"{n} salas" for n in sizes]],
          [[op, *[fmt_t(r[op]) for r in ia]] for op in ia[0]])

    with silencioso():
        bench_integracion(args.repeats)
    imprimir_integracion()

    ciclo = bench_ciclo_real(enemigos, args.ciclos)
    titulo("CICLO COMPLETO ENTRE DECISIONES", "límite §5.2: 20 ms · todos los enemigos actuando")
    if ciclo:
        tabla(("Enemigos activos", "Mediana", "p95", ""),
              [(k, fmt_t(m), fmt_t(p), e) for k, m, p, e in ciclo])
        print("\n  ✓ p95 < 20 ms   ~ solo la mediana   ✗ no cumple")
    else:
        print("  No se pudieron importar las clases reales.")

    ok = sum(1 for r in RESULTADOS if r[1] == OK and not r[0].startswith("Importación"))
    total = sum(1 for r in RESULTADOS if not r[0].startswith("Importación"))
    cumple = [k for k, _, p, _ in ciclo if p < 20]
    print("\n" + "═" * ANCHO)
    print(f"  Integración {ok}/{total} ✓"
          + (f"  ·  ciclo < 20 ms hasta {max(cumple)} enemigos" if cumple else "  ·  ciclo: ningún tamaño cumple"))
    print("═" * ANCHO + "\n")


if __name__ == "__main__":
    main()