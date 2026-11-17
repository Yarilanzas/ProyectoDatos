# evidencia de rendimiento del cazador (spec 003, US5, T061 a T068): M1 a M7.
# Misma estructura que tests/bench_ciclo.py: correr_bench() imprime y escribe resultados_bench_cazador.txt en la raíz,
# con el equipo y la versión de Python. Sin red ni vista; criptas sintéticas deterministas por semilla
# (tests/utiles_terreno.py sobre tests/generador_criptas.py). Cada medición arma su propio motor: ninguna depende del
# estado que deja otra ni del orden en que se corren.
#
#     python -m tests.bench_cazador            todas las mediciones, escribe el archivo
#     python -m tests.bench_cazador M3 M5      solo esas: reemplaza sus bloques en el archivo (no en modo rápido)
#     BENCH_CAZADOR_RAPIDO=1                   menos repeticiones y tamaños (prueba de humo, < 20 s)
#
# Las búsquedas de M4 se cuentan en una pasada aparte, idéntica a la medida (mismas semillas), con primer_paso y
# campo_hacia envueltos por un contador. El motor los llama por nombre de módulo, no por atributo de la instancia, así
# que se envuelven en el espacio de nombres de Modelo.MotorSimulacion con unittest.mock.patch.object, que los restaura
# al salir; no se modifica ningún archivo de Modelo/ y los tiempos se toman sin el contador.

import contextlib
import gc
import os
import platform
import random
import statistics
import sys
import time
from unittest import mock

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import Modelo.MotorSimulacion as modulo_motor
from Modelo.AgendaEventos import AgendaEventos
from Modelo.BusquedaRuta import EspacioBusqueda, campo_hacia
from Modelo.BusquedaRuta import primer_paso as primer_paso_busqueda
from Modelo.ColaPrioridad import ColaPrioridad
from Modelo.Evento import Evento
from tests.bench_motor import fmt_t, silencioso, titulo
from tests.utiles_terreno import armar_motor, cripta_terreno

LIMITE_MS = 20                 # FR-030: ciclo entre dos decisiones del jugador
COCIENTE_MAXIMO = 1.5          # FR-033 / SC-007
ARCHIVO_RESULTADOS = "resultados_bench_cazador.txt"
VARIABLE_RAPIDO = "BENCH_CAZADOR_RAPIDO"

SEMILLA_CRIPTA = 7
SALAS_REFERENCIA = 300         # dimensión de la cripta de referencia (≈ 760 salidas); la publicada aún no existe
RANGO_PEQUENO = 500            # 5 salidas de costo 100
RANGO_GRANDE = 2000            # cubre casi toda la cripta de 300 salas
CAZADORES = 50
VIDA_JUGADOR = 10 ** 9         # el jugador no muere durante los ciclos medidos (como bench_motor.bench_ciclo_real)


def es_rapido():
    return os.environ.get(VARIABLE_RAPIDO) == "1"


def _rapido(rapido):
    return es_rapido() if rapido is None else rapido


# ───────────────────────── medición ─────────────────────────

def p95(tiempos):
    """Mismo criterio que bench_motor.bench_ciclo_real: posición int(0,95·n) de las muestras ordenadas."""
    ordenados = sorted(tiempos)
    return ordenados[min(len(ordenados) - 1, int(len(ordenados) * 0.95))]


def resumen(tiempos):
    return statistics.median(tiempos), p95(tiempos)


def muestras(funcion, cantidad, lote=1):
    """``cantidad`` muestras en ms por llamada: cada muestra cronometra ``lote`` llamadas seguidas y divide."""
    gc.collect()
    tiempos = []
    for _ in range(cantidad):
        inicio = time.perf_counter()
        for _ in range(lote):
            funcion()
        tiempos.append((time.perf_counter() - inicio) * 1000 / lote)
    return tiempos


@contextlib.contextmanager
def contar_busquedas():
    """Cuenta las llamadas a primer_paso y campo_hacia que hace el motor mientras dura el bloque."""
    cuenta = {"primer_paso": 0, "campo_hacia": 0}
    original_paso = modulo_motor.primer_paso
    original_campo = modulo_motor.campo_hacia

    def paso(*args, **kwargs):
        cuenta["primer_paso"] += 1
        return original_paso(*args, **kwargs)

    def campo(*args, **kwargs):
        cuenta["campo_hacia"] += 1
        return original_campo(*args, **kwargs)

    with mock.patch.object(modulo_motor, "primer_paso", paso), mock.patch.object(modulo_motor, "campo_hacia", campo):
        yield cuenta


