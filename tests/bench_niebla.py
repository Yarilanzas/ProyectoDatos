# Mediciones de la capacidad de niebla de guerra, mapa conocido e «ir a» (Fase 6, M1 a M6; research R9).
# Base de la medición (T100): mediana de varias repeticiones y escritura de resultados_bench_niebla.txt con equipo y
# versión de Python, igual que tests/bench_ciclo.py. M1 a M6 (T101 a T106) se agregan aquí; `--bench` la llama (T107).
# Sin red y sin vista: no inicia partidas, así que no pasa por nueva_partida ni necesita forzar=True.
# Los mapas son sintéticos (tests/mapas_sinteticos.py), sin datos de ninguna cripta real.
# Atiende: PR-15, SC-006, Principio VIII.
#
# Principio I: la mediana usa el ordenamiento propio del repositorio (Modelo/ordenamiento.py), ni el ordenamiento
# ni las estadísticas de la biblioteca estándar.

import os
import platform
import sys
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.Conocimiento import _CAMBIO_SALA, Conocimiento, DESCONOCIDA, EXPLORADA, SIN_OBSERVAR
from Modelo.ordenamiento import merge_sort
from Modelo.retroceso import Historial
from tests.mapas_sinteticos import salas_sinteticas

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


def encabezado():
    return [
        "-Niebla de guerra, mapa conocido e «ir a» (Fase 6, M1 a M6)-",
        f"equipo: {platform.platform()} | {platform.processor() or platform.machine()}"
        f" | Python {platform.python_version()}",
        f"cada dato es la mediana de {REPETICIONES} repeticiones, sin red ni vista, con mapas sintéticos",
        f"resultado provisional: el límite de {LIMITE_PASO_IR_A_MS} ms de §6.1 se define para la cripta de "
        "referencia, que aún no está publicada",
    ]


def escribir_resultados(lineas, ruta=ARCHIVO_RESULTADOS):
    """Escribe el encabezado y ``lineas`` en ``ruta`` y los muestra en consola."""
    todas = encabezado() + list(lineas)
    for linea in todas:
        print(linea)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(todas) + "\n")


# --- Filas de resultados ---------------------------------------------------------------------------------------------

class Fila:
    """Una fila de resultado: qué medición, qué variante, con qué parámetros, cuánto tardó y qué hipótesis contrasta.
    ``ms`` es None si no se pudo medir; entonces ``nota`` dice por qué y la hipótesis queda como no medida."""

    def __init__(self, medicion, variante, parametros, ms, hipotesis, nota=""):
        self.medicion = medicion
        self.variante = variante
        self.parametros = tuple(parametros)  # pares (nombre, valor), en el orden en que se muestran
        self.ms = ms
        self.hipotesis = hipotesis
        self.nota = nota

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
        nota = f" ({self.nota})" if self.nota else ""
        return (f"{self.medicion} {self.variante:<16} {parametros:<28} {self.ms:10.4f} ms   "
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


# --- Resultados -----------------------------------------------------------------------------------------------------

def _seccion(titulo, filas):
    return [titulo] + [fila.texto() for fila in filas]


def correr_bench(ruta=ARCHIVO_RESULTADOS):
    lineas = []
    lineas += _seccion(f"M1: consultar estado de sala y recuerdo de puerta, {CONSULTAS_M1} consultas por fila "
                       "(R1; FR-001, FR-005)", medir_m1())
    lineas += _seccion("M2: revelar r salas con k ya conocidas (R1; FR-003, FR-009)", medir_m2())
    lineas += _seccion("M3: registrar y deshacer una entrada con antorcha (R2; FR-014)", medir_m3())
    lineas.append("M4 a M6: pendientes (T104 a T106)")
    escribir_resultados(lineas, ruta)

if __name__ == "__main__":
    correr_bench()
