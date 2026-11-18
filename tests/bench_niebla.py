# Mediciones de la capacidad de niebla de guerra, mapa conocido e «ir a» (Fase 6, M1 a M6; research R9).
# Base de la medición (T100): mediana de varias repeticiones y escritura de resultados_bench_niebla.txt con equipo y
# versión de Python, igual que tests/bench_ciclo.py. M1 a M6 (T101 a T106) se agregan aquí; `--bench` la llama (T107).
# Sin red y sin vista: no pasa por nueva_partida ni crear_paquete_niebla, así que no necesita forzar=True. M6 arma
# el motor a mano con `iniciar_partida`, como tests/bench_ciclo.py.
# Los mapas son sintéticos (tests/mapas_sinteticos.py), sin datos de ninguna cripta real. La única excepción es la
# fila de M4 de la cripta sustituta de la de referencia (T110): la mayor de las copias locales
# (`datos_locales/esqueleto_<id>.json`). Su esqueleto se lee al correr, nunca se escribe en este archivo
# (Principio IV), y solo se lee. HIPÓTESIS: la cripta de referencia del enunciado (§6.1) aún no está publicada.
# Atiende: PR-15, SC-006, SC-007, Principio VIII.
#
# Principio I: la mediana usa el ordenamiento propio del repositorio (Modelo/ordenamiento.py), ni el ordenamiento
# ni las estadísticas de la biblioteca estándar.

import contextlib
import io
import json
import os
import platform
import random
import sys
import tempfile
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from AlmacenamientoLocalApi.AlmacenamientoLocalApi import AlmacenamientoLocalApi
from DTOS.SalaEsqueleto import SalaEsqueleto
from DTOS.Salida import Salida
from Modelo.Conocimiento import _CAMBIO_SALA, Conocimiento, DESCONOCIDA, EXPLORADA, GrafoConocido, SIN_OBSERVAR
from Modelo.Enemigo import Enemigo
from Modelo.Jugador import Jugador
from Modelo.MotorSimulacion import MotorSimulacion
from Modelo.BusquedaRuta import EspacioBusqueda
from Modelo.ordenamiento import merge_sort
from Modelo.retroceso import Historial
from Modelo.rutas_ir_a import primer_paso
from Persistencia.ArchivoPartida import LectorPartida, guardar_partida
from Persistencia.ConversorPartida import registro_conocimiento_desde_motor
from Persistencia.ExportadorJSON import cargar_conocimiento_json, guardar_partida_json
from Persistencia.RegistroSala import RegistroSala
from tests.bench_ciclo import CICLOS as CICLOS_CICLO, ENEMIGOS as ENEMIGOS_CICLO, LIMITE_MS as LIMITE_MS_CICLO
from tests.mapas_sinteticos import cadena, grilla, salas_sinteticas

# Límite del cálculo de un paso de «ir a», en ms, con el mapa conocido completo de la cripta de referencia
# (enunciado §6.1; plan.md, P-08). El valor puede cambiar por enmienda: este es el único lugar que lo escribe,
# y M4 (T104) compara contra esta constante.
LIMITE_PASO_IR_A_MS = 5

REPETICIONES = 7
ARCHIVO_RESULTADOS = "resultados_bench_niebla.txt"


def _identidad(valor):
    return valor


def mediana(valores):
    """Mediana de ``valores``; con cantidad par, el promedio de los dos centrales. No cambia la entrada.
    O(r log r) con r = len(valores), por merge_sort."""
    if len(valores) == 0:
        raise ValueError("mediana de una lista vacía")
    ordenados, _ = merge_sort(valores, _identidad)
    centro = len(ordenados) // 2
    if len(ordenados) % 2 == 1:
        return ordenados[centro]
    return (ordenados[centro - 1] + ordenados[centro]) / 2


def medir_ms(funcion, repeticiones=REPETICIONES, reloj=time.perf_counter_ns):
    """Llama ``funcion`` ``repeticiones`` veces y devuelve la mediana de los tiempos, en ms.
    ``reloj`` devuelve nanosegundos; se puede cambiar en las pruebas."""
    if repeticiones < 1:
        raise ValueError("repeticiones debe ser >= 1")
    tiempos = []
    for _ in range(repeticiones):
        inicio = reloj()
        funcion()
        tiempos.append((reloj() - inicio) / 1_000_000)
    return mediana(tiempos)


def encabezado(repeticiones=REPETICIONES):
    return [
        "-Niebla de guerra, mapa conocido e «ir a» (Fase 6, M1 a M6)-",
        f"equipo: {platform.platform()} | {platform.processor() or platform.machine()}"
        f" | Python {platform.python_version()}",
        f"cada dato es la mediana de {repeticiones} repeticiones (M6: mediana y p95 de los ciclos), sin red ni "
        "vista, con mapas sintéticos y, en M4, el esqueleto de la mayor de las copias locales de datos_locales",
        f"M4: las filas sintéticas son pruebas de estrés, con resultado provisional (PROVISIONAL); la medición del "
        f"límite de {LIMITE_PASO_IR_A_MS} ms de §6.1 es la fila «referencia/paso», con el mapa conocido completo "
        "de la cripta sustituta (la mayor de las copias locales); HIPÓTESIS: la cripta de referencia del "
        "enunciado aún no está publicada",
    ]


def escribir_resultados(lineas, ruta=ARCHIVO_RESULTADOS, repeticiones=REPETICIONES):
    """Escribe el encabezado y ``lineas`` en ``ruta`` y los muestra en consola."""
    todas = encabezado(repeticiones) + list(lineas)
    for linea in todas:
        print(linea)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(todas) + "\n")


# --- Filas de resultados ---------------------------------------------------------------------------------------------

class Fila:
    """Una fila de resultado: qué medición, qué variante, con qué parámetros, cuánto tardó y qué hipótesis contrasta.
    ``ms`` es None si no se pudo medir; entonces ``nota`` dice por qué y la hipótesis queda como no medida."""

    def __init__(self, medicion, variante, parametros, ms, hipotesis, nota="", veredicto="", provisional=False,
                 p95=None):
        self.medicion = medicion
        self.variante = variante
        self.parametros = tuple(parametros)  # pares (nombre, valor), en el orden en que se muestran
        self.ms = ms
        self.hipotesis = hipotesis
        self.nota = nota
        self.veredicto = veredicto        # «cumple» o «no cumple» frente a un límite (M4, M6); vacío si no aplica
        self.provisional = provisional    # M4: mapa sintético, sin veredicto definitivo de §6.1 (T110)
        self.p95 = p95                    # M6: percentil 95 de los ciclos, en ms

    def valor(self, nombre):
        # O(p), p parámetros (dos o tres): recorrido lineal, sin dict como índice.
        for clave, valor in self.parametros:
            if clave == nombre:
                return valor
        return None

    def texto(self):
        parametros = " ".join(f"{clave}={valor}" for clave, valor in self.parametros)
        if self.ms is None:
            return (f"{self.medicion} {self.variante:<16} {parametros:<28} no medido (ms)   "
                    f"hipótesis no medida: {self.hipotesis}. Motivo: {self.nota}")
        p95 = f" p95 {self.p95:10.4f} ms" if self.p95 is not None else ""
        veredicto = ""
        if self.veredicto:
            veredicto = f"   {'PROVISIONAL ' if self.provisional else ''}{self.veredicto}"
        nota = f" ({self.nota})" if self.nota else ""
        return (f"{self.medicion} {self.variante:<16} {parametros:<28} {self.ms:10.4f} ms{p95}{veredicto}   "
                f"hipótesis: {self.hipotesis}{nota}")