# ───────────────────────── salida ─────────────────────────

def lineas_tabla(encabezado, filas):
    """Mismo formato que bench_motor.tabla, pero devuelve las líneas para imprimirlas y escribirlas."""
    filas = [[str(c) for c in fila] for fila in filas]
    encabezado = [str(c) for c in encabezado]
    cols = len(encabezado)
    anchos = [max(len(r[c]) for r in [encabezado] + filas) for c in range(cols)]

    def linea(fila):
        celdas = [fila[0].ljust(anchos[0])] + [fila[c].rjust(anchos[c]) for c in range(1, cols)]
        return "  " + "   ".join(celdas)

    return [linea(encabezado), "  " + "   ".join("─" * a for a in anchos)] + [linea(f) for f in filas]


def bloque(nombre, nota, cuerpo):
    """Imprime el bloque con titulo() de bench_motor y devuelve sus líneas para el archivo."""
    titulo(nombre, nota)
    for linea in cuerpo:
        print(linea)
    return ["", f"-{nombre} ({nota})-"] + list(cuerpo)


def cumple(condicion):
    return "cumple" if condicion else "NO cumple"


# ───────────────────────── criptas y motores ─────────────────────────

def _ancho(salas):
    ancho = 1
    while ancho * ancho < salas:
        ancho += 1
    return ancho


def sala_centro(salas):
    """Id de la sala en el centro de la cuadrícula en serpentina de generar_cripta."""
    ancho = _ancho(salas)
    filas = (salas + ancho - 1) // ancho
    fila, columna = filas // 2, ancho // 2
    return fila * ancho + (columna if fila % 2 == 0 else ancho - 1 - columna) + 1


def distancias_hacia(cripta, sala_jugador, cota):
    """Pares (id, distancia hacia el jugador) de las salas a distancia ≤ cota, sin la del jugador, por id.
    Usa un motor propio sin cazadores y un espacio nuevo: no toca ningún motor medido."""
    motor = armar_motor(cripta, sala_jugador, [])
    grafo = motor.grafo_cripta
    espacio = campo_hacia(grafo, motor.jugador.sala, cota, EspacioBusqueda(grafo.cantidad_salas))
    pares = []
    for sala in motor.salas:
        ordinal = grafo.ordinal(sala)
        if espacio.epoca[ordinal] == espacio.epoca_actual and sala.id != sala_jugador:
            pares.append((sala.id, espacio.dist[ordinal]))
    pares.sort()
    return pares


def tamano_region(cripta, sala_jugador, cota):
    """|R|: salas a distancia ≤ cota hacia el jugador, contando la del jugador."""
    return len(distancias_hacia(cripta, sala_jugador, cota)) + 1


def motor_con_cazadores(cripta, sala_jugador, cazadores, estrategia=None):
    """armar_motor + jugador que no muere + todos los cazadores activados con motor.activar_enemigo."""
    motor = armar_motor(cripta, sala_jugador, cazadores)
    motor.jugador.vida_max = VIDA_JUGADOR
    motor.jugador.vida = VIDA_JUGADOR
    if estrategia is not None:
        motor.estrategia_cazador = estrategia
    with silencioso():
        for enemigo in motor.enemigos:
            motor.activar_enemigo(enemigo)
    return motor


def cripta_referencia():
    return cripta_terreno(SEMILLA_CRIPTA, SALAS_REFERENCIA)


def cazadores_en_rango(cripta, sala_jugador, rango, cantidad, semilla):
    """``cantidad`` pares (sala, rango) en salas al azar (semilla) a distancia ≤ rango del jugador."""
    salas = [id_sala for id_sala, _ in distancias_hacia(cripta, sala_jugador, rango)]
    azar = random.Random(semilla)
    return [(azar.choice(salas), rango) for _ in range(cantidad)]


def cazadores_en_cripta(cripta, sala_jugador, rangos, cantidad, semilla):
    """``cantidad`` pares (sala, rango) en salas al azar de toda la cripta (sin la del jugador), rango al azar."""
    azar = random.Random(semilla)
    salas = [s["id"] for s in cripta.salas_json if s["id"] != sala_jugador]
    return [(azar.choice(salas), azar.choice(rangos)) for _ in range(cantidad)]


