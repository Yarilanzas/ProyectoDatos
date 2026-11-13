# Utilidades de prueba de la línea de tiempo (spec 004, T009 y T010; SC-003, FR-001, FR-008, FR-025).
# Este archivo no lleva prefijo test: `unittest discover` no lo ejecuta. Sin red: arma paquetes offline temporales
# con `crear_paquete_niebla`. Ninguna prueba que use esto depende de partida.cripta, partida.cripta.log ni partida.log
# (FR-024): la bitácora y los datos locales viven en una carpeta temporal propia de cada partida.
#
# Interfaz
# --------
# GeneradorAcciones(semilla).siguiente(motor) -> (nombre, argumento)      acciones deterministas, sin tocar el azar del motor
# jugar(motor, generador, cantidad) -> lista de (nombre, argumento)       las acciones que el motor aceptó
# resumen_ampliado(motor) -> resumen + mensajes + rastros                 lo que se compara contra un clon
# preparar_motor_linea(motor, espiar=True) -> motor                       lo vuelve MotorLinea: espía y cazador doble
# partida_linea(...) -> PartidaLinea                                      motor + controlador + rutas, en carpeta propia
# agregar_cazador(motor, id_enemigo, id_sala) -> Enemigo                  doble del cazador (T010)
# agregar_enemigo(motor, id_enemigo, id_sala, comportamiento) -> Enemigo  p. ej. un «errante», que consume azar

import os
import random
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from API.Fuentes import FuenteDatosOffline
from Controlador.ControladorPartida import ControladorPartida
from Gestor.GestorDatos import GestorDatos
from Modelo.Enemigo import Enemigo
from Modelo.MotorSimulacion import MotorSimulacion
from tests.test_integracion import VistaFalsa
from tests.utiles_niebla import CRIPTA_NIEBLA, ENEMIGO, TRAMPA, contenido_sala, crear_paquete_niebla, salida

SIN_ATRIBUTO = "sin rastro"  # lo que `resumen_ampliado` anota de una sala sin el atributo `rastro`
NOMBRE_BITACORA = "linea.log"
NOMBRE_DATOS = "datos_locales"
NOMBRE_PAQUETE = "paquete"

# Seis salas con ciclos, sin puertas cerradas: resoluble (FR-021 de la spec 002) y con varias rutas.
#   1 -E- 2 -E- 3
#   |     |     |
#   S     S     S
#   4 -E- 5 -E- 6
SALAS_LINEA = [
    {"id": 1, "nombre": "Entrada", "salidas": {"E": salida(2), "S": salida(4)}},
    {"id": 2, "nombre": "Pasillo", "salidas": {"O": salida(1), "E": salida(3), "S": salida(5)}},
    {"id": 3, "nombre": "Capilla", "salidas": {"O": salida(2), "S": salida(6)}},
    {"id": 4, "nombre": "Almacén", "salidas": {"N": salida(1), "E": salida(5)}},
    {"id": 5, "nombre": "Cámara", "salidas": {"N": salida(2), "O": salida(4), "E": salida(6)}},
    {"id": 6, "nombre": "Salida", "salidas": {"N": salida(3), "O": salida(5)}},
]

CONTENIDO_LINEA = [
    contenido_sala(2, enemigos=("e-rata-1",)),
    contenido_sala(5, trampas=("t-dardos-1",)),
]

# vida alta para que el generador no termine la partida antes de tiempo
JUGADOR_RESISTENTE = {"vida_max": 100000, "ataque": 6, "defensa": 1, "velocidad": 100}

DIRECCIONES = ("N", "S", "E", "O")


# ───────────────────────── Generador de acciones ─────────────────────────

class GeneradorAcciones:
    """Elige entre atacar, esperar y mover con un `random.Random(semilla)` **propio**: nunca toca `motor.azar`, así que
    jugar con él no cambia lo que consume la simulación. Misma semilla y mismo estado, mismas acciones.

    `siguiente(motor)` devuelve (nombre, argumento) con el mismo texto que la bitácora: `mover N`, `atacar e-rata-1`,
    `esperar` sin argumento."""

    def __init__(self, semilla):
        self.azar = random.Random(semilla)

    def siguiente(self, motor):
        jugador = motor.jugador
        vecinos = [e for e in motor.obtener_enemigos(sala=jugador.sala, solo_vivos=True)]
        if vecinos and self.azar.random() < 0.7:
            return "atacar", str(vecinos[self.azar.randrange(len(vecinos))].id)

        # nunca entra en la sala de salida: ganar terminaría la partida y cortaría la prueba
        abiertas = [direccion for direccion in DIRECCIONES
                    if direccion in jugador.sala.salidas and not jugador.sala.salidas[direccion].cerrada
                    and jugador.sala.salidas[direccion].sala_destino != motor.sala_salida]
        if abiertas and self.azar.random() < 0.75:
            return "mover", abiertas[self.azar.randrange(len(abiertas))]
        return "esperar", ""


