# Utilidades de prueba y bench de la capacidad de terreno y cazador (spec 003, T003).
# Este archivo no lleva prefijo test: `unittest discover` no lo ejecuta.
# Adaptador sobre `generar_cripta` de tests/generador_criptas.py (Persona B): no lo modifica.
# Sin red, sin datos de criptas reales (Constitución IV) y sin tocar el `random` global.
# Atiende: FR-028, FR-033 (enunciado §6.3).
#
# Interfaz
# --------
# cripta_terreno(semilla, salas, costo_ida=100, costo_vuelta=100, variacion=None) -> CriptaSintetica
# armar_motor(cripta, sala_jugador, cazadores, semilla=1) -> MotorSimulacion
# mapa_a_mano(salas, sala_jugador, cazadores=(), sala_salida=None, llave_salida=None, semilla=1) -> MotorSimulacion
#
# `cazadores` es una lista de pares (sala, rango). Cada cazador se construye con motor.crear_enemigo a partir de una
# FichaEnemigo leída con FichaEnemigo.desde_json (comportamiento "cazador" y su rango). Los costos llegan a las salidas
# por Salida.desde_json. Ningún costo ni rango se asigna a mano.

import os
import random
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from DTOS.FichaCatalogo import FichaEnemigo
from DTOS.SalaEsqueleto import SalaEsqueleto
from Modelo.Jugador import Jugador
from Modelo.MotorSimulacion import MotorSimulacion
from tests.generador_criptas import JUGADOR, generar_cripta

ID_JUGADOR = "jugador"
PREFIJO_FICHA = "ent_cazador_r"
PREFIJO_CAZADOR = "caz-"
CAZADOR = {"clase": "enemigo", "nombre": "Cazador", "vida_max": 8, "ataque": 3, "defensa": 0,
           "velocidad": 100, "comportamiento": "cazador"}


class GestorTerreno:
    """Gestor mínimo sin red: solo lo que el motor pide en estas pruebas (fichas por id).

    Las fichas están en una lista y se buscan recorriéndola (O(fichas)); hay una por rango distinto.
    """

    def __init__(self):
        self.fichas = []
        self.estado_juego = None

    def conectar_estado_juego(self, estado_juego):
        self.estado_juego = estado_juego

    def obtener_ficha(self, id_ficha):
        for ficha in self.fichas:
            if ficha.id == id_ficha:
                return ficha
        return None

    def ficha_cazador(self, rango):
        """Devuelve el id de la ficha de cazador con ese rango; la crea con FichaEnemigo.desde_json si no existe."""
        id_ficha = f"{PREFIJO_FICHA}{rango}"
        if self.obtener_ficha(id_ficha) is None:
            datos = {"id": id_ficha, "rango": rango}
            datos.update(CAZADOR)
            self.fichas.append(FichaEnemigo.desde_json(datos))
        return id_ficha


# ───────────────────────── Criptas sintéticas ─────────────────────────

def _salida_de_vuelta(salas_json, origen, destino):
    # Salida destino→origen. Los ids de generar_cripta son 1..n en orden, así que la sala `destino` es salas_json[destino-1].
    salidas = salas_json[destino - 1]["salidas"]
    for direccion in salidas:
        if salidas[direccion]["sala"] == origen:
            return salidas[direccion]
    return None


def _variar_costos(salas_json, semilla, costo_ida, costo_vuelta, variacion):
    # Recorre cada arista una vez (desde la sala de id menor, en el orden N, S, E, O de salas_json) y sortea los dos
    # sentidos con una instancia local: el resultado solo depende de la semilla y de los parámetros.
    azar = random.Random(semilla)
    for sala in salas_json:
        origen = sala["id"]
        salidas = sala["salidas"]
        for direccion in salidas:
            ida = salidas[direccion]
            destino = ida["sala"]
            if destino < origen:
                continue
            vuelta = _salida_de_vuelta(salas_json, origen, destino)
            costo_a = max(1, costo_ida + azar.randint(-variacion, variacion))
            costo_b = max(1, costo_vuelta + azar.randint(-variacion, variacion))
            if variacion > 0 and costo_b == costo_a:
                costo_b += 1  # sentidos con costo propio (puertas dirigidas)
            ida["costo"] = costo_a
            if vuelta is not None:
                vuelta["costo"] = costo_b