# ───────────────────────── M1 ─────────────────────────

def medir_m1(rapido=None):
    """M1: decidir un cazador frente a decidir 50 en la misma cripta, estrategia individual (FR-030)."""
    rapido = _rapido(rapido)
    cantidad = 10 if rapido else 40
    cripta = cripta_referencia()
    jugador = sala_centro(SALAS_REFERENCIA)
    motor = motor_con_cazadores(cripta, jugador, cazadores_en_rango(cripta, jugador, RANGO_GRANDE, CAZADORES, 101),
                                estrategia="individual")
    cazadores = list(motor.enemigos)
    uno = cazadores[0]

    def decidir_uno():
        motor.decidir_cazador(uno)

    def decidir_todos():
        for cazador in cazadores:
            motor.decidir_cazador(cazador)

    m1, p1 = resumen(muestras(decidir_uno, cantidad, lote=20))
    m50, p50 = resumen(muestras(decidir_todos, cantidad))
    cuerpo = [
        f"cripta sintética de {SALAS_REFERENCIA} salas (semilla {SEMILLA_CRIPTA}), rango {RANGO_GRANDE}, cazadores "
        f"en salas al azar a distancia ≤ rango, estrategia individual, {cantidad} muestras",
    ] + lineas_tabla(("Cazadores que deciden", "Mediana", "p95", "Por cazador (mediana)"), [
        (1, fmt_t(m1), fmt_t(p1), fmt_t(m1)),
        (CAZADORES, fmt_t(m50), fmt_t(p50), fmt_t(m50 / CAZADORES)),
    ]) + [
        f"cociente 50 / 1 = {m50 / m1:.1f}",
        f"las {CAZADORES} decisiones (sin el resto del ciclo) < {LIMITE_MS} ms en p95: {cumple(p50 < LIMITE_MS)}",
    ]
    return bloque("M1: decisión de un cazador frente a 50", "FR-030", cuerpo)


# ───────────────────────── M2 ─────────────────────────

def medir_m2(rapido=None):
    """M2: ColaPrioridad frente a la agenda del motor y a la búsqueda lineal del mínimo (FR-033)."""
    rapido = _rapido(rapido)
    tamanos = (10, 100, 1000) if rapido else (10, 100, 1000, 10000)
    filas = []
    for n in tamanos:
        azar = random.Random(n)
        prioridades = [azar.randrange(10 * n) for _ in range(n)]
        repeticiones = 3 if rapido else (7 if n <= 1000 else 5)
        repeticiones_lineal = 3 if (rapido or n >= 10000) else 7

        def cola():
            c = ColaPrioridad()
            for i in range(n):
                c.insertar(prioridades[i], i)
            while not c.vacia():
                c.extraer_minimo()

        def agenda():
            a = AgendaEventos()
            for i in range(n):
                a.agregar(Evento(prioridades[i], i, "BENCH"))
            while a.extraer() is not None:
                pass

        def lineal():
            lista = [(prioridades[i], i) for i in range(n)]
            while lista:
                menor = 0
                for j in range(1, len(lista)):
                    if lista[j] < lista[menor]:
                        menor = j
                lista[menor] = lista[-1]
                lista.pop()

        mc, pc = resumen(muestras(cola, repeticiones))
        ma, pa = resumen(muestras(agenda, repeticiones))
        ml, pl = resumen(muestras(lineal, repeticiones_lineal))
        filas.append((n, fmt_t(mc), fmt_t(pc), fmt_t(ma), fmt_t(pa), fmt_t(ml), fmt_t(pl),
                      f"{ma / mc:.2f}", f"{ml / mc:.1f}"))
    cuerpo = [
        "insertar n entradas (distancia al azar, semilla n) y extraer todas en orden; mediana y p95 de "
        f"{3 if rapido else '7 (5 con 10000; lineal: 3 con 10000)'} repeticiones",
    ] + lineas_tabla(("Salas n", "Cola med", "Cola p95", "Agenda med", "Agenda p95", "Lineal med", "Lineal p95",
                      "Agenda/Cola", "Lineal/Cola"), filas)
    return bloque("M2: ColaPrioridad frente a agenda y búsqueda lineal del mínimo", "FR-033", cuerpo)