def jugar(motor, generador, cantidad):
    """Ejecuta hasta `cantidad` acciones del generador y devuelve las **aceptadas**, en orden, como (nombre, argumento).
    Se detiene si la partida termina."""
    aceptadas = []
    intentos = 0
    while len(aceptadas) < cantidad and intentos < cantidad * 4:
        intentos += 1
        if motor.jugador is None or not motor.jugador.esta_vivo() or motor.victoria:
            break
        nombre, argumento = generador.siguiente(motor)
        if motor.ejecutar_accion(nombre, argumento):
            aceptadas.append((nombre, argumento))
    return aceptadas


# ───────────────────────── Comparación ampliada ─────────────────────────

def resumen_ampliado(motor):
    """`obtener_estado_resumen()` (que ya trae el `conocimiento`) más lo que ese resumen no ve: los `mensajes` en
    pantalla y los `rastros` de todas las salas (una sala sin atributo `rastro` se anota como SIN_ATRIBUTO, distinto de
    `None`). Se compara con `==`."""
    resumen = motor.obtener_estado_resumen()
    resumen["mensajes"] = motor.mensajes.ultimos()
    resumen["rastros"] = [(sala.id, getattr(sala, "rastro", SIN_ATRIBUTO)) for sala in motor.salas]
    return resumen


# ───────────────────────── Motor espía y cazador doble ─────────────────────────

class MotorLinea(MotorSimulacion):
    """Motor de prueba: se comporta como `MotorSimulacion`, con dos agregados que solo existen aquí.

    1. **Espía** (T009): si `espiar` es True, guarda en `resumenes` el `resumen_ampliado` tras cada evento ejecutado.
    2. **Doble del cazador** (T010): un `Enemigo` con `comportamiento == "cazador"` decide con una regla fija.

    Se usa con `preparar_motor_linea(motor)`, que cambia la clase de un motor ya armado (sin red) y le agrega sus listas.
    Todo el estado cuelga del motor (nada a nivel de módulo), así que `deepcopy` lo copia y la re-simulación lo repite."""

    espiar = False
    resumenes = None
    decisiones_cazador = None

    def ejecutar_evento(self, evento):
        super().ejecutar_evento(evento)
        if self.espiar:
            self.resumenes.append(resumen_ampliado(self))

    # REPETIR CON EL REAL: el enemigo con comportamiento «cazador» de A (003-T045 a T048) aún no está en main.
    # Mismo nombre de tarea de T079 y T118 de la spec 004. Doble mínimo: no consume azar y anota cada decisión.
    def accion_enemigo(self, enemigo, jugador):
        if enemigo.comportamiento == "cazador" and enemigo.sala is not jugador.sala:
            return "MOVER_RASTRO"  # el hueco del motor que acepta una salida elegida por una regla (no por azar)
        return super().accion_enemigo(enemigo, jugador)

    def salida_rastro(self, enemigo):
        if enemigo.comportamiento != "cazador":
            return super().salida_rastro(enemigo)
        return self._salida_cazador(enemigo)

    def _distancias_al_jugador(self):
        """Saltos hasta la sala del jugador desde cada sala (por ordinal de `grafo_cripta`), con las puertas de ahora.
        Búsqueda en anchura sobre las entrantes, con una lista como cola. -1 = no llega."""
        grafo = self.grafo_cripta
        distancia = [-1] * grafo.cantidad_salas
        cola = [self.jugador.sala]
        distancia[grafo.ordinal(self.jugador.sala)] = 0
        cabeza = 0
        while cabeza < len(cola):
            sala = cola[cabeza]
            cabeza += 1
            for _direccion, origen, _costo in grafo.entrantes(sala):
                if distancia[grafo.ordinal(origen)] == -1:
                    distancia[grafo.ordinal(origen)] = distancia[grafo.ordinal(sala)] + 1
                    cola.append(origen)
        return distancia

    def _salida_cazador(self, enemigo):
        """Regla fija: la salida abierta cuyo destino queda más cerca (en saltos) de la sala del jugador; a igual
        distancia, la primera en el orden de `sala.salidas`. Si ninguna acerca, espera. Sin azar."""
        grafo = self.grafo_cripta
        distancia = self._distancias_al_jugador()
        actual = distancia[grafo.ordinal(enemigo.sala)]
        mejor = None
        mejor_distancia = actual
        for direccion, salida in self.salidas_abiertas(enemigo.sala):
            destino = self._destino(salida)
            if destino is None:
                continue
            d = distancia[grafo.ordinal(destino)]
            if d != -1 and actual != -1 and d < mejor_distancia:
                mejor = (direccion, salida, destino)
                mejor_distancia = d
        if mejor is None:
            self.decisiones_cazador.append((self.reloj, enemigo.id, "ESPERAR", None, None, 100))
            return None
        direccion, salida, destino = mejor
        self.decisiones_cazador.append(
            (self.reloj, enemigo.id, "MOVER", destino.id, direccion, self.costo_salida(salida)))
        return salida


def preparar_motor_linea(motor, espiar=True):
    """Convierte `motor` (ya armado, sin red) en `MotorLinea`: agrega la lista de resúmenes del espía y la de
    decisiones del cazador doble, que cuelgan del motor. Devuelve el mismo motor."""
    motor.__class__ = MotorLinea
    motor.espiar = espiar
    motor.resumenes = []
    motor.decisiones_cazador = []
    return motor