def cripta_terreno(semilla, salas, costo_ida=100, costo_vuelta=100, variacion=None):
    """Cripta sintética casi abierta (una sola llave: solo la puerta de la sala de salida está cerrada).

    Sin `variacion`, `costo_ida` vale para cada salida hacia el id mayor y `costo_vuelta` para la otra (generar_cripta).
    Con `variacion` (entero ≥ 0), cada salida recibe base ± variacion, sorteado con random.Random(semilla), mínimo 1;
    con variacion ≥ 1, los dos sentidos de una puerta nunca cuestan lo mismo. Determinista por semilla.
    """
    for nombre, valor in (("costo_ida", costo_ida), ("costo_vuelta", costo_vuelta)):
        if not isinstance(valor, int) or isinstance(valor, bool) or valor < 1:
            raise ValueError(f"{nombre} debe ser un entero ≥ 1")
    if variacion is not None and (not isinstance(variacion, int) or isinstance(variacion, bool) or variacion < 0):
        raise ValueError("variacion debe ser None o un entero ≥ 0")

    cripta = generar_cripta(semilla, salas, llaves=1, costo_ida=costo_ida, costo_vuelta=costo_vuelta,
                            id_cripta=f"terreno-{semilla}-{salas}")
    if variacion is not None:
        _variar_costos(cripta.salas_json, semilla, costo_ida, costo_vuelta, variacion)
    return cripta


# ───────────────────────── Motor sin red ─────────────────────────

def _buscar(salas, id_sala):
    for sala in salas:
        if sala.id == id_sala:
            return sala
    raise ValueError(f"La sala {id_sala!r} no existe")


def _motor(esqueleto, sala_jugador, cazadores, sala_salida, llave_salida, semilla):
    # Mismo camino que Gestor/PreparadorPartida._crear_motor: el esqueleto (list[SalaEsqueleto]) son las salas del
    # motor, tal cual. Sin cripta_id, preparar_sala no pide contenido: todas las salas quedan como cargadas y vacías.
    gestor = GestorTerreno()
    motor = MotorSimulacion(semilla=semilla, gestor_datos=gestor)

    jugador = Jugador(ID_JUGADOR, vida=JUGADOR["vida_max"], vida_max=JUGADOR["vida_max"], ataque=JUGADOR["ataque"],
                      defensa=JUGADOR["defensa"], velocidad=JUGADOR["velocidad"],
                      sala=_buscar(esqueleto, sala_jugador))

    enemigos = []
    ancho = max(3, len(str(len(cazadores))))
    for indice in range(len(cazadores)):
        sala, rango = cazadores[indice]
        tipo = gestor.ficha_cazador(rango)
        enemigos.append(motor.crear_enemigo(f"{PREFIJO_CAZADOR}{indice + 1:0{ancho}d}", tipo, None,
                                            _buscar(esqueleto, sala)))

    motor.iniciar_partida(jugador, esqueleto, enemigos, sala_salida=sala_salida, llave_salida=llave_salida)
    motor._salas_contenido_cargado = [sala.id for sala in esqueleto]
    return motor


def armar_motor(cripta, sala_jugador, cazadores, semilla=1):
    """Motor sin red sobre `cripta` (de cripta_terreno), con el jugador en `sala_jugador` y un cazador por cada
    (sala, rango) de `cazadores`. Queda en el primer punto de decisión del jugador (reloj 0)."""
    detalles = cripta.detalles
    return _motor(cripta.esqueleto(), sala_jugador, list(cazadores), detalles.sala_salida, detalles.llave_salida,
                  semilla)


def mapa_a_mano(salas, sala_jugador, cazadores=(), sala_salida=None, llave_salida=None, semilla=1):
    """Motor pequeño desde una descripción explícita, para los casos del Apéndice B.

    `salas` es una lista de (id, salidas) y cada salida es (dirección, destino, costo, cerrada); costo None deja la
    salida sin costo declarado (vale 100, FR-005). Cada salida es dirigida: la vuelta se declara en la otra sala.

        # 2 salidas con costo 500 frente a 4 con costo 400 (US2.2)
        mapa_a_mano([
            (1, [("E", 2, 250, False), ("S", 4, 100, False)]),
            (2, [("E", 3, 250, False)]),
            (3, []),
            (4, [("E", 5, 100, False)]),
            (5, [("E", 6, 100, False)]),
            (6, [("N", 3, 100, False)]),
        ], sala_jugador=3, cazadores=[(1, 400)])
    """
    esqueleto = []
    for id_sala, salidas in salas:
        datos = {}
        for direccion, destino, costo, cerrada in salidas:
            salida = {"sala": destino, "cerrada": cerrada}
            if costo is not None:
                salida["costo"] = costo
            datos[direccion] = salida
        esqueleto.append(SalaEsqueleto.desde_json({"id": id_sala, "nombre": f"Sala {id_sala}", "salidas": datos}))
    return _motor(esqueleto, sala_jugador, list(cazadores), sala_salida, llave_salida, semilla)