def _medir_fila(medicion, variante, parametros, funcion, repeticiones, hipotesis, nota=""):
    # Si la medición falla, la fila lo dice y la hipótesis queda sin medir: no se inventa un número.
    try:
        ms = float(medir_ms(funcion, repeticiones))
    except Exception as error:  # noqa: BLE001 - se informa en la fila
        return Fila(medicion, variante, parametros, None, hipotesis, f"{type(error).__name__}: {error}")
    return Fila(medicion, variante, parametros, ms, hipotesis, nota)


# --- Salas sintéticas como objetos ----------------------------------------------------------------------------------
# `Conocimiento` recibe objetos con `id` y `salidas` (dict dirección -> salida con `cerrada`), como los DTO del juego.
# El dict `salidas` es el del registro de la sala, que `Conocimiento` solo recorre: no es un índice (Principio I).

ORDEN_DIRECCIONES = ("N", "S", "E", "O")


class SalaSintetica:
    def __init__(self, id_sala, nombre=""):
        self.id = id_sala
        self.nombre = nombre
        self.salidas = {}


class SalidaSintetica:
    def __init__(self, destino, costo=1, cerrada=False):
        self.destino = destino      # el objeto sala, ya resuelto
        self.sala = destino.id
        self.costo = costo
        self.cerrada = cerrada


def _destino(salida):
    return salida.destino


class _HistorialNulo:
    # Para preparar el estado sin registrar nada.
    def registrar(self, deshacer, description=""):
        pass


_SIN_HISTORIAL = _HistorialNulo()


def objetos_sinteticos(esqueleto, cerrar_cada=0):
    """Objetos sala y salida a partir de la lista de tests/mapas_sinteticos.py. Los ids son 1..n en orden, así que el
    destino se resuelve por posición. Con ``cerrar_cada`` > 0, una de cada tantas salidas queda cerrada. O(n + e)."""
    salas = [SalaSintetica(datos["id"], datos["nombre"]) for datos in esqueleto]
    contador = 0
    for posicion in range(len(esqueleto)):
        for direccion, datos in esqueleto[posicion]["salidas"].items():
            cerrada = cerrar_cada > 0 and contador % cerrar_cada == 0
            salas[posicion].salidas[direccion] = SalidaSintetica(salas[datos["sala"] - 1], datos["costo"], cerrada)
            contador += 1
    return salas


def _indice_direccion(direccion):
    for indice in range(len(ORDEN_DIRECCIONES)):
        if ORDEN_DIRECCIONES[indice] == direccion:
            return indice
    raise ValueError(f"dirección desconocida: {direccion}")


def clave_puerta(salida):
    """Clave de una puerta dirigida en las líneas base: (id de la sala de origen, índice de la dirección).
    Usa `_origen` y `_direccion`, que `Conocimiento` asigna a cada salida."""
    return (salida._origen.id, _indice_direccion(salida._direccion))


# --- Líneas base (solo para medir; no son código del juego) ---------------------------------------------------------

class ListaOrdenada:
    """Pares (clave, valor) ordenados por clave, con búsqueda binaria escrita a mano (Principio I).

    | Operación          | Complejidad                       |
    |--------------------|-----------------------------------|
    | buscar             | O(log k)                          |
    | insertar / quitar  | O(log k + k): desplaza elementos  |
    | agregar (al final) | O(1)                              |
    """

    def __init__(self):
        self._pares = []

    def _posicion(self, clave):
        # Primera posición cuya clave no es menor que `clave`.
        ini, fin = 0, len(self._pares)
        while ini < fin:
            medio = (ini + fin) // 2
            if self._pares[medio][0] < clave:
                ini = medio + 1
            else:
                fin = medio
        return ini

    def buscar(self, clave, defecto=None):
        posicion = self._posicion(clave)
        if posicion < len(self._pares) and self._pares[posicion][0] == clave:
            return self._pares[posicion][1]
        return defecto

    def insertar(self, clave, valor):
        # Si la clave ya está, cambia su valor.
        posicion = self._posicion(clave)
        if posicion < len(self._pares) and self._pares[posicion][0] == clave:
            self._pares[posicion] = (clave, valor)
        else:
            self._pares.insert(posicion, (clave, valor))

    def agregar(self, clave, valor):
        # Para construirla en orden: la clave debe ser mayor que la última.
        if self._pares and not self._pares[-1][0] < clave:
            raise ValueError("agregar exige claves en orden creciente")
        self._pares.append((clave, valor))

    def quitar(self, clave):
        posicion = self._posicion(clave)
        if posicion < len(self._pares) and self._pares[posicion][0] == clave:
            self._pares.pop(posicion)

    def pares(self):
        return list(self._pares)


class ListaLineal:
    """Pares (clave, valor) sin orden, con búsqueda lineal. buscar, insertar y quitar: O(k); agregar: O(1)."""

    def __init__(self):
        self._pares = []

    def _posicion(self, clave):
        for posicion in range(len(self._pares)):
            if self._pares[posicion][0] == clave:
                return posicion
        return -1

    def buscar(self, clave, defecto=None):
        posicion = self._posicion(clave)
        return defecto if posicion < 0 else self._pares[posicion][1]

    def insertar(self, clave, valor):
        posicion = self._posicion(clave)
        if posicion < 0:
            self._pares.append((clave, valor))
        else:
            self._pares[posicion] = (clave, valor)

    def agregar(self, clave, valor):
        # Sin comprobar si ya está: solo para construirla con claves distintas.
        self._pares.append((clave, valor))

    def quitar(self, clave):
        posicion = self._posicion(clave)
        if posicion >= 0:
            self._pares.pop(posicion)

    def pares(self):
        return list(self._pares)


# --- M1: consultar estado de sala y recuerdo de puerta (T101; research R1; FR-001, FR-005) --------------------------

TAMANOS_M1 = (20, 200, 2000, 20000)
CONSULTAS_M1 = 100

HIPOTESIS_M1 = (
    ("arreglos", "el tiempo de los arreglos no crece con n (O(1))"),
    ("binaria", "la lista ordenada con binaria crece con log n"),
    ("lineal", "línea base: la lista lineal crece con n"),
)