def agregar_enemigo(motor, id_enemigo, id_sala, comportamiento, velocidad=100):
    """Agrega al motor (que debe ser `MotorLinea`) un enemigo sin ficha, con ese `comportamiento`, y lo activa.
    Sirve para tener un «errante» (consume azar) o un «cazador» (doble) sin armar un paquete."""
    if not isinstance(motor, MotorLinea):
        raise TypeError("Use preparar_motor_linea(motor) antes de agregar enemigos")
    sala = motor.buscar_sala(motor.salas, id_sala)
    if sala is None:
        raise ValueError(f"La sala {id_sala!r} no existe")
    enemigo = Enemigo(id_enemigo, 8, 8, 3, 0, velocidad, comportamiento, sala=sala, tipo_id=None)
    enemigo.botin = []
    enemigo.regeneracion = 0
    motor.registrar_enemigo(enemigo)
    motor.activar_enemigo(enemigo)
    return enemigo


def agregar_cazador(motor, id_enemigo, id_sala, velocidad=100):
    """Doble del cazador de A (T010): un `Enemigo` con `comportamiento == "cazador"` en la sala `id_sala`, activo."""
    return agregar_enemigo(motor, id_enemigo, id_sala, "cazador", velocidad)


# ───────────────────────── Partida completa en carpeta propia ─────────────────────────

class PartidaLinea:
    """Motor y controlador de una partida de prueba, con su carpeta temporal propia.

    `ruta_bitacora` es la ruta que se pasa como `--bitacora` (nunca el `partida.log` de `main.py`) y `ruta_datos` la
    carpeta de datos locales de la caché; `nuevo_gestor()` arma un gestor nuevo sobre **esa misma carpeta** (equivale a
    un proceso nuevo). Llamar a `cerrar()` (o `addCleanup(partida.cerrar)`) cierra la bitácora y borra la carpeta."""

    def __init__(self, carpeta, paquete, ruta_datos, ruta_bitacora, gestor, controlador, vista):
        self.carpeta = carpeta
        self.paquete = paquete
        self.ruta_datos = ruta_datos
        self.ruta_bitacora = ruta_bitacora
        self.gestor = gestor
        self.controlador = controlador
        self.vista = vista

    @property
    def motor(self):
        return self.controlador.motor

    def nuevo_gestor(self, iniciado=True):
        """Gestor nuevo sobre la misma carpeta de datos locales (sin red: la fuente es el paquete offline). Con
        `iniciado=True` (por omisión) ya llamó a `iniciar_cripta`, como el gestor histórico que sirve a los clones;
        con `iniciado=False` queda como el de un proceso recién arrancado, listo para `cargar`."""
        gestor = GestorDatos(FuenteDatosOffline(self.paquete), ruta_base=self.ruta_datos, cache_size=25)
        if iniciado:
            gestor.iniciar_cripta(CRIPTA_NIEBLA)
        return gestor

    def cerrar(self):
        try:
            if self.controlador.bitacora is not None:
                self.controlador.bitacora.cerrar()
        except (ValueError, OSError):
            pass
        self.carpeta.cleanup()


def partida_linea(salas=None, contenido=None, semilla=7, jugador=None, forzar=False, espiar=False, **opciones):
    """Crea el paquete offline y empieza una partida con `ControladorPartida.nueva_partida`, sin red.

    Todo va a una carpeta temporal propia: el paquete, los datos locales (`ruta_datos`) y la bitácora
    (`ruta_bitacora`). Por defecto usa SALAS_LINEA (resoluble, con una rata y una trampa) y un jugador resistente.

    La cripta debe ser **resoluble**; si una prueba necesita otra, pasa `forzar=True` con un comentario que cite el
    FR-021 de la spec 002 (una partida nueva solo inicia si la cripta es resoluble). `espiar=True` deja el motor como
    `MotorLinea` con espía. `opciones` va tal cual a `crear_paquete_niebla`."""
    carpeta = tempfile.TemporaryDirectory()
    base = carpeta.name
    paquete = os.path.join(base, NOMBRE_PAQUETE)
    ruta_datos = os.path.join(base, NOMBRE_DATOS)
    ruta_bitacora = os.path.join(base, NOMBRE_BITACORA)
    crear_paquete_niebla(paquete, SALAS_LINEA if salas is None else salas,
                         CONTENIDO_LINEA if contenido is None else contenido,
                         jugador=JUGADOR_RESISTENTE if jugador is None else jugador, **opciones)

    gestor = GestorDatos(FuenteDatosOffline(paquete), ruta_base=ruta_datos, cache_size=25)
    vista = VistaFalsa()
    controlador = ControladorPartida(gestor, vista, ruta_bitacora)
    controlador.nueva_partida(CRIPTA_NIEBLA, semilla, forzar=forzar)
    partida = PartidaLinea(carpeta, paquete, ruta_datos, ruta_bitacora, gestor, controlador, vista)
    if espiar:
        preparar_motor_linea(controlador.motor)
    return partida