# ───────────────────────── M3 ─────────────────────────

K_M3 = (1, 2, 5, 10, 25, 50)


def k_estrella(filas):
    """Menor k desde el cual la compartida es más rápida (mediana) que la individual para todo k mayor medido."""
    resultado = None
    for k, individual, compartida in reversed(filas):
        if compartida < individual:
            resultado = k
        else:
            break
    return resultado


def medir_m3(rapido=None):
    """M3: campo compartido frente a individual, k cazadores, rango pequeño y grande, puertas estables (FR-030,
    FR-032)."""
    rapido = _rapido(rapido)
    cantidad = 8 if rapido else 40
    cripta = cripta_referencia()
    jugador = sala_centro(SALAS_REFERENCIA)
    cuerpo = [
        f"cripta sintética de {SALAS_REFERENCIA} salas, cazadores activados en salas al azar a distancia ≤ rango; "
        "una muestra = decidir los k cazadores una vez (compartida: un ciclo nuevo, así que recalcula el campo una "
        f"vez); {cantidad} muestras intercaladas por estrategia",
    ]
    for nombre, rango in (("pequeño", RANGO_PEQUENO), ("grande", RANGO_GRANDE)):
        posiciones = cazadores_en_rango(cripta, jugador, rango, max(K_M3), 303)
        filas, medianas = [], []
        for k in K_M3:
            motor = motor_con_cazadores(cripta, jugador, posiciones[:k])
            cazadores = list(motor.enemigos)

            def individual():
                for cazador in cazadores:
                    motor.decidir_cazador_individual(cazador)

            def compartida():
                motor.ciclo += 1  # empieza otro ciclo: el campo anterior ya no sirve
                for cazador in cazadores:
                    motor.decidir_cazador_compartida(cazador)

            tiempos_i, tiempos_c = [], []
            gc.collect()
            for _ in range(cantidad):
                tiempos_i += muestras(individual, 1)
                tiempos_c += muestras(compartida, 1)
            mi, pi = resumen(tiempos_i)
            mc, pc = resumen(tiempos_c)
            medianas.append((k, mi, mc))
            filas.append((k, fmt_t(mi), fmt_t(pi), fmt_t(mc), fmt_t(pc), f"{mi / mc:.2f}",
                          "compartida" if mc < mi else "individual"))
        estrella = k_estrella(medianas)
        cuerpo += ["", f"rango {nombre} = {rango}  (|R| = {tamano_region(cripta, jugador, rango)} salas)"]
        cuerpo += lineas_tabla(("k", "Individual med", "Individual p95", "Compartida med", "Compartida p95",
                                "Ind/Comp", "Más rápida"), filas)
        cuerpo.append(f"k* medido (rango {nombre}) = {estrella if estrella is not None else 'no se alcanza'}")
    return bloque("M3: campo compartido frente a individual", "FR-030, FR-032", cuerpo)


# ───────────────────────── M4 ─────────────────────────

CAMBIOS_POR_CICLO = 2


def _puertas_cambiables(motor):
    """Salidas abiertas que no tocan la sala de salida (su puerta con llave queda como está), en orden de sala y
    dirección."""
    candidatas = []
    for sala in sorted(motor.salas, key=lambda s: s.id):
        if sala.id == motor.sala_salida:
            continue
        for direccion in ("N", "S", "E", "O"):
            salida = sala.salidas.get(direccion)
            if salida is not None and not salida.cerrada and salida.sala_destino != motor.sala_salida:
                candidatas.append(salida)
    return candidatas


def _correr_m4(escenario, ciclos):
    """Arma el motor del escenario y corre ``ciclos`` ciclos; devuelve los tiempos (ms) de cada ciclo."""
    cripta = cripta_referencia()
    jugador = sala_centro(SALAS_REFERENCIA)
    estrategia = "individual" if escenario == "c" else "compartida"
    motor = motor_con_cazadores(cripta, jugador, cazadores_en_cripta(cripta, jugador, (RANGO_GRANDE,), CAZADORES,
                                                                     404), estrategia=estrategia)
    candidatas = _puertas_cambiables(motor) if escenario == "b" else []
    azar = random.Random(505)
    cerradas = []
    tiempos = []
    gc.collect()
    with silencioso():
        for _ in range(ciclos):
            if escenario == "b":  # entre ciclos, fuera del tiempo medido
                for salida in cerradas:
                    motor._escribir_cerrada(salida, False, "bench: reabrir", registrar=False)
                cerradas = [azar.choice(candidatas) for _ in range(CAMBIOS_POR_CICLO)]
                for salida in cerradas:
                    motor._escribir_cerrada(salida, True, "bench: cerrar", registrar=False)
            inicio = time.perf_counter()
            motor.ejecutar_accion("esperar")
            tiempos.append((time.perf_counter() - inicio) * 1000)
    return tiempos, motor.version_puertas


