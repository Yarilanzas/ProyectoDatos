# Evidencia de rendimiento de la línea de tiempo (spec 004, Fase 8, M1 a M10; T099 a T110; Principio VIII).
# Misma estructura que tests/bench_ciclo.py, bench_niebla.py y bench_cazador.py: `correr_bench()` imprime y escribe
# resultados_bench_linea.txt en la raíz, con el equipo y la versión de Python. Sin red ni vista; partidas deterministas por
# semilla sobre una cripta sintética de 20 salas (tests/mapas_sinteticos.py), sin datos de ninguna cripta real
# (Principio IV). Cada medición arma su propia partida: ninguna depende del estado que deja otra.
#
#     python -m tests.bench_linea             todas las mediciones, escribe resultados_bench_linea.txt
#     python -m tests.bench_linea M1 M3       solo esas, solo en pantalla (el archivo es de la corrida completa)
#     BENCH_LINEA_RAPIDO=1                    tamaños mínimos y una repetición (prueba de humo, unos segundos)
#
# Qué mide cada una (tasks.md, T101 a T110):
#   M1  tiempo de `historia` (#k y por instante) con varios K y sin puntos de control, n = 5 000      (SC-002)
#   M2  memoria de la línea (tracemalloc) y bytes por punto, n = 2 500, 5 000 y 10 000                (SC-006)
#   M3  costo de copiar y de materializar con N = 20, 60, 200 y 2 000 salas, frente a deepcopy a secas (P-D06)
#   M4  costo del recorte (`retroceder`) con 500, 5 000 y 50 000 acciones, umbral de SC-010
#   M5  sobrecosto de registrar por acción, con y sin línea (p95 < 20 ms)
#   M6  carga: tiempo de reconstruir el guion y tamaño del bloque, con y sin @cargar
#   M7  equivalencia de contenido: los mismos 100 instantes con K = 1, 50 y 500, tres semillas
#   M8  `--replay --hasta` de principio a fin, con y sin --checkpoint-cada
#   M9  oráculo de la copia: estructurada frente a deepcopy completo con N <= 60
#   M10 retroceso antes y después de la línea (repetición de P1 §4.6 con la carga nueva)
#
# Todo tiempo se toma con el recolector de basura detenido (y vaciado antes): una pausa del recolector no es el costo de la
# operación (tests/test_linea_rendimiento.py, T090). Principio I: sin dict ni set como índice; las medianas y los percentiles
# usan el ordenamiento propio (Modelo/ordenamiento.py).

import contextlib
import copy
import gc
import io
import os
import pickle
import platform
import shutil
import sys
import tempfile
import time
import tracemalloc
from unittest import mock

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Controlador.ControladorPartida import guardar_motor
from Controlador.ReconstructorLinea import ReconstructorLinea
from Modelo.CopiaEstado import copiar, materializar
from Modelo.LineaTiempo import K_POR_OMISION
from Modelo.ordenamiento import merge_sort
from Persistencia.ConversorPartida import RestauradorPartida
from Vista.TextoResumen import lineas_resumen
from tests.bench_niebla import mediana, medir_ms
from tests.mapas_sinteticos import salas_sinteticas
from tests.utiles_linea import GeneradorAcciones, SesionLinea, jugar, partida_linea, resumen_ampliado
from tests.utiles_niebla import CRIPTA_NIEBLA
from tests.utiles_terreno import GestorTerreno, armar_motor, cripta_terreno

ARCHIVO_RESULTADOS = "resultados_bench_linea.txt"
VARIABLE_RAPIDO = "BENCH_LINEA_RAPIDO"
REPETICIONES = 7
SALAS = 20                       # la cripta sintética de las partidas jugadas
SEMILLAS = (1, 2, 3)
SIN_PUNTOS = 10 ** 9             # un K tan grande que solo existe el punto de la acción 0 (la alternativa sin puntos de control)
LIMITE_CONSULTA_MS = 50          # SC-002: el 100 % de las consultas
LIMITE_REGISTRO_P95_MS = 20      # enunciado §5.2: el p95 de lo que cuesta registrar una acción
COCIENTE_RECORTE = 3             # M4: «casi constante» = el recorte de 50 000 acciones cuesta menos de 3 veces el de 500
MARGEN_DE_VELOCIDAD = 2.5        # T113: una máquina 2.5 veces más lenta que ésta debe seguir cumpliendo SC-002
# T003 y T018 (research.md): referencia de M3, (N, ms, KiB) de `copiar` con grafo_cripta y espacio_busqueda tras 10 acciones
REFERENCIA_T018 = ((20, 0.81, 15), (200, 3.87, 74), (2000, 42.5, 664))


DATOS_K = []   # filas (medición, K, n, valor) que M1, M2, M5 y M6 dejan para justificar el K por omisión (T113)


def es_rapido():
    return os.environ.get(VARIABLE_RAPIDO) == "1"


def _rapido(rapido):
    return es_rapido() if rapido is None else rapido


# ───────────────────────── base común (T099) ─────────────────────────

@contextlib.contextmanager
def sin_recolector():
    """El recolector de basura detenido (y vaciado antes) mientras se mide; siempre se vuelve a encender."""
    gc.collect()
    gc.disable()
    try:
        yield
    finally:
        gc.enable()


def _identidad(valor):
    return valor


