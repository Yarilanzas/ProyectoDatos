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
# huella(motor) -> lineas del resumen histórico del estado actual, sin el título (lo que `historia` debe reproducir)
# partida_con_linea(...) -> PartidaConLinea                              partida con línea de tiempo y espía de resúmenes
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
from Gestor.GestorHistorico import GestorHistorico
from Modelo.Enemigo import Enemigo
from Modelo.Inventario import NodoInventario
from Modelo.LineaTiempo import LineaTiempo
from Modelo.MotorSimulacion import MotorSimulacion
from Modelo.ResumenHistorico import resumir
from tests.test_integracion import VistaFalsa
from Vista.TextoResumen import lineas_resumen
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

    def nuevo_gestor_historico(self):
        """El gestor sin red de los clones (T029): mismo disco que el gestor de la partida, sin compartir contadores ni
        caché, con las versiones y los detalles capturados ahora."""
        return GestorHistorico.desde_gestor(self.gestor, CRIPTA_NIEBLA)

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


# ───────────────────────── Partida con línea y espía de resúmenes (T018 a T022) ─────────────────────────

def huella(motor, reloj=None):
    """Las líneas del resumen histórico del estado de `motor` (sin el título, que depende de la referencia).
    Es lo que `consultar_instante`/`consultar_accion` deben reproducir del estado pasado."""
    return lineas_resumen(resumir(motor, motor.reloj if reloj is None else reloj, ("instante", 0)))[1:]


class MotorEspiaConsulta(MotorLinea):
    """Espía independiente de la reconstrucción: anota el resumen del estado vivo (a) tras cada evento ejecutado y
    (b) tras el efecto de cada acción del jugador, justo antes de que programe su siguiente decisión. Así `instantaneas`
    es la línea de tiempo real, en orden, como pares (reloj, huella). `decisiones` lo llena `jugar_con_linea` con el
    estado justo ANTES de cada decisión aceptada, como pares (reloj, huella)."""

    instantaneas = None
    decisiones = None
    orden = None  # (tiempo, tipo, id del actor o None) de cada evento, en el orden en que el motor lo resolvió

    def ejecutar_evento(self, evento):
        if self.orden is not None:
            self.orden.append((evento.tiempo, evento.tipo, getattr(evento.actor, "id", None)))
        super().ejecutar_evento(evento)
        if self.instantaneas is not None:
            self.instantaneas.append((self.reloj, huella(self)))

    def proxima_accion(self, actor, costo=100):
        if actor is self.jugador and self.instantaneas is not None:
            self.instantaneas.append((self.reloj, huella(self)))
        return super().proxima_accion(actor, costo)


class PartidaConLinea:
    """Partida de `partida_linea` con `MotorEspiaConsulta`, una `LineaTiempo` y un gestor histórico propio."""

    def __init__(self, partida, linea, generador):
        self.partida = partida
        self.linea = linea
        self.generador = generador

    @property
    def motor(self):
        return self.partida.motor

    def jugar(self, acciones=None, hasta_reloj=None, observador=None):
        """Juega con el generador hasta `acciones` aceptadas o hasta que el reloj llegue a `hasta_reloj`; cada acción
        aceptada se registra en la línea. Devuelve las aceptadas."""
        motor = self.motor
        jugadas = []
        while ((acciones is None or len(jugadas) < acciones)
               and (hasta_reloj is None or motor.reloj < hasta_reloj)
               and motor.jugador.esta_vivo() and not motor.victoria):
            nombre, argumento = self.generador.siguiente(motor)
            antes = (motor.reloj, huella(motor))
            if motor.ejecutar_accion(nombre, argumento):
                motor.decisiones.append(antes)
                self.linea.registrar_accion(motor, nombre, argumento)
                jugadas.append((nombre, argumento))
        return jugadas

    def hacer(self, acciones):
        """Ejecuta una lista explícita de (nombre, argumento) y registra en la línea las aceptadas. Devuelve cuántas se
        aceptaron."""
        motor = self.motor
        aceptadas = 0
        for nombre, argumento in acciones:
            antes = (motor.reloj, huella(motor))
            if motor.ejecutar_accion(nombre, argumento):
                motor.decisiones.append(antes)
                self.linea.registrar_accion(motor, nombre, argumento)
                aceptadas += 1
        return aceptadas

    def retroceder(self):
        """`retroceder` por el motor; si lo aceptó, `registrar_retroceso` y el espía descarta las decisiones revertidas.
        Devuelve si fue aceptado (como el observador: lo rechazado no se registra)."""
        motor = self.motor
        if not motor.ejecutar_accion("retroceder", ""):
            return False
        self.linea.registrar_retroceso(motor)
        del motor.decisiones[self.linea.acciones:]
        return True

    def cerrar(self):
        self.partida.cerrar()