def medir_m4(rapido=None):
    """M4: 50 cazadores activados; puertas estables, puertas que cambian y recalcular siempre (FR-030 a FR-032)."""
    rapido = _rapido(rapido)
    ciclos = 15 if rapido else 100
    escenarios = (
        ("a", "puertas estables, compartida"),
        ("b", f"puertas cambian ({CAMBIOS_POR_CICLO} por ciclo), compartida"),
        ("c", "recalcular siempre desde cero, individual"),
    )
    filas = []
    for clave, descripcion in escenarios:
        tiempos, version = _correr_m4(clave, ciclos)
        with contar_busquedas() as cuenta:  # pasada aparte, idéntica, solo para contar
            _correr_m4(clave, ciclos)
        mediana, percentil = resumen(tiempos)
        busquedas = cuenta["primer_paso"] + cuenta["campo_hacia"]
        filas.append((f"({clave}) {descripcion}", fmt_t(mediana), fmt_t(percentil), busquedas,
                      cuenta["primer_paso"], cuenta["campo_hacia"], f"{busquedas / ciclos:.1f}", version,
                      cumple(percentil < LIMITE_MS)))
    cuerpo = [
        f"cripta sintética de {SALAS_REFERENCIA} salas, {CAZADORES} cazadores de rango {RANGO_GRANDE} en salas al "
        f"azar de la cripta, activados antes de medir; {ciclos} ciclos (ejecutar_accion('esperar') hasta la "
        "siguiente decisión del jugador); las puertas de (b) se cambian con motor._escribir_cerrada entre ciclos",
        f"cumple = p95 < {LIMITE_MS} ms (criterio de bench_ciclo.py); búsquedas contadas en una pasada idéntica aparte",
    ] + lineas_tabla(("Escenario", "Mediana", "p95", "Búsquedas", "primer_paso", "campo_hacia", "Por ciclo",
                      "version_puertas", ""), filas)
    return bloque("M4: 50 cazadores, puertas estables, cambiantes y recalcular siempre",
                  "FR-030, FR-031, FR-032", cuerpo)


# ───────────────────────── M5 ─────────────────────────

RANGO_M5 = 600
DESPLAZAMIENTO_M5 = 3  # el cazador está 3 salas a la derecha del jugador en la misma fila de la serpentina


CALENTAMIENTO_M5 = 500  # llamadas a decidir() sin medir antes de cronometrar cada tamaño
REPETICIONES_M5 = 5


def _preparar_m5(salas):
    """Cripta de ``salas`` salas, motor con un cazador y las funciones que se miden. Lo cronometrado es solo la
    decisión; la preparación se informa aparte."""
    inicio = time.perf_counter()
    cripta = cripta_terreno(SEMILLA_CRIPTA, salas)
    jugador = sala_centro(salas)
    cazador = jugador + DESPLAZAMIENTO_M5
    ancho = _ancho(salas)
    if (jugador - 1) // ancho != (cazador - 1) // ancho:
        raise ValueError("el cazador quedó fuera de la fila del jugador")
    motor = motor_con_cazadores(cripta, jugador, [(cazador, RANGO_M5)], estrategia="individual")
    preparacion = time.perf_counter() - inicio
    caz = motor.enemigos[0]
    grafo, espacio = motor.grafo_cripta, motor.espacio_busqueda
    origen, destino = caz.sala, motor.jugador.sala

    def decidir():
        motor.decidir_cazador(caz)

    def con_espacio():
        primer_paso_busqueda(grafo, origen, destino, RANGO_M5, espacio)

    def sin_espacio():
        primer_paso_busqueda(grafo, origen, destino, RANGO_M5, None)

    return {"salas": salas, "preparacion": preparacion, "region": tamano_region(cripta, jugador, RANGO_M5),
            "decision": motor.decidir_cazador(caz).accion, "decidir": decidir, "con_espacio": con_espacio,
            "sin_espacio": sin_espacio}