def percentil(valores, p):
    """Percentil `p` (0 < p <= 1) por rango más cercano, con el ordenamiento propio. O(r log r)."""
    if len(valores) == 0:
        raise ValueError("percentil de una lista vacía")
    ordenados, _ = merge_sort(valores, _identidad)
    posicion = -(-int(p * 1000) * len(ordenados) // 1000) - 1       # techo(p * r) - 1, sin flotantes
    return ordenados[min(max(posicion, 0), len(ordenados) - 1)]


def estadisticas(tiempos):
    """(mediana, p95, máximo) de una lista de tiempos en ms."""
    return mediana(tiempos), percentil(tiempos, 0.95), percentil(tiempos, 1.0)


def ms(desde_ns):
    return (time.perf_counter_ns() - desde_ns) / 1_000_000


def nombre_k(k):
    return "sin puntos" if k == SIN_PUNTOS else f"K={k}"


def techo(numerador, denominador):
    return -(-numerador // denominador)


def encabezado(rapido=False):
    return [
        "-Línea de tiempo: consultar, registrar, recortar, guardar y cargar (spec 004, M1 a M10)-",
        f"equipo: {platform.platform()} | {platform.processor() or platform.machine()} | Python {platform.python_version()}",
        f"partidas deterministas por semilla sobre una cripta sintética de {SALAS} salas, sin red ni vista, con el recolector "
        "de basura detenido al medir; mediana, p95 y máximo de las muestras indicadas",
        f"K por omisión del programa: {K_POR_OMISION} (constante K_POR_OMISION de Modelo/LineaTiempo.py)",
        *(["MODO RÁPIDO: tamaños mínimos y una repetición; los números no valen como medición"] if rapido else []),
    ]


def escribir_resultados(lineas, ruta=None, rapido=False):
    """Escribe el encabezado y `lineas` en `ruta` (por omisión resultados_bench_linea.txt en la raíz) y los muestra."""
    ruta = os.path.join(RAIZ, ARCHIVO_RESULTADOS) if ruta is None else ruta
    todas = encabezado(rapido) + list(lineas)
    for linea in todas:
        print(linea)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(todas) + "\n")
    return todas


def sesion_de(k, semilla, acciones, pergaminos=0):
    """Una partida real de `acciones` acciones aceptadas con una línea de K dado (cripta sintética, sin huellas)."""
    sesion = SesionLinea(k=k, semilla=semilla, pergaminos=pergaminos, huellas=False,
                         salas=salas_sinteticas(SALAS), forzar=True)
    sesion.jugar(acciones)
    return sesion


def motor_de_n_salas(salas, acciones=10, semilla=1):
    """Un motor sin red sobre `salas` salas sintéticas, tras `acciones` acciones (como la medición T018 del research)."""
    motor = armar_motor(cripta_terreno(semilla, salas), sala_jugador=1, cazadores=[], semilla=semilla)
    jugar(motor, GeneradorAcciones(semilla), acciones)
    return motor


def _bloque(titulo, lineas):
    return ["", titulo] + lineas


# ───────────────────────── M1: consultar (T101) ─────────────────────────

def medir_m1(rapido=None):
    """Tiempo de `historia`: `#k` e instantes repartidos en toda la partida, con varios K y sin puntos de control."""
    rapido = _rapido(rapido)
    n = 40 if rapido else 5000
    ks = (5,) if rapido else (1, 10, 50, 100, 500, SIN_PUNTOS)
    lineas = []
    for k in ks:
        muestra = (3 if rapido else 10) if k == SIN_PUNTOS else (5 if rapido else 100)   # sin puntos cada consulta rehace miles
        sesion = sesion_de(k, 1, n)
        try:
            linea, motor = sesion.linea, sesion.motor
            tiempos = []
            mayor_rehecho = 0
            with sin_recolector():
                for i in range(muestra):
                    numero = 1 + i * n // muestra
                    desde = time.perf_counter_ns()
                    linea.consultar_accion(numero, motor)
                    tiempos.append(ms(desde))
                    mayor_rehecho = max(mayor_rehecho, linea.acciones_rehechas)
                for i in range(muestra):
                    t = i * (linea.reloj_actual - 1) // muestra
                    desde = time.perf_counter_ns()
                    linea.consultar_instante(t, motor)
                    tiempos.append(ms(desde))
                    mayor_rehecho = max(mayor_rehecho, linea.acciones_rehechas)
            med, p95, maximo = estadisticas(tiempos)
            dentro = len([t for t in tiempos if t < LIMITE_CONSULTA_MS])
            veredicto = ""
            if k == K_POR_OMISION:
                veredicto = f"   {'cumple' if dentro == len(tiempos) else 'NO CUMPLE'} SC-002 (100 % < {LIMITE_CONSULTA_MS} ms)"
            DATOS_K.append(("M1 máx", k, n, maximo))
            DATOS_K.append(("M1 p95", k, n, p95))
            lineas.append(f"M1 {nombre_k(k):<11} n={n} consultas={len(tiempos):<3} puntos={linea.cantidad_puntos:<5} "
                          f"rehecho<={mayor_rehecho:<5} mediana {med:9.3f} ms p95 {p95:9.3f} ms máx {maximo:9.3f} ms "
                          f"< {LIMITE_CONSULTA_MS} ms: {100 * dentro // len(tiempos):3d} %{veredicto}")
        finally:
            sesion.cerrar()
    return _bloque("-M1: tiempo de `historia` (#k y por instante) según K (T101; FR-018, FR-020, SC-002)-", lineas)


# ───────────────────────── M2: memoria (T102) ─────────────────────────

def _bytes_de_partida(acciones, k):
    """Bytes que retiene una partida de `acciones` acciones y sus puntos de la línea (None: la partida sin línea)."""
    gc.collect()
    tracemalloc.start()
    try:
        if k is None:
            partida = partida_linea(salas=salas_sinteticas(SALAS), forzar=True, semilla=1)
            jugar(partida.motor, GeneradorAcciones(1), acciones)
            gc.collect()
            actual = tracemalloc.get_traced_memory()[0]
            partida.cerrar()
            return actual, 0
        sesion = sesion_de(k, 1, acciones)
        gc.collect()
        actual = tracemalloc.get_traced_memory()[0]
        puntos = sesion.linea.cantidad_puntos
        sesion.cerrar()
        return actual, puntos
    finally:
        tracemalloc.stop()


def medir_m2(rapido=None):
    """Memoria de la línea (tracemalloc) y bytes por punto: la partida con línea menos la misma partida sin ella."""
    rapido = _rapido(rapido)
    tamanos = (30,) if rapido else (2500, 5000, 10000)
    ks = (5, SIN_PUNTOS) if rapido else (10, 50, 100, 500, SIN_PUNTOS)
    lineas = []
    previos = []     # (k, n, bytes de la línea) para el cociente al duplicar n
    for n in tamanos:
        base, _ = _bytes_de_partida(n, None)
        medidas = []
        for k in ((1,) + ks if (n == tamanos[0] and not rapido) else ks):   # K = 1 solo con n = 2 500 (cada acción es un punto)
            medidas.append((k,) + _bytes_de_partida(n, k))
        sin_puntos = [m for m in medidas if m[0] == SIN_PUNTOS][0]
        for k, total, puntos in medidas:
            de_la_linea = total - base
            por_punto = ""
            if k != SIN_PUNTOS and puntos > 1:
                por_punto = f" {(total - sin_puntos[1]) / (puntos - 1) / 1024:8.1f} KiB/punto"
            cota = techo(n, k) + 1 if k != SIN_PUNTOS else 1
            cociente = ""
            for anterior in previos:
                if anterior[0] == k and anterior[1] * 2 == n:
                    razon = de_la_linea / anterior[2]
                    cociente = f" x{razon:.2f} al duplicar n ({'cumple' if 1.6 <= razon <= 2.4 else 'NO CUMPLE'})"
            previos.append((k, n, de_la_linea))
            DATOS_K.append(("M2 KiB", k, n, de_la_linea / 1024))
            lineas.append(f"M2 {nombre_k(k):<11} n={n:<6} línea {de_la_linea / 1024:10.1f} KiB puntos={puntos:<5}"
                          f" (cota {cota}: {'cumple' if puntos <= cota else 'NO CUMPLE'}){por_punto}{cociente}")
    if not rapido:
        lineas.append("M2 K=1 solo se midió con n = 2 500; con n = 5 000 y 10 000 queda sin medir (HIPÓTESIS: crece como n · bytes por punto)")
    return _bloque("-M2: memoria de la línea (tracemalloc) y bytes por punto (T102; FR-021, SC-006)-", lineas)


# ───────────────────────── M3: copiar y materializar (T103) ─────────────────────────

def _referencia(salas):
    for n, tiempo, memoria in REFERENCIA_T018:
        if n == salas:
            return f"T018: {tiempo} ms y {memoria} KiB"
    return "sin referencia en T018"


def _deepcopy_a_secas(motor):
    """`copy.deepcopy(motor)` sin ayuda (solo se le saca el gestor, que no es estado): el que no sirve en criptas grandes."""
    memo = {}
    memo[id(motor.gestor_datos)] = None
    return copy.deepcopy(motor, memo)


def medir_m3(rapido=None):
    """Costo de una copia y de materializar un clon con N salas, frente a `deepcopy` a secas."""
    rapido = _rapido(rapido)
    tamanos = (20,) if rapido else (20, 60, 200, 2000)
    repeticiones = 1 if rapido else REPETICIONES
    lineas = []
    for salas in tamanos:
        motor = motor_de_n_salas(salas)
        with sin_recolector():
            t_copiar = medir_ms(lambda: copiar(motor), repeticiones)
            punto = copiar(motor)
            gestor = GestorTerreno()
            t_materializar = medir_ms(lambda: materializar(punto, gestor), repeticiones)
        gc.collect()
        tracemalloc.start()
        try:
            antes = tracemalloc.get_traced_memory()[0]
            retenido = copiar(motor)
            kib = (tracemalloc.get_traced_memory()[0] - antes) / 1024
        finally:
            tracemalloc.stop()
        del retenido
        try:
            with sin_recolector():
                t_completo = f"{medir_ms(lambda: _deepcopy_a_secas(motor), repeticiones):9.3f} ms"
        except RecursionError:
            t_completo = "RecursionError (no sirve)"
        DATOS_K.append(("M3 materializar", None, salas, t_materializar))
        lineas.append(f"M3 N={salas:<5} copiar {t_copiar:9.3f} ms {kib:8.1f} KiB | materializar {t_materializar:9.3f} ms | "
                      f"deepcopy a secas {t_completo} | {_referencia(salas)}")
    lineas.append("M3 la referencia T018 mide 20 repeticiones con el motor tras 10 acciones; aquí "
                  f"{'1 repetición' if rapido else f'{REPETICIONES} repeticiones'}, motor tras 10 acciones")
    return _bloque("-M3: costo de una copia y de materializar, frente a deepcopy a secas (T103; FR-017, FR-020)-", lineas)


# ───────────────────────── M4 y M10: retroceder (T104 y T110) ─────────────────────────

def _retrocesos(acciones, semilla, cantidad):
    """(tiempos de `retroceder` solo del motor, tiempos de `registrar_retroceso` de la línea) tras `acciones` acciones."""
    sesion = sesion_de(50, semilla, acciones, pergaminos=cantidad)
    historial = []
    linea_ms = []
    try:
        motor, linea = sesion.motor, sesion.linea
        with sin_recolector():
            for _ in range(cantidad):
                sesion.hacer([("esperar", "")])
                desde = time.perf_counter_ns()
                aceptado = motor.ejecutar_accion("retroceder", "")
                medio = time.perf_counter_ns()
                if not aceptado:
                    continue
                linea.registrar_retroceso(motor)
                historial.append((medio - desde) / 1_000_000)
                linea_ms.append(ms(medio))
    finally:
        sesion.cerrar()
    return historial, linea_ms


def _datos_de_retroceso(rapido):
    tamanos = (30,) if rapido else (500, 5000, 50000)
    semillas = (1,) if rapido else SEMILLAS
    cantidad = 2 if rapido else 5
    resultado = []
    for n in tamanos:
        historial, linea = [], []
        for semilla in semillas:
            h, l = _retrocesos(n, semilla, cantidad)
            historial += h
            linea += l
        resultado.append((n, historial, linea))
    return resultado


def medir_m4(rapido=None, datos=None):
    """Costo del recorte de la línea al retroceder, con partidas de 500, 5 000 y 50 000 acciones."""
    rapido = _rapido(rapido)
    datos = _datos_de_retroceso(rapido) if datos is None else datos
    lineas = []
    medianas = []
    mayor = 0.0
    for n, _, linea in datos:
        med, p95, maximo = estadisticas(linea)
        medianas.append(med)
        mayor = max(mayor, maximo)
        lineas.append(f"M4 n={n:<6} muestras={len(linea):<3} recorte de la línea: mediana {med:9.3f} ms p95 {p95:9.3f} ms "
                      f"máx {maximo:9.3f} ms")
    cociente = medianas[-1] / medianas[0] if medianas[0] > 0 else 0
    casi = "cumple" if cociente < COCIENTE_RECORTE else "NO CUMPLE"
    umbral = techo(int(mayor * 2 * 1000), 1000)
    lineas.append(f"M4 tiempo casi constante: mediana con n={datos[-1][0]} / mediana con n={datos[0][0]} = {cociente:.2f} "
                  f"(< {COCIENTE_RECORTE}: {casi})")
    lineas.append(f"M4 umbral numérico de SC-010 fijado con estos datos: {max(umbral, 1)} ms por recorte "
                  "(dos veces el mayor máximo medido, redondeado hacia arriba a ms; a revisar si cambia la medición)")
    return _bloque("-M4: costo del recorte de la línea (`retroceder`) según las acciones de la partida (T104; FR-027, SC-010)-",
                   lineas)


def _historial_parte_i(repeticiones):
    """El `bench_retroceso` de tests/bench_personaC.py (5 intervalos x 50 cambios) como (registrar ms, deshacer ms)."""
    from Modelo.retroceso import Historial

    def registrar_y_deshacer():
        historial = Historial()
        inicio = time.perf_counter_ns()
        for _ in range(5):
            historial.abrir_intervalo()
            for _ in range(50):
                historial.registrar(deshacer=lambda: None, description="cambio de prueba")
        registrar = ms(inicio)
        inicio = time.perf_counter_ns()
        while historial.puede_deshacer():
            historial.deshacer_ultimo()
        return registrar, ms(inicio)

    with sin_recolector():
        medidas = [registrar_y_deshacer() for _ in range(repeticiones)]
    return mediana([r for r, _ in medidas]), mediana([d for _, d in medidas])


def medir_m10(rapido=None, datos=None):
    """Retroceso antes (solo `Historial`) y después (con la línea registrando y recortando), tabla para DECISIONES.md."""
    rapido = _rapido(rapido)
    datos = _datos_de_retroceso(rapido) if datos is None else datos
    registrar, deshacer = _historial_parte_i(1 if rapido else REPETICIONES)
    lineas = [f"M10 P1 §4.6 (bench_personaC, sintético: 5 intervalos x 50 cambios, solo Historial): registrar 250 cambios "
              f"{registrar:8.4f} ms, deshacer 5 intervalos {deshacer:8.4f} ms (mediana de {1 if rapido else REPETICIONES})"]
    razones = []
    peor_total = 0.0
    for n, historial, linea in datos:
        antes = mediana(historial)
        totales = [h + l for h, l in zip(historial, linea)]
        despues = mediana(totales)
        peor_total = max(peor_total, max(totales))
        razones.append(despues / antes if antes > 0 else 0)
        lineas.append(f"M10 n={n:<6} partidas={len(SEMILLAS) if not rapido else 1} retrocesos={len(historial):<3} "
                      f"antes (solo Historial) {antes:8.4f} ms | después (Historial + línea) {despues:8.4f} ms "
                      f"| la línea agrega {despues - antes:8.4f} ms")
    peor = max(razones)
    adecuado = peor_total < LIMITE_REGISTRO_P95_MS
    lineas.append(f"M10 la línea multiplica a lo sumo por {peor:.1f} la mediana de retroceder; el retroceso entero (Historial + línea) "
                  f"tarda a lo sumo {peor_total:.3f} ms ({'por debajo' if adecuado else 'POR ENCIMA'} de {LIMITE_REGISTRO_P95_MS} ms): "
                  f"{'el `Historial` sigue siendo adecuado (no se cambia)' if adecuado else 'el Historial NO es adecuado: hay que revisarlo'}")
    lineas.append("M10 la agenda (P1 §4.1) no se mide aquí [PERSONAS: grupo]")
    return _bloque("-M10: retroceso antes y después de la línea de tiempo (T110; FR-014, FR-027, SC-010; repite P1 §4.6)-", lineas)


# ───────────────────────── M5: registrar por acción (T105) ─────────────────────────

def _acciones_medidas(k, acciones, con_linea):
    """(tiempos de la acción del motor, tiempos de registrarla en la línea) por cada acción aceptada."""
    sesion = SesionLinea(k=k, semilla=1, huellas=False, salas=salas_sinteticas(SALAS), forzar=True)
    accion, registro = [], []
    try:
        motor, linea, generador = sesion.motor, sesion.linea, GeneradorAcciones(1)
        with sin_recolector():
            while len(accion) < acciones and motor.jugador.esta_vivo() and not motor.victoria:
                nombre, argumento = generador.siguiente(motor)
                desde = time.perf_counter_ns()
                aceptada = motor.ejecutar_accion(nombre, argumento)
                medio = time.perf_counter_ns()
                if not aceptada:
                    continue
                accion.append((medio - desde) / 1_000_000)
                if con_linea:
                    linea.registrar_accion(motor, nombre, argumento)
                    registro.append(ms(medio))
    finally:
        sesion.cerrar()
    return accion, registro


def medir_m5(rapido=None):
    """Sobrecosto de registrar cada acción en el ciclo del juego, con y sin línea (p95 < 20 ms)."""
    rapido = _rapido(rapido)
    n = 40 if rapido else 5000
    ks = (5,) if rapido else (1, 10, K_POR_OMISION, 500)
    sin, _ = _acciones_medidas(SIN_PUNTOS, n, False)
    med_sin, p95_sin, max_sin = estadisticas(sin)
    lineas = [f"M5 sin línea      n={n} acción: mediana {med_sin:8.4f} ms p95 {p95_sin:8.4f} ms máx {max_sin:8.4f} ms"]
    for k in ks:
        accion, registro = _acciones_medidas(k, n, True)
        total = [a + r for a, r in zip(accion, registro)]
        med_r, p95_r, max_r = estadisticas(registro)
        med_t, p95_t, max_t = estadisticas(total)
        DATOS_K.append(("M5 p95", k, n, p95_r))
        lineas.append(f"M5 con línea {nombre_k(k):<7} n={n} registrar: mediana {med_r:8.4f} ms p95 {p95_r:8.4f} ms máx {max_r:8.4f} ms"
                      f" | acción + registrar: mediana {med_t:8.4f} ms p95 {p95_t:8.4f} ms máx {max_t:8.4f} ms"
                      f"   {'cumple' if p95_r < LIMITE_REGISTRO_P95_MS else 'NO CUMPLE'} (p95 de registrar < {LIMITE_REGISTRO_P95_MS} ms)")
    return _bloque("-M5: sobrecosto de registrar cada acción (T105; FR-017, FR-021; p95 < 20 ms de §5.2)-", lineas)


# ───────────────────────── M6: cargar (T106) ─────────────────────────

def _tiempo_de_cargar(acciones, k, con_carga, repeticiones):
    """(ms de reconstruir, bytes del bloque, bytes de pickle de un punto) de una partida guardada tras `acciones` acciones."""
    sesion = sesion_de(k, 1, acciones // 2 if con_carga else acciones)
    try:
        if con_carga:
            sesion.guardar_y_cargar()
            sesion.jugar(acciones - acciones // 2)
        registro = sesion.linea.a_registro()
        ruta = os.path.join(sesion.partida.carpeta.name, "bench.cripta")
        guardar_motor(sesion.motor, ruta, sesion.partida.gestor, linea=registro)
        bloque = len(registro.to_bytes())
        try:
            referencia = len(pickle.dumps(copiar(sesion.motor).estado))
        except Exception as error:      # solo es una cota de referencia: si no se puede serializar, se dice
            referencia = f"no serializable ({type(error).__name__})"
        restaurador = RestauradorPartida(ruta)
        try:
            tiempos = []
            for _ in range(repeticiones):
                reconstructor = ReconstructorLinea(sesion.partida.nuevo_gestor(iniciado=False))
                try:
                    with sin_recolector():
                        desde = time.perf_counter_ns()
                        reconstructor.reconstruir(restaurador.leer_linea(), restaurador.encabezado, restaurador.leer_jugador())
                        tiempos.append(ms(desde))
                finally:
                    reconstructor.cerrar()
        finally:
            restaurador.cerrar()
        return mediana(tiempos), bloque, referencia
    finally:
        sesion.cerrar()


def medir_m6(rapido=None):
    """Carga: tiempo de reconstruir el guion y tamaño del bloque, con distintos K, con y sin `@cargar`."""
    rapido = _rapido(rapido)
    tamanos = (30,) if rapido else (1000, 5000, 20000)
    ks = (5,) if rapido else (10, K_POR_OMISION, 500)
    lineas = []
    for n in tamanos:
        repeticiones = 1 if (rapido or n > 5000) else 3
        for k in ks:
            for con_carga in (False, True):
                tiempo, bloque, pickle_punto = _tiempo_de_cargar(n, k, con_carga, repeticiones)
                if not con_carga:
                    DATOS_K.append(("M6 ms", k, n, tiempo))
                if isinstance(pickle_punto, int):
                    cota = f"pickle de UN punto {pickle_punto / 1024:8.1f} KiB (unos {techo(n, k) * pickle_punto / 1024 / 1024:8.1f} MiB con " \
                           f"{techo(n, k) + 1} puntos)"
                else:
                    cota = f"pickle de un punto: {pickle_punto}"
                lineas.append(f"M6 n={n:<6} {nombre_k(k):<7} {'con @cargar' if con_carga else 'sin @cargar'} reconstruir {tiempo:10.1f} ms "
                              f"bloque {bloque / 1024:8.1f} KiB ({bloque / n:5.1f} B/acción) | {cota}")
    lineas.append(f"M6 cada tiempo es la mediana de {'1 reconstrucción' if rapido else '3 reconstrucciones (n <= 5 000) o 1 (n = 20 000)'}; "
                  "el pickle es solo una cota de referencia de guardar puntos completos (decisión 2: se guarda el guion)")
    return _bloque("-M6: cargar: tiempo de reconstruir y tamaño del bloque (T106; FR-022, FR-031)-", lineas)


# ───────────────────────── M7: equivalencia de contenido (T107) ─────────────────────────

def _resumenes_de_cien_instantes(k, semilla, acciones):
    sesion = sesion_de(k, semilla, acciones)
    try:
        linea, motor = sesion.linea, sesion.motor
        reloj = linea.reloj_actual
        return [lineas_resumen(linea.consultar_instante(reloj * i // 100, motor))[1:] for i in range(100)]
    finally:
        sesion.cerrar()


def medir_m7(rapido=None):
    """Equivalencia de contenido (no de tiempo): los mismos 100 instantes con K = 1, 50 y 500 dan resúmenes idénticos."""
    rapido = _rapido(rapido)
    acciones = 40 if rapido else 150
    ks = (1, 5) if rapido else (1, 50, 500)
    semillas = (1,) if rapido else SEMILLAS
    lineas = []
    for semilla in semillas:
        referencia = None
        iguales = True
        for k in ks:
            resumenes = _resumenes_de_cien_instantes(k, semilla, acciones)
            referencia = referencia if referencia is not None else resumenes
            iguales = iguales and resumenes == referencia
        lineas.append(f"M7 semilla={semilla} acciones={acciones} instantes=100 K={'/'.join(str(k) for k in ks)}: resúmenes "
                      f"{'idénticos' if iguales else 'DISTINTOS'} ({'cumple' if iguales else 'NO CUMPLE'} FR-028, SC-003)")
    return _bloque("-M7: los mismos 100 instantes con K distintos dan los mismos resúmenes (T107; FR-028, SC-003)-", lineas)


# ───────────────────────── M8: --replay --hasta (T108) ─────────────────────────

class VistaQueFalla:
    """Reemplaza a `VistaConsola`: `--replay` no debe instanciar la vista (Principio II)."""

    def __init__(self, *argumentos, **opciones):
        raise AssertionError("--replay instanció la vista")


def _correr_main(argumentos):
    """`main.main()` con `--replay` y sin vista ni red; devuelve (código, salida)."""
    import main
    salida = io.StringIO()
    with mock.patch.object(main, "VistaConsola", VistaQueFalla), \
            mock.patch.object(main, "configurar_logging", lambda *a, **k: None), \
            mock.patch.object(sys, "argv", ["main.py", *argumentos]), contextlib.redirect_stdout(salida):
        codigo = main.main()
    return codigo, salida.getvalue()


def medir_m8(rapido=None):
    """`--replay --hasta` de principio a fin, con y sin `--checkpoint-cada` (el costo es el de un replay completo)."""
    rapido = _rapido(rapido)
    acciones = 30 if rapido else 1000
    repeticiones = 1 if rapido else 3
    partida = partida_linea(salas=salas_sinteticas(SALAS), forzar=True, semilla=1)
    lineas = []
    try:
        generador = GeneradorAcciones(1)
        controlador = partida.controlador
        while controlador.linea is not None and controlador.linea.acciones < acciones and controlador.motor.estado_partida() == "en_curso":
            nombre, argumento = generador.siguiente(controlador.motor)
            controlador.ejecutar(f"{nombre} {argumento}".strip())
        controlador.bitacora.cerrar()
        base = ["--offline", partida.paquete, "--datos-locales", partida.ruta_datos, "--replay", partida.ruta_bitacora]
        final = controlador.linea.reloj_actual
        variantes = [("--replay (sin --hasta)", base)]
        for k in ((5,) if rapido else (None, 1, 10, 500)):
            etiqueta = "--hasta" + ("" if k is None else f" --checkpoint-cada {k}")
            variantes.append((etiqueta, base + ["--hasta", str(final // 2)] + ([] if k is None else ["--checkpoint-cada", str(k)])))
        normal = None
        for etiqueta, argumentos in variantes:
            with sin_recolector():
                tiempo = medir_ms(lambda: _correr_main(argumentos), repeticiones)
            codigo, salida = _correr_main(argumentos)
            normal = tiempo if normal is None else normal
            lineas.append(f"M8 acciones={controlador.linea.acciones:<5} {etiqueta:<34} {tiempo:10.1f} ms (x{tiempo / normal:4.2f} del replay normal) "
                          f"código {codigo}, {len(salida.splitlines())} líneas")
    finally:
        partida.cerrar()
    lineas.append("M8 informa: el costo de `--hasta` es el de reproducir toda la bitácora más una consulta; K solo cambia los puntos que se guardan")
    return _bloque("-M8: `--replay --hasta` de principio a fin, con y sin --checkpoint-cada (T108; FR-011, FR-028)-", lineas)


# ───────────────────────── M9: oráculo de la copia (T109) ─────────────────────────

def _completo(motor):
    memo = {}
    for colaborador in (motor.gestor_datos, motor.restaurador):
        if colaborador is not None:
            memo[id(colaborador)] = None
    return copy.deepcopy(motor, memo)


def medir_m9(rapido=None):
    """Oráculo de la copia: la copia estructurada frente a `deepcopy` completo con N <= 60, resúmenes iguales."""
    rapido = _rapido(rapido)
    tamanos = (20,) if rapido else (20, 60)
    repeticiones = 1 if rapido else REPETICIONES
    lineas = []
    for salas in tamanos:
        motor = motor_de_n_salas(salas)
        estructurada = materializar(copiar(motor), GestorTerreno())
        completa = _completo(motor)
        iguales = resumen_ampliado(estructurada) == resumen_ampliado(completa) == resumen_ampliado(motor)
        jugar(estructurada, GeneradorAcciones(7), 20)
        jugar(completa, GeneradorAcciones(7), 20)
        iguales = iguales and resumen_ampliado(estructurada) == resumen_ampliado(completa)
        with sin_recolector():
            t_estructurada = medir_ms(lambda: materializar(copiar(motor), GestorTerreno()), repeticiones)
            t_completa = medir_ms(lambda: _completo(motor), repeticiones)
        lineas.append(f"M9 N={salas:<3} resúmenes {'iguales' if iguales else 'DISTINTOS'} (antes y tras 20 acciones más: "
                      f"{'cumple' if iguales else 'NO CUMPLE'}) | copiar+materializar {t_estructurada:8.3f} ms | deepcopy completo {t_completa:8.3f} ms")
    return _bloque("-M9: oráculo de la copia: estructurada frente a deepcopy completo, N <= 60 (T109; FR-017, FR-021)-", lineas)


# ───────────────────────── justificación del K por omisión (T113) ─────────────────────────

def _dato(medicion, k, n=None):
    for nombre, kk, nn, valor in DATOS_K:
        if nombre == medicion and kk == k and (n is None or nn == n):
            return valor
    return None


def _celda(valor, formato):
    return "      -" if valor is None else format(valor, formato)


def justificar_k(rapido=None):
    """Tabla de M1, M2, M5 y M6 por K y el K por omisión que sale de ella (T113; FR-018, SC-007, SC-002).

    Un K **cumple** si todas las consultas medidas tardan menos de `LIMITE_CONSULTA_MS` (SC-002) y, además, su p95 por
    `MARGEN_DE_VELOCIDAD` sigue por debajo de ese límite: una máquina más lenta que ésta seguiría cumpliendo. Se usa el p95 y
    no el máximo para el margen porque el máximo de 200 consultas lo fija un solo valor atípico (en dos corridas seguidas el de
    K = 50 pasó de 18 a 21 ms). Regla: **se conserva el K vigente mientras cumpla**; si deja de cumplir, el mayor K que cumpla
    (más K, menos puntos: menos memoria y guardar y cargar más rápidos). La alternativa sin puntos de control no cumple."""
    rapido = _rapido(rapido)
    ks = []
    for nombre, k, n, _ in DATOS_K:
        if nombre == "M1 máx" and k != SIN_PUNTOS and k not in ks:
            ks.append(k)
    if not ks:
        return []
    n_memoria = 5000 if not rapido else 30
    lineas = [f"T113 regla: cumple el K con todas las consultas < {LIMITE_CONSULTA_MS} ms y p95 x {MARGEN_DE_VELOCIDAD} < "
              f"{LIMITE_CONSULTA_MS} ms; se conserva el K vigente mientras cumpla, y si no, el mayor K que cumpla",
              f"T113 memoria con n = {n_memoria}; reconstruir con n = {n_memoria} (sin @cargar)"]
    cumplen = []
    for k in ks:
        maximo = _dato("M1 máx", k)
        p95 = _dato("M1 p95", k)
        cumple = maximo < LIMITE_CONSULTA_MS and p95 * MARGEN_DE_VELOCIDAD < LIMITE_CONSULTA_MS
        if cumple:
            cumplen.append(k)
        lineas.append(f"T113 {nombre_k(k):<8} consulta: p95 {_celda(p95, '7.2f')} ms (margen x{LIMITE_CONSULTA_MS / p95:5.1f}) "
                      f"máx {_celda(maximo, '7.2f')} ms (margen x{LIMITE_CONSULTA_MS / maximo:4.1f}) | memoria "
                      f"{_celda(_dato('M2 KiB', k, n_memoria), '9.1f')} KiB | registrar p95 {_celda(_dato('M5 p95', k), '7.3f')} ms | "
                      f"reconstruir {_celda(_dato('M6 ms', k, n_memoria), '8.1f')} ms   {'cumple' if cumple else 'NO cumple'}")
    sin_maximo = _dato("M1 máx", SIN_PUNTOS)
    if sin_maximo is not None:
        sin_p95 = _dato("M1 p95", SIN_PUNTOS)
        lineas.append(f"T113 sin puntos de control: consulta p95 {sin_p95:7.2f} ms máx {sin_maximo:7.2f} ms (margen x"
                      f"{LIMITE_CONSULTA_MS / sin_maximo:4.2f}): {'cumple' if sin_maximo < LIMITE_CONSULTA_MS else 'NO cumple'}; memoria "
                      f"{_celda(_dato('M2 KiB', SIN_PUNTOS, n_memoria), '9.1f')} KiB")
    if not cumplen:
        lineas.append("T113 ningún K cumple con estos datos: hay que revisar (plan B de T098)")
    else:
        if K_POR_OMISION in cumplen:
            elegido, motivo = K_POR_OMISION, "se conserva el vigente porque cumple"
        else:
            elegido, motivo = max(cumplen), "el vigente no cumple: se elige el mayor que cumple"
        lineas.append(f"T113 también cumplen: {', '.join(str(k) for k in cumplen)}; los datos no distinguen entre ellos en el "
                      "peor caso (el máximo lo fija un valor atípico): más K ahorra memoria, menos K da consultas más cortas")
        lineas.append(f"T113 K por omisión: {elegido} ({motivo}); K_POR_OMISION vale {K_POR_OMISION}: "
                      f"{'sin cambios' if elegido == K_POR_OMISION else 'DIFIERE: cambiar la constante y los textos que dicen ' + str(K_POR_OMISION)}")
    # cifras de M3 de esta misma corrida (las que M3 dejó en DATOS_K); sin M3 en la corrida, se dice que no hay
    m3 = [(s, _dato("M3 materializar", None, s)) for s in (20, 200, 2000)]
    m3 = [(s, v) for s, v in m3 if v is not None]
    if m3:
        partes = [f"{v:.1f} ms con N = {s:,}".replace(",", " ") for s, v in m3]
        texto_m3 = "M3: materializar pasa de " + partes[0]
        if len(partes) == 2:
            texto_m3 += f" a {partes[1]}"
        elif len(partes) == 3:
            texto_m3 += f" a {partes[1]} y a {partes[2]}"
    else:
        texto_m3 = "M3: no se midió en esta corrida"
    lineas.append("T113 HIPÓTESIS (no medido): el margen de 2.5x es una elección del grupo, no una medición; las medidas son de "
                  "esta máquina y de una cripta sintética de 20 salas; con criptas mayores el costo de cada punto crece "
                  f"({texto_m3}), lo que pesa en contra de un K grande")
    return _bloque("-T113: justificación del K por omisión (FR-018, SC-002, SC-007)-", lineas)


# ───────────────────────── despachador ─────────────────────────

# (nombre, función): las dos del retroceso (M4 y M10) reciben los datos de las mismas partidas
MEDICIONES = (("M1", medir_m1), ("M2", medir_m2), ("M3", medir_m3), ("M4", medir_m4), ("M5", medir_m5), ("M6", medir_m6),
              ("M7", medir_m7), ("M8", medir_m8), ("M9", medir_m9), ("M10", medir_m10))
NOMBRES = tuple(nombre for nombre, _ in MEDICIONES)


def _resto_de_la_hipotesis(rapido):
    return ["", "-Lo que no se midió-",
            "no medido (HIPÓTESIS): costo de la agenda (P1 §4.1), que esta capacidad no mide [PERSONAS: grupo]",
            "no medido (HIPÓTESIS): M2 con K = 1 y n > 2 500; M3 con N > 2 000; M4 con n > 50 000"]


def correr_bench(nombres=None, rapido=None, ruta=None):
    """Corre las mediciones (todas si `nombres` es None) y escribe resultados_bench_linea.txt (o `ruta`). Con algunas
    solo las muestra: el archivo es el de la corrida completa. Devuelve las líneas."""
    rapido = _rapido(rapido)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    DATOS_K.clear()
    inicio = time.perf_counter()
    datos_retroceso = None
    cuerpo = []
    for nombre, medir in MEDICIONES:
        if nombres is not None and nombre not in nombres:
            continue
        if nombre in ("M4", "M10"):
            if datos_retroceso is None:
                datos_retroceso = _datos_de_retroceso(rapido)    # las dos mediciones salen de las mismas partidas
            cuerpo += medir(rapido, datos_retroceso)
        else:
            cuerpo += medir(rapido)
    total = time.perf_counter() - inicio
    cuerpo += ["", f"duración de la corrida: {total:.1f} s"]
    if nombres is None:
        cuerpo = cuerpo[:-2] + justificar_k(rapido) + _resto_de_la_hipotesis(rapido) + cuerpo[-2:]
        return escribir_resultados(cuerpo, ruta, rapido)
    for linea in encabezado(rapido) + cuerpo:
        print(linea)
    return cuerpo


if __name__ == "__main__":
    pedidas = [a.upper() for a in sys.argv[1:]]
    desconocidas = [a for a in pedidas if a not in NOMBRES]
    if desconocidas:
        sys.exit(f"Mediciones desconocidas: {', '.join(desconocidas)} (válidas: M1 a M10)")
    correr_bench(pedidas or None)