def dar_pergaminos(motor, cantidad, desde=0):
    """Agrega `cantidad` pergaminos de retroceso al inventario del jugador (sin pasar por el suelo)."""
    for i in range(desde, desde + cantidad):
        motor.jugador.inventario.recoge(
            NodoInventario(f"pergamino-{i}", "itm_pergamino", "Pergamino de retroceso", 0, 10, "pergamino_retroceso"))


def partida_con_linea(k=10, semilla=3, efectos=True, pergaminos=0, **opciones):
    """`pergaminos`: cuántos pergaminos de retroceso tiene el jugador al empezar (antes de `linea.iniciar`).
    Partida (cripta resoluble, por ControladorPartida.nueva_partida) con un errante, el cazador doble, y si
    `efectos`: veneno, velocidad temporal y antorcha encendida con su evento de apagado, todo **antes** de
    `linea.iniciar`, así el punto de control de la acción 0 ya los trae."""
    partida = partida_linea(semilla=semilla, **opciones)
    motor = preparar_motor_linea(partida.motor, espiar=False)
    motor.__class__ = MotorEspiaConsulta
    motor.instantaneas = []
    motor.decisiones = []
    motor.orden = []
    agregar_enemigo(motor, "err-001", 4, "errante")
    agregar_cazador(motor, "caz-001", 6)
    if efectos:
        motor.aplicar_veneno(motor.jugador, 2)
        motor.aplicar_velocidad_temporal(motor.jugador, 10, 300)
        motor.jugador.antorcha_encendida = True
        motor.programar_evento(motor.reloj + 500, "APAGAR_ANTORCHA", motor.jugador)
    dar_pergaminos(motor, pergaminos)
    linea = LineaTiempo(k=k, gestor_historico=partida.nuevo_gestor_historico())
    linea.iniciar(motor)
    return PartidaConLinea(partida, linea, GeneradorAcciones(semilla))


# ───────────────────────── Cripta de coincidencia (T049; Historia 3) ─────────────────────────

class Coincidencia:
    """Resultado de `partida_coincidencia`: la partida con línea, el instante `t` donde coinciden tres eventos, el orden de
    resolución que observó el motor espía en `t` y el instante `t + 1` del evento posterior."""

    def __init__(self, pl, t, orden):
        self.pl = pl
        self.t = t
        self.orden = orden


T_COINCIDENCIA = 150
EVENTOS_EN_T = ("FIN_VELOCIDAD", "ACCION_ACTOR", "CERRAR_PUERTA")


def partida_coincidencia(k=3, semilla=3, acciones=4):
    """Partida (cripta resoluble, por ControladorPartida.nueva_partida) donde **exactamente en t = 150** coinciden:

    - el fin de un efecto de velocidad del jugador (`FIN_VELOCIDAD`),
    - la acción de una rata guardián que está en la sala del jugador y lo ataca (`ACCION_ACTOR`),
    - una puerta de la sala del jugador que se cierra sola (`CERRAR_PUERTA`),

    programados en ese orden (así los resuelve el motor, por su secuencia), y un evento en `t + 1`: se apaga la antorcha
    (`APAGAR_ANTORCHA`). t = 150 no es una decisión del jugador. Todo se programa antes de `linea.iniciar`, así el punto de
    control de la acción 0 ya lo trae. Luego el jugador espera `acciones` veces y se devuelve `Coincidencia` con el orden de
    resolución que anotó el motor espía en `t` (lista de (tiempo, tipo, actor))."""
    partida = partida_linea(semilla=semilla)
    motor = preparar_motor_linea(partida.motor, espiar=False)
    motor.__class__ = MotorEspiaConsulta
    motor.instantaneas = []
    motor.decisiones = []
    motor.orden = []
    jugador = motor.jugador
    t = T_COINCIDENCIA

    motor.aplicar_velocidad_temporal(jugador, 10, t)          # FIN_VELOCIDAD en t
    rata = agregar_enemigo(motor, "rata-t", jugador.sala.id, "guardian")
    rata.evento_actual.cancelar()                              # su acción llegaba en 100: se mueve a t
    rata.tiempo_siguiente = t
    rata.evento_actual = motor.programar_evento(t, "ACCION_ACTOR", rata)
    puerta = jugador.sala.salidas["E"]
    motor.programar_evento(t, "CERRAR_PUERTA", puerta)         # CERRAR_PUERTA en t
    jugador.antorcha_encendida = True
    motor.programar_evento(t + 1, "APAGAR_ANTORCHA", jugador)  # el evento de t + 1

    linea = LineaTiempo(k=k, gestor_historico=partida.nuevo_gestor_historico())
    linea.iniciar(motor)
    pl = PartidaConLinea(partida, linea, GeneradorAcciones(semilla))
    pl.hacer([("esperar", "")] * acciones)
    orden = [evento for evento in motor.orden if evento[0] == t]
    return Coincidencia(pl, t, orden)