def _calentar(funcion, llamadas):
    for _ in range(llamadas):
        funcion()


def medir_m5(rapido=None):
    """M5: criptas de 10², 10³, 10⁴ y 10⁵ salas, mismo rango y misma posición relativa; cada tamaño se calienta
    antes de cronometrar y la medición de todos los tamaños se repite; control con espacio nuevo por búsqueda
    (FR-033, SC-007)."""
    rapido = _rapido(rapido)
    tamanos = (100, 1000, 10000) if rapido else (100, 1000, 10000, 100000)
    cantidad, lote = (10, 20) if rapido else (40, 50)
    repeticiones = 2 if rapido else REPETICIONES_M5
    calentamiento = 100 if rapido else CALENTAMIENTO_M5
    casos = [_preparar_m5(salas) for salas in tamanos]

    # repeticiones de todos los tamaños; en cada una, cada tamaño se calienta justo antes de cronometrarlo
    medianas = [[] for _ in casos]  # medianas[i][r]: mediana de decidir() del tamaño i en la repetición r
    filas_rep = []
    for r in range(repeticiones):
        fila = [r + 1]
        for i in range(len(casos)):
            _calentar(casos[i]["decidir"], calentamiento)
            mediana, _ = resumen(muestras(casos[i]["decidir"], cantidad, lote))
            medianas[i].append(mediana)
            fila.append(fmt_t(mediana))
        fila.append(f"{medianas[-1][r] / medianas[0][r]:.2f}")
        filas_rep.append(fila)
    finales = [statistics.median(m) for m in medianas]
    cociente = finales[-1] / finales[0]
    filas_rep.append([f"mediana de las {repeticiones}"] + [fmt_t(t) for t in finales] + [f"{cociente:.2f}"])

    # control: reutilizar el EspacioBusqueda del motor frente a uno nuevo por llamada (también calentado)
    filas_control = []
    for caso in casos:
        _calentar(caso["con_espacio"], calentamiento)
        mr, pr = resumen(muestras(caso["con_espacio"], cantidad, lote))
        _calentar(caso["sin_espacio"], calentamiento)
        mn, pn = resumen(muestras(caso["sin_espacio"], cantidad, lote))
        filas_control.append((caso["salas"], f"{caso['preparacion']:.2f} s", caso["region"], caso["decision"],
                              fmt_t(mr), fmt_t(pr), fmt_t(mn), fmt_t(pn), f"{mn / mr:.1f}"))

    cuerpo = [
        f"criptas sintéticas (semilla {SEMILLA_CRIPTA}) por cripta_terreno y armar_motor; jugador en el centro de la "
        f"cuadrícula, cazador {DESPLAZAMIENTO_M5} salas a su derecha en la misma fila, rango {RANGO_M5}, estrategia "
        f"individual; antes de cronometrar cada tamaño, {calentamiento} llamadas a decidir() sin medir; cada dato es "
        f"la mediana de {cantidad} muestras de {lote} llamadas; {repeticiones} repeticiones de todos los tamaños",
        "",
        "decidir(): mediana por tamaño y repetición, y cociente de la repetición",
    ] + lineas_tabla(["Repetición"] + [f"{t} salas" for t in tamanos]
                     + [f"tiempo({tamanos[-1]}) / tiempo({tamanos[0]})"], filas_rep) + [
        f"cociente final (mediana de las {repeticiones} repeticiones) tiempo({tamanos[-1]}) / tiempo({tamanos[0]}) = "
        f"{cociente:.2f}  (máximo {COCIENTE_MAXIMO}): {cumple(cociente <= COCIENTE_MAXIMO)}",
        "",
        "control: Preparación = generar la cripta y armar el motor (no se mide en la decisión); Reutiliza/Espacio "
        "nuevo = primer_paso de Modelo.BusquedaRuta con el EspacioBusqueda del motor o con espacio=None (listas "
        "nuevas en cada llamada)",
    ] + lineas_tabla(("Salas", "Preparación", "|R|", "Decisión", "Reutiliza med", "Reutiliza p95",
                      "Espacio nuevo med", "Espacio nuevo p95", "Nuevo/Reutiliza"), filas_control)
    return bloque("M5: decisión del cazador en criptas de tamaño creciente", "FR-033, SC-007", cuerpo)