def preparar_m1(n):
    """Conocimiento real sobre ``n`` salas sintéticas con los tres estados y los tres recuerdos mezclados: se entra
    sin antorcha a una de cada tres salas de la primera mitad, y una de cada cinco salidas está cerrada. O(n + e)."""
    salas = objetos_sinteticos(salas_sinteticas(n), cerrar_cada=5)
    conocimiento = Conocimiento(salas, _destino)
    for posicion in range(0, n // 2, 3):
        conocimiento.entrar(salas[posicion], False, _SIN_HISTORIAL)
    return conocimiento, salas


def lineas_base_m1(conocimiento):
    """Las mismas salas reveladas y puertas observadas que ``conocimiento``, en lista ordenada y en lista lineal.
    Devuelve (ordenada_salas, lineal_salas, ordenada_puertas, lineal_puertas). Lo no revelado no se guarda: buscarlo
    da el valor por defecto (DESCONOCIDA o SIN_OBSERVAR), igual que en los arreglos.
    La ordenada se arma recorriendo las salas por id y sus salidas en orden N, S, E, O, así que ya sale en orden;
    la lineal sigue el orden de revelación. O(n + e)."""
    ordenada_salas, lineal_salas = ListaOrdenada(), ListaLineal()
    ordenada_puertas, lineal_puertas = ListaOrdenada(), ListaLineal()

    for sala in conocimiento._salas:  # salas sintéticas: posición = orden por id
        estado = conocimiento.estado(sala)
        if estado != DESCONOCIDA:
            ordenada_salas.agregar(sala.id, estado)
        for direccion in ORDEN_DIRECCIONES:
            salida = sala.salidas.get(direccion)
            if salida is not None and conocimiento.recuerdo(salida) != SIN_OBSERVAR:
                ordenada_puertas.agregar(clave_puerta(salida), conocimiento.recuerdo(salida))

    for sala in conocimiento.reveladas:
        lineal_salas.agregar(sala.id, conocimiento.estado(sala))
    for salida in conocimiento.observadas:
        lineal_puertas.agregar(clave_puerta(salida), conocimiento.recuerdo(salida))

    return ordenada_salas, lineal_salas, ordenada_puertas, lineal_puertas


def _consultas_m1(salas, consultas):
    # Salas repartidas por todo el mapa, siempre las mismas para cada variante; de cada una, su primera salida.
    elegidas = [salas[(indice * 7919) % len(salas)] for indice in range(consultas)]
    salidas = [next(iter(sala.salidas.values())) for sala in elegidas]
    return elegidas, salidas


def medir_m1(tamanos=TAMANOS_M1, repeticiones=REPETICIONES, consultas=CONSULTAS_M1):
    """M1: ``consultas`` consultas de estado de sala y de recuerdo de puerta por cada ``n``. El tiempo de cada fila
    es el de todas las consultas juntas. Las claves de las líneas base se calculan antes de medir."""
    filas = []
    for n in tamanos:
        conocimiento, salas = preparar_m1(n)
        ordenada_salas, lineal_salas, ordenada_puertas, lineal_puertas = lineas_base_m1(conocimiento)
        elegidas, salidas = _consultas_m1(salas, consultas)
        ids = [sala.id for sala in elegidas]
        claves = [clave_puerta(salida) for salida in salidas]
        parametros = (("n", n), ("consultas", consultas))

        def sala_arreglos():
            for sala in elegidas:
                conocimiento.estado(sala)

        def puerta_arreglos():
            for salida in salidas:
                conocimiento.recuerdo(salida)

        def buscar_todas(lista, claves_lista, defecto):
            def consultar():
                for clave in claves_lista:
                    lista.buscar(clave, defecto)
            return consultar

        funciones = (
            ("sala", (sala_arreglos, buscar_todas(ordenada_salas, ids, DESCONOCIDA),
                      buscar_todas(lineal_salas, ids, DESCONOCIDA))),
            ("puerta", (puerta_arreglos, buscar_todas(ordenada_puertas, claves, SIN_OBSERVAR),
                        buscar_todas(lineal_puertas, claves, SIN_OBSERVAR))),
        )
        for objeto, por_variante in funciones:
            for indice in range(len(HIPOTESIS_M1)):
                variante, hipotesis = HIPOTESIS_M1[indice]
                filas.append(_medir_fila("M1", f"{objeto}/{variante}", parametros, por_variante[indice],
                                         repeticiones, hipotesis))
    return filas


# --- M2: revelar r salas con k ya conocidas (T102; research R1; FR-003, FR-009) -------------------------------------
# Se mide escribir los r cambios de sala de una entrada con antorcha y deshacerlos (para repetir desde el mismo
# estado), que es lo que cambia entre representaciones; calcular cuáles son es igual en ambas y no se mide.

TAMANOS_M2 = (10, 100, 1000, 10000)
HIPOTESIS_M2_ARREGLOS = "con arreglos no crece con k"
HIPOTESIS_M2_LISTA = "con lista ordenada crece con k (insertar desplaza)"


def preparar_m2(k):
    """Conocimiento real con exactamente ``k`` salas exploradas (las de id más alto) en un mapa de 2k + 100 salas,
    el lote de salas de entrar con antorcha a la sala 1 (ya deshecho) y la lista ordenada con lo mismo conocido.
    Las salas reveladas tienen los ids más bajos: en la lista ordenada se insertan al frente (peor caso)."""
    salas = objetos_sinteticos(salas_sinteticas(2 * k + 100))
    conocimiento = Conocimiento(salas, _destino)
    conocidas = [(_CAMBIO_SALA, sala._ordinal, DESCONOCIDA, EXPLORADA) for sala in salas[len(salas) - k:]]
    conocimiento.aplicar(conocidas)

    lote = conocimiento.entrar(salas[0], True, _SIN_HISTORIAL)
    conocimiento.invertir(lote)
    lote_salas = [cambio for cambio in lote if cambio[0] == _CAMBIO_SALA]

    lista = ListaOrdenada()
    for sala in salas:
        estado = conocimiento.estado(sala)
        if estado != DESCONOCIDA:
            lista.agregar(sala.id, estado)
    return conocimiento, lote_salas, lista


def revelar_en_lista(lista, lote, conocimiento):
    # Escribe en la lista los cambios de sala del lote, en su orden. O(r (log k + k)).
    for tipo, ordinal, _, nuevo in lote:
        if tipo == _CAMBIO_SALA:
            lista.insertar(conocimiento._salas[ordinal].id, nuevo)


def deshacer_en_lista(lista, lote, conocimiento):
    # Deshace en la lista los cambios de sala del lote, al revés. O(r (log k + k)).
    for indice in range(len(lote) - 1, -1, -1):
        tipo, ordinal, anterior, _ = lote[indice]
        if tipo != _CAMBIO_SALA:
            continue
        id_sala = conocimiento._salas[ordinal].id
        if anterior == DESCONOCIDA:
            lista.quitar(id_sala)
        else:
            lista.insertar(id_sala, anterior)


def medir_m2(tamanos=TAMANOS_M2, repeticiones=REPETICIONES):
    filas = []
    for k in tamanos:
        conocimiento, lote, lista = preparar_m2(k)
        parametros = (("k", k), ("r", len(lote)))

        def con_arreglos():
            conocimiento.aplicar(lote)
            conocimiento.invertir(lote)

        def con_lista():
            revelar_en_lista(lista, lote, conocimiento)
            deshacer_en_lista(lista, lote, conocimiento)

        filas.append(_medir_fila("M2", "arreglos", parametros, con_arreglos, repeticiones, HIPOTESIS_M2_ARREGLOS,
                                 "revelar y deshacer"))
        filas.append(_medir_fila("M2", "lista ordenada", parametros, con_lista, repeticiones, HIPOTESIS_M2_LISTA,
                                 "revelar y deshacer; inserción al frente"))
    return filas


# --- M3: registrar y deshacer una entrada con antorcha (T103; research R2; FR-014) ----------------------------------
# Tres formas de registrar el cambio en el Historial: el lote real de `Conocimiento`, un cierre por cada escritura y
# una copia completa. Las dos últimas son líneas base escritas aquí; el juego usa el lote.

TAMANOS_M3_N = (200, 2000, 20000)
VECINAS_M3 = (4, 16, 64)


def preparar_m3(n, vecinas):
    """``n`` salas: la primera (el centro) tiene ``vecinas`` salidas a las salas 2..vecinas+1, con vuelta, y las demás
    forman una cadena E-O. Entrar con antorcha al centro escribe un número de cambios r que crece con ``vecinas``.
    Los mapas de tests/mapas_sinteticos.py tienen a lo sumo 4 salidas por sala, por eso aquí se arma una estrella."""
    if n < vecinas + 2:
        raise ValueError("n debe ser al menos vecinas + 2")
    salas = [SalaSintetica(posicion + 1, f"Sala {posicion + 1}") for posicion in range(n)]
    centro = salas[0]
    for posicion in range(1, vecinas + 1):
        centro.salidas[f"V{posicion}"] = SalidaSintetica(salas[posicion])
        salas[posicion].salidas["C"] = SalidaSintetica(centro)
    for posicion in range(1, n - 1):
        salas[posicion].salidas["E"] = SalidaSintetica(salas[posicion + 1])
        salas[posicion + 1].salidas["O"] = SalidaSintetica(salas[posicion])
    return salas, centro


class ConocimientoCierres(Conocimiento):
    """Línea base de M3: igual que `Conocimiento`, pero registra un cierre (`lambda`) por cada escritura en vez de un
    solo lote (research R2, alternativa descartada). Solo para medir."""

    def entrar(self, sala, antorcha, historial):
        self._historial_actual = historial
        return Conocimiento.entrar(self, sala, antorcha, historial)

    def _registrar(self, lote, historial):
        pass  # cada escritura ya registró su cierre

    def _cambiar_sala(self, sala, valor, lote):
        ordinal = sala._ordinal
        anterior = self.estado_sala[ordinal]
        Conocimiento._cambiar_sala(self, sala, valor, lote)

        def deshacer():
            self.estado_sala[ordinal] = anterior
            if anterior == DESCONOCIDA:
                self.reveladas.pop()

        self._historial_actual.registrar(deshacer=deshacer, description="conocimiento: sala")

    def _observar(self, salida, lote):
        ordinal = salida._ordinal
        anterior = self.recuerdo_puerta[ordinal]
        Conocimiento._observar(self, salida, lote)
        if self.recuerdo_puerta[ordinal] == anterior:
            return

        def deshacer():
            self.recuerdo_puerta[ordinal] = anterior
            if anterior == SIN_OBSERVAR:
                self.observadas.pop()

        self._historial_actual.registrar(deshacer=deshacer, description="conocimiento: puerta")


def _crear_conocimiento(salas):
    return Conocimiento(salas, _destino)


def _crear_con_cierres(salas):
    return ConocimientoCierres(salas, _destino)


def _registrar_entrando(conocimiento, centro, historial):
    # Lote (el real) o cierres (la subclase): la diferencia está en cómo registra `entrar`.
    conocimiento.entrar(centro, True, historial)


def _restaurar_desde(conocimiento, copia):
    conocimiento.estado_sala = copia.estado_sala
    conocimiento.recuerdo_puerta = copia.recuerdo_puerta
    conocimiento.reveladas = copia.reveladas
    conocimiento.observadas = copia.observadas


def _registrar_copia(conocimiento, centro, historial):
    # Copia completa antes de cambiar, O(n + e); deshacer vuelve a esa copia.
    copia = conocimiento.copiar()
    conocimiento.entrar(centro, True, _SIN_HISTORIAL)
    historial.registrar(deshacer=lambda: _restaurar_desde(conocimiento, copia), description="conocimiento: copia")


VARIANTES_M3 = (
    ("lote", _crear_conocimiento, _registrar_entrando),
    ("cierres", _crear_con_cierres, _registrar_entrando),
    ("copia", _crear_conocimiento, _registrar_copia),
)

HIPOTESIS_M3 = (
    ("lote", "el lote crece con r y no con n"),
    ("cierres", "los cierres crecen con r (un Cambio y una función por escritura)"),
    ("copia", "la copia crece con n"),
)


def estado_de(conocimiento):
    """Todo lo que cambia al entrar, comparable con ==: estados, recuerdos y el orden de reveladas y observadas."""
    return (list(conocimiento.estado_sala), list(conocimiento.recuerdo_puerta),
            [sala.id for sala in conocimiento.reveladas],
            [(salida._origen.id, salida._direccion) for salida in conocimiento.observadas])


def medir_m3(tamanos=TAMANOS_M3_N, vecinas=VECINAS_M3, repeticiones=REPETICIONES):
    """M3: abrir un intervalo, registrar la entrada con antorcha al centro y deshacerla, por variante, ``n`` y
    ``vecinas``. r es la cantidad de escrituras de esa entrada (el tamaño del lote real)."""
    filas = []
    for n in tamanos:
        for cantidad in vecinas:
            salas, centro = preparar_m3(n, cantidad)
            r = len(Conocimiento(salas, _destino).entrar(centro, True, _SIN_HISTORIAL))
            parametros = (("n", n), ("vecinas", cantidad), ("r", r))
            for indice in range(len(VARIANTES_M3)):
                variante, crear, registrar = VARIANTES_M3[indice]
                conocimiento = crear(salas)

                def registrar_y_deshacer(conocimiento=conocimiento, registrar=registrar):
                    historial = Historial()
                    historial.abrir_intervalo()
                    registrar(conocimiento, centro, historial)
                    historial.deshacer_ultimo()

                filas.append(_medir_fila("M3", variante, parametros, registrar_y_deshacer, repeticiones,
                                         HIPOTESIS_M3[indice][1], "registrar y deshacer"))
    return filas


# --- M4: un paso y un viaje completo de «ir a» por `primer_paso` (T104; research R9; FR-024, FR-026, SC-007) -------
# Se mide la interfaz real, `Modelo.rutas_ir_a.primer_paso`, que delega en `Modelo/BusquedaRuta.py` de Persona A.
# Nunca un buscador de prueba: ese número no diría nada del juego. El grafo es un `GrafoConocido` real sobre un
# `Conocimiento` con todo el mapa explorado y todas las puertas abiertas (el «mapa conocido completo»), y el costo de
# cada salida lo da `motor.costo_salida`, como en el juego.
# PROVISIONAL: los mapas sintéticos son pruebas de estrés. El límite de §6.1 se define para la cripta de referencia;
# su medición, sobre la cripta sustituta (la mayor de las copias locales), es la fila «referencia/paso» (T110,
# `medir_m4_referencia`), no estas.

TAMANOS_M4 = (25, 100, 400, 2500)
TOPOLOGIAS_M4 = (("grilla", grilla), ("cadena", cadena))
NOTA_PROVISIONAL_M4 = ("mapa sintético, prueba de estrés; la medición de §6.1 es la fila de la cripta sustituta")


def veredicto_paso(ms):
    """«cumple» si ``ms`` no pasa de `LIMITE_PASO_IR_A_MS` (§6.1: 5 ms o menos), «no cumple» si lo pasa.
    Lee la constante en cada llamada, así que una enmienda solo cambia la constante."""
    return "cumple" if ms <= LIMITE_PASO_IR_A_MS else "no cumple"


def preparar_m4(generar, cantidad):
    """Mapa conocido completo de ``generar(cantidad)`` (cadena o grilla de tests/mapas_sinteticos.py): se entra sin
    antorcha a cada sala, así que todas quedan exploradas y todas sus puertas recordadas como abiertas.
    Devuelve (grafo, origen, destino): la primera sala y la última, el extremo opuesto del mapa. O(V + e)."""
    salas = objetos_sinteticos(generar(cantidad))
    conocimiento = Conocimiento(salas, _destino)
    for sala in salas:
        conocimiento.entrar(sala, False, _SIN_HISTORIAL)
    grafo = GrafoConocido(conocimiento, MotorSimulacion(semilla=0).costo_salida)
    return grafo, salas[0], salas[-1]


def viaje_m4(grafo, origen, destino, espacio=None):
    """Recorre el viaje paso a paso como «ir a»: en cada sala pide `primer_paso` hasta el destino y avanza a la
    vecina del paso. Devuelve la lista de pasos. ``espacio`` es un `EspacioBusqueda` reutilizado en todo el viaje,
    o None para que `primer_paso` cree uno por llamada (T109 mide ambos)."""
    pasos = []
    actual = origen
    while actual is not destino:
        paso = primer_paso(grafo, actual, destino, None, espacio)
        if paso is None:
            raise ValueError(f"sin ruta de {actual.id} a {destino.id}")
        pasos.append(paso)
        if len(pasos) > grafo.cantidad_salas:
            raise ValueError("el viaje no termina: más pasos que salas")
        actual = paso.destino
    return pasos


def _fila_m4(variante, parametros, funcion, repeticiones, pasos, hipotesis):
    fila = _medir_fila("M4", variante, parametros, funcion, repeticiones, hipotesis, NOTA_PROVISIONAL_M4)
    fila.provisional = True
    if fila.ms is not None:
        fila.veredicto = veredicto_paso(fila.ms / pasos)
    return fila


def medir_m4(tamanos=TAMANOS_M4, repeticiones=REPETICIONES, espacio=None):
    """M4: por topología y V, una fila con un paso desde la primera sala hasta la última (la ruta más larga del mapa)
    y otra con el viaje completo. El veredicto compara contra `LIMITE_PASO_IR_A_MS`: el del paso, su tiempo; el del
    viaje, el promedio por paso. Todas las filas son provisionales.

    ``espacio``: None, o una función que recibe la cantidad de salas y devuelve un `EspacioBusqueda` (por ejemplo la
    clase misma), que se crea una vez por mapa, fuera de la medición, y se reutiliza en cada paso. Es para T109."""
    filas = []
    for nombre, generar in TOPOLOGIAS_M4:
        for cantidad in tamanos:
            grafo, origen, destino = preparar_m4(generar, cantidad)
            reutilizado = None if espacio is None else espacio(grafo.cantidad_salas)
            pasos = len(viaje_m4(grafo, origen, destino, reutilizado))
            modo = ("espacio", "por llamada" if reutilizado is None else "reutilizado")

            def un_paso(grafo=grafo, origen=origen, destino=destino, reutilizado=reutilizado):
                primer_paso(grafo, origen, destino, None, reutilizado)

            def viaje(grafo=grafo, origen=origen, destino=destino, reutilizado=reutilizado):
                viaje_m4(grafo, origen, destino, reutilizado)

            filas.append(_fila_m4(f"{nombre}/paso", (("V", cantidad), ("pasos", 1), modo), un_paso, repeticiones,
                                  1, f"un paso con el mapa conocido completo tarda {LIMITE_PASO_IR_A_MS} ms o menos "
                                     "(§6.1)"))
            filas.append(_fila_m4(f"{nombre}/viaje", (("V", cantidad), ("pasos", pasos), modo), viaje,
                                  repeticiones, pasos, "dato de apoyo: el viaje crece con los pasos; veredicto con "
                                                       "el promedio por paso"))
    return filas


# --- M4 con la cripta sustituta de la de referencia (T110; FR-024, SC-007, PR-15) -----------------------------------
# HIPÓTESIS: la cripta de referencia del enunciado (§6.1) aún no está publicada. Se usa como sustituta la mayor de
# las copias locales de esqueletos que guarda la caché (`AlmacenamientoLocalApi.guardar_esqueleto`, formato
# {"version", "esqueleto"}). La fila «referencia/paso» es la medición de §6.1 sobre esa sustituta; el veredicto
# definitivo depende de la publicación de la cripta de referencia. Ningún dato de la sustituta
# está en este archivo (Principio IV): el id sale del nombre del archivo, y la versión y las salas, de su contenido, al correr.
# La carpeta solo se lee: si no hay copias, la fila sale «no medido» con el motivo y el bench sigue.

CARPETA_DATOS_LOCALES = os.path.join(RAIZ, "datos_locales")
PREFIJO_ESQUELETO = "esqueleto_"
EXTENSION_ESQUELETO = ".json"
NOTA_REFERENCIA_M4 = ("la mayor de las copias locales ({id_cripta}, {salas} salas), usada como sustituta de la cripta "
                      "de referencia (HIPÓTESIS: la del enunciado, §6.1, aún no está publicada)")
HIPOTESIS_REFERENCIA_M4 = (f"el peor paso con el mapa conocido completo de la cripta sustituta tarda "
                           f"{LIMITE_PASO_IR_A_MS} ms o menos (§6.1)")
# Cribado y confirmación: todos los pares alcanzables se miden con 1 repetición, y los K más lentos del cribado se
# vuelven a medir con la mediana de `repeticiones`. La fila da el máximo de esas medianas.
CONFIRMADOS_M4_REFERENCIA = 50


def cripta_mas_grande(carpeta=CARPETA_DATOS_LOCALES):
    """(id, versión, cantidad de salas) de la copia local con más salas entre los `esqueleto_<id>.json` de
    ``carpeta``; en empate, la de id menor. None si la carpeta no existe o no tiene copias. Solo lee. O(archivos)."""
    if not os.path.isdir(carpeta):
        return None
    elegida = None
    for nombre in os.listdir(carpeta):
        if not (nombre.startswith(PREFIJO_ESQUELETO) and nombre.endswith(EXTENSION_ESQUELETO)):
            continue
        with open(os.path.join(carpeta, nombre), encoding="utf-8") as archivo:
            datos = json.load(archivo)
        candidata = (nombre[len(PREFIJO_ESQUELETO):-len(EXTENSION_ESQUELETO)], datos["version"],
                     len(datos["esqueleto"]))
        if (elegida is None or candidata[2] > elegida[2]
                or (candidata[2] == elegida[2] and candidata[0] < elegida[0])):
            elegida = candidata
    return elegida


def _id_de_sala(sala):
    return sala.id


def _buscar_por_id(ordenadas, id_sala):
    """Búsqueda binaria de ``id_sala`` en ``ordenadas`` (salas por id, ascendente). None si no está. O(log n)."""
    bajo, alto = 0, len(ordenadas) - 1
    while bajo <= alto:
        medio = (bajo + alto) // 2
        actual = ordenadas[medio].id
        if actual == id_sala:
            return ordenadas[medio]
        if actual < id_sala:
            bajo = medio + 1
        else:
            alto = medio - 1
    return None


def preparar_m4_referencia(carpeta=CARPETA_DATOS_LOCALES):
    """Mapa conocido completo del esqueleto real de la cripta sustituta (la mayor de las copias locales). Devuelve
    (id, grafo, salas), o None si no hay copias locales.

    Lee con `AlmacenamientoLocalApi.cargar_esqueleto`, con la versión que trae el propio archivo, así que las salas
    son los `SalaEsqueleto` y `Salida` del juego. El destino de cada salida (`sala_destino`, un id) se resuelve una
    vez por búsqueda binaria sobre las salas ordenadas por id con `merge_sort`, sin dict ni set como índice
    (Principio I), y queda en `salida.destino`, que es lo que lee `_destino`.

    Como `preparar_m4`, se entra sin antorcha a cada sala: todas quedan exploradas y cada puerta queda recordada con
    su estado real del esqueleto. Las puertas cerradas (con llave) quedan recordadas cerradas y no entran al grafo.
    El grafo es dirigido: una puerta cerrada en un sentido puede estar abierta en el otro. Por eso no todo par de
    salas es alcanzable, y la medición solo usa pares que lo son. El costo de cada salida lo da
    `motor.costo_salida`, como en el juego. O(V log V + e)."""
    cripta = cripta_mas_grande(carpeta)
    if cripta is None:
        return None
    id_cripta, version, _ = cripta
    salas = AlmacenamientoLocalApi(carpeta).cargar_esqueleto(id_cripta, version)
    if salas is None:
        raise ValueError(f"la copia local de {id_cripta} no se pudo leer con su versión {version}")
    ordenadas, _ = merge_sort(salas, _id_de_sala)
    for sala in salas:
        for salida in sala.salidas.values():
            salida.destino = _buscar_por_id(ordenadas, salida.sala_destino)
    conocimiento = Conocimiento(salas, _destino)
    for sala in salas:
        conocimiento.entrar(sala, False, _SIN_HISTORIAL)
    grafo = GrafoConocido(conocimiento, MotorSimulacion(semilla=0).costo_salida)
    return id_cripta, grafo, salas


def _distancias_desde(grafo, origen, espacio):
    """Dijkstra completo hacia adelante desde ``origen`` sobre ``grafo.aristas``, sin destino ni cota. Usa las listas
    por ordinal y la `ColaPrioridad` de ``espacio`` (un `EspacioBusqueda`, sin modificar su código): al terminar,
    ``espacio.dist[k]`` vale para cada ordinal k con ``espacio.epoca[k] == espacio.epoca_actual``; los demás no son
    alcanzables. Principio I: listas y cola propias, sin dict ni set como índice. O((V + E) log E)."""
    espacio.reiniciar()
    dist, epoca, sala, cola = espacio.dist, espacio.epoca, espacio.sala, espacio.cola
    vigente = espacio.epoca_actual
    inicio = grafo.ordinal(origen)
    dist[inicio], epoca[inicio], sala[inicio] = 0, vigente, origen
    cola.insertar(0, inicio)
    while not cola.vacia():
        distancia, ordinal = cola.extraer_minimo()
        if distancia > dist[ordinal]:
            continue  # entrada vieja de la inserción perezosa
        for _direccion, vecina, costo in grafo.aristas(sala[ordinal]):
            nueva = distancia + costo
            otro = grafo.ordinal(vecina)
            if epoca[otro] != vigente or nueva < dist[otro]:
                dist[otro], epoca[otro], sala[otro] = nueva, vigente, vecina
                cola.insertar(nueva, otro)


def pares_alcanzables(grafo, salas, espacio=None):
    """[(origen, destino, costo)]: todos los pares distintos (origen, destino) con ruta en ``grafo``, en el orden de
    ``salas`` (origen y luego destino), con el costo acumulado mínimo. Se enumeran con las distancias de
    `_distancias_desde` (un Dijkstra completo por origen), no con un `primer_paso` por par. Los orígenes sin ningún
    destino alcanzable no aportan pares. ``espacio`` es un `EspacioBusqueda` para ``grafo.cantidad_salas``; None crea
    uno. O(V · (V + E) log E)."""
    if espacio is None:
        espacio = EspacioBusqueda(grafo.cantidad_salas)
    else:
        espacio.validar(grafo)
    pares = []
    for origen in salas:
        _distancias_desde(grafo, origen, espacio)
        vigente = espacio.epoca_actual
        for destino in salas:
            ordinal = grafo.ordinal(destino)
            if destino is not origen and espacio.epoca[ordinal] == vigente:
                pares.append((origen, destino, espacio.dist[ordinal]))
    return pares


def _ms_del_cribado(medido):
    return medido[0]


def medir_m4_referencia(repeticiones=REPETICIONES, espacio=None, carpeta=CARPETA_DATOS_LOCALES):
    """M4 de §6.1 (T110): el peor caso de un paso de «ir a» en el mapa conocido completo de la cripta sustituta (la
    mayor de las copias locales; HIPÓTESIS: la cripta de referencia del enunciado aún no está publicada, así que el
    veredicto no es definitivo). Cada par se mide como el paso de `medir_m4` (`medir_ms` de `primer_paso`).

    Cribado y confirmación: (1) se miden TODOS los pares alcanzables (`pares_alcanzables`) con 1 repetición cada
    uno; (2) los `CONFIRMADOS_M4_REFERENCIA` (K) pares más lentos del cribado se vuelven a medir con la mediana de
    ``repeticiones``; si hay menos de K pares, se confirman todos; (3) la fila da el máximo de esas medianas. Reporta
    cuántos orígenes aportan pares («origenes»), cuántos pares hay («pares»), cuántos se confirmaron
    («confirmados»), el par del máximo («peor») y su costo acumulado («costo»). El veredicto es `veredicto_paso` del
    máximo, contra `LIMITE_PASO_IR_A_MS`. La fila no es provisional.

    ``espacio``: como en `medir_m4`; el `EspacioBusqueda` se crea una vez y se reutiliza en todos los pares medidos.
    Si no hay copias locales, o no se pueden leer, devuelve una fila «no medido» con el motivo: no falla."""
    modo = ("espacio", "por llamada" if espacio is None else "reutilizado")
    try:
        preparado = preparar_m4_referencia(carpeta)
    except Exception as error:  # noqa: BLE001 - se informa en la fila
        return [Fila("M4", "referencia/paso", (("pasos", 1), modo), None, HIPOTESIS_REFERENCIA_M4,
                     f"no se pudo leer la copia local del esqueleto: {type(error).__name__}: {error}")]
    if preparado is None:
        return [Fila("M4", "referencia/paso", (("pasos", 1), modo), None, HIPOTESIS_REFERENCIA_M4,
                     f"no hay copias locales de esqueletos ({PREFIJO_ESQUELETO}<id>{EXTENSION_ESQUELETO}) en "
                     f"{carpeta}; se omite la medición de §6.1")]
    id_cripta, grafo, salas = preparado
    reutilizado = None if espacio is None else espacio(grafo.cantidad_salas)

    def paso(origen, destino):
        def un_paso():
            primer_paso(grafo, origen, destino, None, reutilizado)
        return un_paso

    try:
        pares = pares_alcanzables(grafo, salas, reutilizado)
        # (1) Cribado: 1 repetición por par.
        cribado = []
        for indice in range(len(pares)):
            origen, destino, _ = pares[indice]
            cribado.append((float(medir_ms(paso(origen, destino), 1)), indice))
        # (2) Confirmación: los K más lentos (los últimos del orden ascendente), con la mediana de `repeticiones`.
        ordenado, _ = merge_sort(cribado, _ms_del_cribado)
        confirmar = ordenado[max(0, len(ordenado) - CONFIRMADOS_M4_REFERENCIA):]
        peor_ms, peor_par = None, None
        for _, indice in confirmar:
            origen, destino, costo = pares[indice]
            ms = float(medir_ms(paso(origen, destino), repeticiones))
            if peor_ms is None or ms > peor_ms:
                peor_ms, peor_par = ms, (origen, destino, costo)
    except Exception as error:  # noqa: BLE001 - se informa en la fila
        return [Fila("M4", "referencia/paso", (("cripta", id_cripta), ("pasos", 1), modo), None,
                     HIPOTESIS_REFERENCIA_M4, f"{type(error).__name__}: {error}")]
    if peor_ms is None:
        return [Fila("M4", "referencia/paso", (("cripta", id_cripta), ("pasos", 1), modo), None,
                     HIPOTESIS_REFERENCIA_M4, "el mapa conocido completo no tiene ningún par de salas alcanzable")]
    origenes = 0
    for indice in range(len(pares)):
        if indice == 0 or pares[indice][0] is not pares[indice - 1][0]:
            origenes += 1  # los pares vienen agrupados por origen
    parametros = (("cripta", id_cripta), ("V", len(salas)), ("pasos", 1), ("origenes", origenes),
                  ("pares", len(pares)), ("confirmados", len(confirmar)),
                  ("peor", f"{peor_par[0].id}->{peor_par[1].id}"), ("costo", peor_par[2]), modo)
    nota = NOTA_REFERENCIA_M4.format(id_cripta=id_cripta, salas=len(salas))
    return [Fila("M4", "referencia/paso", parametros, peor_ms, HIPOTESIS_REFERENCIA_M4, nota,
                 veredicto=veredicto_paso(peor_ms), provisional=False)]


# --- M5: tamaño y tiempo del bloque de conocimiento; bytes leídos al cargar (T105; research R3, R9; FR-015) ----------
# Con las funciones reales de Persistencia: `registro_conocimiento_desde_motor` arma el bloque, `guardar_partida` y
# `guardar_partida_json` escriben el archivo, y `LectorPartida.leer_conocimiento` y `cargar_conocimiento_json` lo
# leen. El archivo tiene un registro de sala por cada una de las n salas, para que «cargar no lee las salas» se vea.
# «guardar» mide armar y serializar el bloque (binario: to_bytes; JSON: to_dict y json.dumps compacto, como
# ExportadorJSON); escribir el archivo no se mide porque incluye fsync. «cargar» mide abrir el archivo y leer el
# bloque. `bytes` es el tamaño del bloque y `leidos` lo que lee el cargado: en binario, `LectorPartida.bytes_leidos`;
# en JSON, el archivo entero, porque json.load no puede leer una parte.

TAMANOS_M5 = (20, 200, 2000)
SALAS_POR_EXPLORADA_M5 = 4


class MotorM5:
    """Lo que `registro_conocimiento_desde_motor` lee del motor: `conocimiento` y `salas`. Solo para medir."""

    def __init__(self, conocimiento, salas):
        self.conocimiento = conocimiento
        self.salas = salas


def preparar_m5(k):
    """``k`` salas exploradas (entrando sin antorcha) en un mapa de 4k salas con una de cada cinco salidas cerrada,
    así el bloque tiene exploradas, recuerdos abiertos y cerrados, y puertas reales. O(n + e)."""
    salas = objetos_sinteticos(salas_sinteticas(SALAS_POR_EXPLORADA_M5 * k), cerrar_cada=5)
    conocimiento = Conocimiento(salas, _destino)
    for sala in salas[:k]:
        conocimiento.entrar(sala, False, _SIN_HISTORIAL)
    return MotorM5(conocimiento, salas)


def _rutas_m5(carpeta):
    return os.path.join(carpeta, "partida_m5.dat"), os.path.join(carpeta, "partida_m5.json")


def _bloque_json(registro):
    # Mismo JSON compacto que ExportadorJSON para el campo "conocimiento".
    return json.dumps(registro.to_dict(), separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _cargar_binario(ruta):
    with LectorPartida(ruta) as lector:
        registro = lector.leer_conocimiento()
        return registro, lector.bytes_leidos


def ida_y_vuelta_m5(motor, carpeta):
    """Guarda la partida de ``motor`` en binario y en JSON dentro de ``carpeta`` y carga el conocimiento de cada uno.
    Devuelve (original, desde_binario, desde_json, bytes_leidos_binario, bytes_leidos_json)."""
    original = registro_conocimiento_desde_motor(motor)
    registros = [RegistroSala(sala.id, -1, [], [], [], []) for sala in motor.salas]
    ruta_binaria, ruta_json = _rutas_m5(carpeta)
    guardar_partida(ruta_binaria, "bench", "1", "1", 0, 0, registros, conocimiento=original)
    guardar_partida_json(ruta_json, "bench", "1", "1", 0, 0, registros, conocimiento=original)
    desde_binario, leidos_binario = _cargar_binario(ruta_binaria)
    desde_json = cargar_conocimiento_json(ruta_json)
    return original, desde_binario, desde_json, leidos_binario, os.path.getsize(ruta_json)


def medir_m5(tamanos=TAMANOS_M5, repeticiones=REPETICIONES):
    filas = []
    for k in tamanos:
        motor = preparar_m5(k)
        with tempfile.TemporaryDirectory() as carpeta:
            original, _, _, leidos_binario, leidos_json = ida_y_vuelta_m5(motor, carpeta)
            ruta_binaria, ruta_json = _rutas_m5(carpeta)
            n = len(motor.salas)
            binario = (("k", k), ("n", n), ("bytes", len(original.to_bytes())), ("leidos", leidos_binario))
            texto = (("k", k), ("n", n), ("bytes", len(_bloque_json(original))), ("leidos", leidos_json))

            def guardar_binario():
                registro_conocimiento_desde_motor(motor).to_bytes()

            def guardar_json():
                _bloque_json(registro_conocimiento_desde_motor(motor))

            filas.append(_medir_fila("M5", "binario/guardar", binario, guardar_binario, repeticiones,
                                     "el bloque crece con lo conocido"))
            filas.append(_medir_fila("M5", "binario/cargar", binario, lambda: _cargar_binario(ruta_binaria),
                                     repeticiones, "cargar lee el bloque y no las salas"))
            filas.append(_medir_fila("M5", "json/guardar", texto, guardar_json, repeticiones,
                                     "línea base: el bloque JSON crece con lo conocido"))
            filas.append(_medir_fila("M5", "json/cargar", texto, lambda: cargar_conocimiento_json(ruta_json),
                                     repeticiones, "línea base: JSON lee el archivo completo"))
    return filas


# --- M6: ciclo completo entre decisiones, con y sin conocimiento (T106; research R9; FR-014, SC-006) ----------------
# Reusa tests/bench_ciclo.py: sus tamaños (ENEMIGOS), sus ciclos (CICLOS) y su límite de 20 ms (§5.2). El montaje es
# el de `bench_ciclo_real` de tests/bench_motor.py (que bench_ciclo llama), copiado aquí porque esa función no deja
# quitar el conocimiento y calcula la mediana y el p95 con la biblioteca estándar; aquí van con merge_sort.
# Las dos variantes corren el mismo ciclo, con las mismas semillas: «sin conocimiento» solo pone
# `motor.conocimiento = None` tras `iniciar_partida`, como los motores de la Parte I (H7). No usa nueva_partida.

ENEMIGOS_M6 = tuple(ENEMIGOS_CICLO)
CICLOS_M6 = CICLOS_CICLO
LIMITE_CICLO_MS = LIMITE_MS_CICLO
SALAS_M6 = 200


def percentil(valores, porcentaje):
    """Valor en la posición min(r - 1, ⌊r · porcentaje / 100⌋) de ``valores`` ordenados, igual que el p95 de
    bench_ciclo. Ordena con merge_sort (Principio I) y no cambia la entrada. O(r log r)."""
    if len(valores) == 0:
        raise ValueError("percentil de una lista vacía")
    ordenados, _ = merge_sort(valores, _identidad)
    return ordenados[min(len(ordenados) - 1, int(len(ordenados) * porcentaje / 100))]


def preparar_m6(enemigos, con_conocimiento):
    """Motor real con una cadena de 200 salas, el jugador en el medio y ``enemigos`` enemigos activos, igual que
    `bench_ciclo_real`. Con ``con_conocimiento`` False se quita el conocimiento después de iniciar."""
    salas = [SalaEsqueleto(i, f"s{i}", {}) for i in range(1, SALAS_M6 + 1)]
    for i in range(SALAS_M6 - 1):
        salas[i].salidas["E"] = Salida(salas[i + 1].id, False, None, None)
        salas[i + 1].salidas["O"] = Salida(salas[i].id, False, None, None)
    azar = random.Random(2)
    jugador = Jugador("J", 10**9, 10**9, 1, 0, 100, salas[SALAS_M6 // 2])
    lista = [Enemigo(f"e{i:05d}", 10, 10, 1, 0, azar.choice((80, 100, 150)),
                     azar.choice(("errante", "rastreador", "guardian")),
                     sala=salas[azar.randrange(SALAS_M6)]) for i in range(enemigos)]
    motor = MotorSimulacion(semilla=1)
    with contextlib.redirect_stdout(io.StringIO()):
        motor.iniciar_partida(jugador, salas, lista)
        for enemigo in lista:
            motor.activar_enemigo(enemigo)
    if not con_conocimiento:
        motor.conocimiento = None  # el motor lo tolera (H7): así jugaba la Parte I
    return motor


def ciclo_m6(motor):
    """Un ciclo completo entre dos decisiones del jugador: esperar y que actúen todos los enemigos."""
    motor.ejecutar_accion("esperar")


def medir_m6(enemigos=ENEMIGOS_M6, ciclos=CICLOS_M6):
    """M6: por tamaño y variante, ``ciclos`` ciclos medidos uno a uno; la fila da la mediana (ms) y el p95, y el
    veredicto compara el p95 con `LIMITE_CICLO_MS` (por debajo de 20 ms, como bench_ciclo)."""
    filas = []
    for cantidad in enemigos:
        for variante, con_conocimiento in (("con conocimiento", True), ("sin conocimiento", False)):
            parametros = (("enemigos", cantidad), ("ciclos", ciclos))
            hipotesis = f"sin regresión frente a {LIMITE_CICLO_MS} ms (§5.2)"
            try:
                motor = preparar_m6(cantidad, con_conocimiento)
                tiempos = []
                with contextlib.redirect_stdout(io.StringIO()):
                    for _ in range(ciclos):
                        inicio = time.perf_counter_ns()
                        ciclo_m6(motor)
                        tiempos.append((time.perf_counter_ns() - inicio) / 1_000_000)
                ms, p95 = float(mediana(tiempos)), float(percentil(tiempos, 95))
            except Exception as error:  # noqa: BLE001 - se informa en la fila
                filas.append(Fila("M6", variante, parametros, None, hipotesis, f"{type(error).__name__}: {error}"))
                continue
            fila = Fila("M6", variante, parametros, ms, hipotesis, "ms = mediana", p95=p95,
                        veredicto="cumple" if p95 < LIMITE_CICLO_MS else "no cumple")
            filas.append(fila)
    return filas


# --- Resultados -----------------------------------------------------------------------------------------------------

def _seccion(titulo, filas):
    return [titulo] + [fila.texto() for fila in filas]


class TamanosBench:
    """Tamaños de cada medición. Por omisión, los de research R9 (los de `--bench`); la prueba rápida (T108) usa
    `TAMANOS_MINIMOS`. Solo datos."""

    def __init__(self, m1=TAMANOS_M1, consultas_m1=CONSULTAS_M1, m2=TAMANOS_M2, m3_n=TAMANOS_M3_N,
                 m3_vecinas=VECINAS_M3, m4=TAMANOS_M4, m5=TAMANOS_M5, m6_enemigos=ENEMIGOS_M6,
                 m6_ciclos=CICLOS_M6, repeticiones=REPETICIONES):
        self.m1 = m1
        self.consultas_m1 = consultas_m1
        self.m2 = m2
        self.m3_n = m3_n
        self.m3_vecinas = m3_vecinas
        self.m4 = m4
        self.m5 = m5
        self.m6_enemigos = m6_enemigos
        self.m6_ciclos = m6_ciclos
        self.repeticiones = repeticiones


TAMANOS_MINIMOS = TamanosBench(m1=(20,), consultas_m1=3, m2=(10,), m3_n=(50,), m3_vecinas=(2,), m4=(25,), m5=(20,),
                               m6_enemigos=(10,), m6_ciclos=2, repeticiones=1)


def correr_bench(ruta=ARCHIVO_RESULTADOS, tamanos=None, datos_locales=CARPETA_DATOS_LOCALES):
    """Corre M1 a M6 y escribe ``ruta`` con el encabezado (equipo y versión de Python). Devuelve las filas.
    M4 se mide dos veces (T109): con un `EspacioBusqueda` nuevo en cada llamada a `primer_paso` y con uno
    reutilizado en todo el viaje. En cada una, además de los mapas sintéticos, va la fila de la cripta sustituta
    de la de referencia, la mayor de las copias locales de ``datos_locales`` (T110). ``tamanos`` es un `TamanosBench`; None usa los de research R9."""
    t = TamanosBench() if tamanos is None else tamanos
    secciones = (
        (f"M1: consultar estado de sala y recuerdo de puerta, {t.consultas_m1} consultas por fila "
         "(R1; FR-001, FR-005)", medir_m1(t.m1, t.repeticiones, t.consultas_m1)),
        ("M2: revelar r salas con k ya conocidas (R1; FR-003, FR-009)", medir_m2(t.m2, t.repeticiones)),
        ("M3: registrar y deshacer una entrada con antorcha (R2; FR-014)",
         medir_m3(t.m3_n, t.m3_vecinas, t.repeticiones)),
        (f"M4: un paso y un viaje de «ir a» por primer_paso, límite {LIMITE_PASO_IR_A_MS} ms por paso, con y sin "
         f"EspacioBusqueda reutilizado (R6; FR-024, FR-026, SC-007). Filas sintéticas, PROVISIONAL: "
         f"{NOTA_PROVISIONAL_M4}. Fila «referencia/paso»: medición de §6.1, el peor paso del mapa conocido "
         "completo de la cripta sustituta (cribado de todos los pares alcanzables con 1 repetición y confirmación "
         f"de los {CONFIRMADOS_M4_REFERENCIA} más lentos con la mediana), la mayor de las copias locales (T110; "
         "HIPÓTESIS: la cripta de referencia del enunciado aún no está publicada)",
         # Las filas de la cripta sustituta van después de todas las sintéticas: medirlas entre los dos
         # bloques sintéticos alteraba las filas que venían después.
         medir_m4(t.m4, t.repeticiones) + medir_m4(t.m4, t.repeticiones, espacio=EspacioBusqueda)
         + medir_m4_referencia(t.repeticiones, None, datos_locales)
         + medir_m4_referencia(t.repeticiones, EspacioBusqueda, datos_locales)),
        ("M5: bloque de conocimiento, binario frente a JSON; bytes = bloque, leidos = al cargar (R3; FR-015)",
         medir_m5(t.m5, t.repeticiones)),
        (f"M6: ciclo completo con y sin conocimiento, {t.m6_ciclos} ciclos por fila, límite {LIMITE_CICLO_MS} ms "
         "al p95 (R1, R2; FR-014, SC-006)", medir_m6(t.m6_enemigos, t.m6_ciclos)),
    )
    lineas, filas = [], []
    for titulo, propias in secciones:
        lineas += _seccion(titulo, propias)
        filas += propias
    escribir_resultados(lineas, ruta, t.repeticiones)
    return filas

if __name__ == "__main__":
    correr_bench()