# ───────────────────────── M6 ─────────────────────────

def medir_m6(rapido=None):
    """M6: rango pequeño frente a grande en la misma cripta (FR-033)."""
    rapido = _rapido(rapido)
    cantidad, lote = (10, 20) if rapido else (40, 50)
    cripta = cripta_referencia()
    jugador = sala_centro(SALAS_REFERENCIA)
    todas = distancias_hacia(cripta, jugador, 10 ** 9)

    def mas_cercana_a(objetivo):
        return min(todas, key=lambda par: (abs(par[1] - objetivo), par[0]))

    posiciones = (("cerca", mas_cercana_a(300)), ("lejos", mas_cercana_a(1200)))
    filas, cocientes = [], []
    for nombre, (sala, distancia) in posiciones:
        tiempos = []
        for rango in (RANGO_PEQUENO, RANGO_GRANDE):
            motor = motor_con_cazadores(cripta, jugador, [(sala, rango)], estrategia="individual")
            caz = motor.enemigos[0]
            decision = motor.decidir_cazador(caz).accion
            mediana, percentil = resumen(muestras(lambda: motor.decidir_cazador(caz), cantidad, lote))
            tiempos.append(mediana)
            filas.append((nombre, distancia, rango, tamano_region(cripta, jugador, rango), decision,
                          fmt_t(mediana), fmt_t(percentil)))
        cocientes.append(f"{nombre}: grande / pequeño = {tiempos[1] / tiempos[0]:.2f}")
    cuerpo = [
        f"cripta sintética de {SALAS_REFERENCIA} salas, un cazador, estrategia individual; «cerca» y «lejos» son las "
        "salas con distancia hacia el jugador más próxima a 300 y a 1200; |R| = salas a distancia ≤ rango; "
        f"{cantidad} muestras de {lote} llamadas",
    ] + lineas_tabla(("Posición", "Distancia", "Rango", "|R|", "Decisión", "Mediana", "p95"), filas) + cocientes
    return bloque("M6: rango pequeño frente a grande en la misma cripta", "FR-033", cuerpo)


# ───────────────────────── M7 ─────────────────────────

RANGOS_M7 = (RANGO_PEQUENO, 1000, RANGO_GRANDE)


def medir_m7(rapido=None):
    """M7: 50 cazadores activos en la cripta de referencia, ciclo completo con la estrategia por defecto (FR-030,
    SC-004)."""
    rapido = _rapido(rapido)
    ciclos = 15 if rapido else 100
    cripta = cripta_referencia()
    jugador = sala_centro(SALAS_REFERENCIA)
    motor = motor_con_cazadores(cripta, jugador, cazadores_en_cripta(cripta, jugador, RANGOS_M7, CAZADORES, 707))
    estrategia = motor.estrategia_cazador
    tiempos = []
    gc.collect()
    with silencioso():
        for _ in range(ciclos):
            inicio = time.perf_counter()
            motor.ejecutar_accion("esperar")
            tiempos.append((time.perf_counter() - inicio) * 1000)
    mediana, percentil = resumen(tiempos)
    cuerpo = [
        f"cripta sintética de {SALAS_REFERENCIA} salas (PROVISIONAL: la de referencia aún no está publicada), "
        f"{CAZADORES} cazadores activados con rangos al azar en {RANGOS_M7} en salas al azar, estrategia del motor "
        f"por defecto = {estrategia!r}; {ciclos} ciclos como bench_motor.bench_ciclo_real",
    ] + lineas_tabla(("Cazadores activos", "Mediana", "p95", ""),
                     [(CAZADORES, fmt_t(mediana), fmt_t(percentil), cumple(percentil < LIMITE_MS))]) + [
        f"cumple = p95 < {LIMITE_MS} ms (criterio de bench_ciclo.py)",
    ]
    return bloque("M7: ciclo completo con 50 cazadores activos", "FR-030, SC-004", cuerpo)


# ───────────────────────── correr ─────────────────────────

MEDICIONES = (("M1", medir_m1), ("M2", medir_m2), ("M3", medir_m3), ("M4", medir_m4), ("M5", medir_m5),
              ("M6", medir_m6), ("M7", medir_m7))


def encabezado(rapido):
    modo = (f"rápido ({VARIABLE_RAPIDO}=1: menos repeticiones y tamaños, solo para probar el script)" if rapido
            else "completo")
    return [
        "-Cazador: decisión, campo compartido y ciclo con 50 cazadores (spec 003, US5, M1 a M7)-",
        f"equipo: {platform.platform()} | {platform.processor() or platform.machine()} | Python {platform.python_version()}",
        f"modo: {modo}; sin red ni vista; tiempos con time.perf_counter; p95 = posición int(0,95·n) de las muestras",
        f"criptas sintéticas de tests/utiles_terreno.py (semilla {SEMILLA_CRIPTA}, costo 100 por salida); la cripta "
        f"de referencia publicada aún no existe: se usa una sintética de {SALAS_REFERENCIA} salas (PROVISIONAL)",
    ]


def reemplazar_bloques(existentes, bloques):
    """Devuelve ``existentes`` (líneas del archivo) con el bloque de cada medición de ``bloques`` ({nombre: líneas})
    puesto en lugar del anterior. Un bloque va de su línea en blanco previa a la línea en blanco que precede al bloque
    siguiente o a «duración de la corrida»; si no estaba, se agrega antes de esa línea final."""
    lineas = list(existentes)
    for nombre, bloque_nuevo in bloques.items():
        indice = next((i for i, l in enumerate(lineas) if l.startswith(f"-{nombre}:")), None)
        if indice is None:
            final = next((i for i, l in enumerate(lineas) if l.startswith("duración de la corrida")), len(lineas))
            if final > 0 and lineas[final - 1] == "":
                final -= 1
            lineas[final:final] = bloque_nuevo
            continue
        comienzo = indice - 1 if indice > 0 and lineas[indice - 1] == "" else indice
        termino = len(lineas)
        for j in range(indice + 1, len(lineas) - 1):
            siguiente = lineas[j + 1]
            if lineas[j] == "" and (siguiente.startswith("-M") or siguiente.startswith("duración de la corrida")):
                termino = j
                break
        lineas[comienzo:termino] = bloque_nuevo
    return lineas


def correr_bench(nombres=None):
    """Corre las mediciones (todas si ``nombres`` es None) y escribe resultados_bench_cazador.txt. Con todas reescribe
    el archivo; con algunas (y fuera del modo rápido) reemplaza solo sus bloques y deja el resto como estaba."""
    rapido = es_rapido()
    # con la salida redirigida en Windows la consola es cp1252: se reemplaza lo que no se puede mostrar en lugar de
    # fallar (el archivo de resultados se escribe siempre en UTF-8)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ruta = os.path.join(RAIZ, ARCHIVO_RESULTADOS)
    inicio = time.perf_counter()
    cabecera = encabezado(rapido)
    for linea in cabecera:
        print(linea)
    lineas = list(cabecera)
    bloques = {}
    for nombre, medir in MEDICIONES:
        if nombres is None or nombre in nombres:
            bloques[nombre] = medir(rapido)
            lineas += bloques[nombre]
    total = time.perf_counter() - inicio
    print(f"\nduración de la corrida: {total:.1f} s")
    if nombres is None:
        lineas += ["", f"duración de la corrida: {total:.1f} s"]
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write("\n".join(lineas) + "\n")
    elif not rapido and os.path.exists(ruta):
        for nombre in bloques:
            bloques[nombre] = bloques[nombre] + [
                f"(medición actualizada sola con python -m tests.bench_cazador {' '.join(bloques)}, {total:.1f} s; "
                "el resto del archivo es de la última corrida completa)"]
        with open(ruta, encoding="utf-8") as archivo:
            existentes = archivo.read().splitlines()
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write("\n".join(reemplazar_bloques(existentes, bloques)) + "\n")
        print(f"bloques {', '.join(bloques)} actualizados en {ARCHIVO_RESULTADOS}")
    return lineas


if __name__ == "__main__":
    pedidas = [a.upper() for a in sys.argv[1:]]
    desconocidas = [a for a in pedidas if a not in dict(MEDICIONES)]
    if desconocidas:
        sys.exit(f"Mediciones desconocidas: {', '.join(desconocidas)} (válidas: M1 a M7)")
    correr_bench(pedidas or None)
