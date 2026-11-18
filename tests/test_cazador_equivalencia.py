# Equivalencia del cazador con la referencia desde cero, capacidad 003, historia US4 (T057; FR-016, FR-028, SC-003).
#
# Partidas sintéticas de tests/utiles_terreno.py jugadas de verdad con motor.ejecutar_accion y la estrategia
# "compartida" (campo de distancias por ciclo). motor.decidir_cazador se envuelve en la instancia: en CADA turno de cada
# cazador, antes de llamar al original, la prueba calcula la referencia desde cero (firma_desde_cero de
# tests/test_cazador.py: primer_paso sin espacio, sin compartir nada con el motor), y compara acción, dirección, sala
# de destino y costo. Después del turno comprueba que el cazador quedó en la sala de destino de la decisión.
#
# El jugador actúa con un random.Random propio de la prueba (nunca motor.azar); entre sus acciones la prueba cierra y
# abre puertas con motor._escribir_cerrada, programa cierres automáticos (CERRAR_PUERTA) que ocurren dentro de los
# ciclos y activa cazadores dormidos con motor.activar_enemigo. Al jugador se le da vida de sobra para que la partida
# no termine por los ataques.
#
# Pendiente: T058 (partida guardada, cargada y continuada; retrocedida con un pergamino y reproducida con --replay) y
# T059 (reconstrucción de un estado pasado de la línea de tiempo) se agregan en este archivo después. Dependen de la
# capacidad 004 (formato de guardado y línea de tiempo) y del registro de decisiones T076; todavía no se escriben.

import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import random
import unittest

from tests.test_cazador import cazadores_de, firma, firma_desde_cero
from tests.utiles_terreno import armar_motor, cripta_terreno

# (nombre, semilla de la cripta, salas, costo_ida, costo_vuelta, variacion, rangos de los cazadores, acciones)
# Costos distintos por sentido: costo_ida ≠ costo_vuelta y variacion > 0 (los dos sentidos nunca cuestan lo mismo).
ESCENARIOS = [
    ("8 salas", 11, 8, 120, 80, 40, [0, 90, 250, 10 ** 6], 160),
    ("25 salas", 23, 25, 100, 140, 60, [0, 60, 150, 400, 900, 10 ** 6], 160),
    ("60 salas", 37, 60, 90, 130, 50, [0, 0, 80, 200, 350, 600, 1200, 3000, 10 ** 6, 10 ** 9], 160),
    # Costos iguales en los dos sentidos y sin variación: muchos empates de ruta y rangos que caen justo en la distancia
    # (múltiplos de 100), para ejercitar los desempates (id de la vecina, N-S-E-O) y el borde «distancia = rango».
    ("25 salas, costos uniformes", 29, 25, 100, 100, 0, [100, 200, 200, 300, 400, 500, 700], 160),
    ("60 salas, costos uniformes", 41, 60, 100, 100, 0, [100, 100, 200, 300, 300, 400, 600, 800, 1000], 160),
]
SEMILLAS_PARTIDA = (101, 202)

VIDA_DE_SOBRA = 10 ** 9


class Partida:
    """Una partida con la estrategia compartida y la comparación turno a turno colgada de motor.decidir_cazador."""

    def __init__(self, prueba, nombre, cripta, semilla, rangos):
        self.prueba = prueba
        self.nombre = nombre
        self.azar = random.Random(semilla)            # azar de la prueba, nunca motor.azar
        self.turnos = 0
        self.acciones = {"MOVER": 0, "ESPERAR": 0, "ATACAR": 0}
        self.ataques_sin_decidir = 0                  # ATACAR resueltos por accion_enemigo, sin decidir_cazador
        self.cierres = 0
        self.aperturas = 0
        self.cambios_de_sala = 0
        self.pendientes = []                          # (cazador, id de la sala donde debe quedar)

        salas_cazadores = [self.azar.randrange(2, len(cripta.salas_json) + 1) for _ in rangos]
        self.motor = armar_motor(cripta, 1, list(zip(salas_cazadores, rangos)), semilla=semilla)
        motor = self.motor
        motor.jugador.vida_max = VIDA_DE_SOBRA
        motor.jugador.vida = VIDA_DE_SOBRA
        motor.estrategia_cazador = "compartida"
        self.cazadores = cazadores_de(motor)
        # Puertas que la prueba cierra y abre: todas menos las que piden llave (la de la sala de salida).
        self.puertas = [sala.salidas[d] for sala in motor.salas for d in sala.salidas
                        if getattr(sala.salidas[d], "llave", None) is None]
        self._envolver_decision()
        self._contar_puertas()

    # ── Envolturas en la instancia ──

    def _envolver_decision(self):
        motor = self.motor
        original = motor.decidir_cazador

        def envoltura(cazador):
            self.verificar_posiciones()
            esperada = firma_desde_cero(motor, cazador)          # ANTES de la decisión del motor
            decision = original(cazador)                         # estrategia compartida
            obtenida = firma(motor, cazador, decision)
            if obtenida != esperada:
                self.prueba.fail(
                    f"[{self.nombre}] ciclo {motor.ciclo}, reloj {motor.reloj}: el cazador {cazador.id} en la sala "
                    f"{cazador.sala.id} (rango {cazador.rango}, jugador en {motor.jugador.sala.id}) decidió "
                    f"{obtenida} con la estrategia compartida y la referencia desde cero da {esperada}")
            self.turnos += 1
            self.acciones[decision.accion] += 1
            destino = obtenida[2] if decision.accion == "MOVER" else cazador.sala.id
            self.pendientes.append((cazador, destino, motor.ciclo))
            return decision

        motor.decidir_cazador = envoltura

        # El motor no llama a decidir_cazador cuando el cazador comparte sala con el jugador: accion_enemigo devuelve
        # "ATACAR" para cualquier enemigo en esa sala antes de llegar a "CAZAR". Esos turnos también se comparan: la
        # referencia desde cero y la estrategia compartida (llamada directamente) deben dar ATACAR.
        original_accion = motor.accion_enemigo

        def accion(enemigo, jugador):
            resultado = original_accion(enemigo, jugador)
            if enemigo.comportamiento == "cazador" and resultado == "ATACAR":
                self.verificar_posiciones()
                esperada = firma_desde_cero(motor, enemigo)
                obtenida = firma(motor, enemigo, motor.decidir_cazador_compartida(enemigo))
                for nombre, valor in (("el motor", ("ATACAR", None, None, 100)), ("la compartida", obtenida)):
                    if valor != esperada:
                        self.prueba.fail(
                            f"[{self.nombre}] ciclo {motor.ciclo}, reloj {motor.reloj}: el cazador {enemigo.id} en "
                            f"la sala {enemigo.sala.id} (rango {enemigo.rango}): {nombre} da {valor} y la referencia "
                            f"desde cero da {esperada}")
                self.turnos += 1
                self.acciones["ATACAR"] += 1
                self.ataques_sin_decidir += 1
                self.pendientes.append((enemigo, enemigo.sala.id, motor.ciclo))
            return resultado

        motor.accion_enemigo = accion

    def _contar_puertas(self):
        motor = self.motor
        original = motor._escribir_cerrada

        def envoltura(salida, cerrada, *args, **kwargs):
            if salida.cerrada != cerrada:
                if cerrada:
                    self.cierres += 1
                else:
                    self.aperturas += 1
            return original(salida, cerrada, *args, **kwargs)

        motor._escribir_cerrada = envoltura

    def verificar_posiciones(self):
        """Cada cazador que decidió quedó en la sala de destino de su decisión (la suya si no se movió)."""
        for cazador, destino, ciclo in self.pendientes:
            self.prueba.assertEqual(
                cazador.sala.id, destino,
                f"[{self.nombre}] el cazador {cazador.id} decidió en el ciclo {ciclo} ir a {destino} y está en "
                f"{cazador.sala.id}")
        self.pendientes = []

    # ── Lo que hace la prueba entre acciones del jugador ──

    def tocar_puertas(self):
        azar = self.azar
        motor = self.motor
        for _ in range(azar.randint(0, 3)):
            salida = azar.choice(self.puertas)
            motor._escribir_cerrada(salida, not salida.cerrada)
        if azar.random() < 0.5:
            abiertas = [s for s in self.puertas if not s.cerrada]
            if abiertas:
                motor.programar_evento(motor.reloj + azar.randint(1, 250), "CERRAR_PUERTA", azar.choice(abiertas))
        if azar.random() < 0.06:
            dormidos = [c for c in self.cazadores if not c.activo and c.esta_vivo()]
            if dormidos:
                motor.activar_enemigo(azar.choice(dormidos))

    def actuar_jugador(self):
        azar = self.azar
        motor = self.motor
        jugador = motor.jugador
        sala = jugador.sala
        abiertas = [d for d in sala.salidas if not sala.salidas[d].cerrada]
        cerradas = [d for d in sala.salidas
                    if sala.salidas[d].cerrada and getattr(sala.salidas[d], "llave", None) is None]
        tirada = azar.random()
        if tirada < 0.6 and abiertas:
            accion = ("mover", azar.choice(abiertas))
        elif tirada < 0.8 and cerradas:
            accion = ("abrir", azar.choice(cerradas))
        else:
            accion = ("esperar", None)
        self.prueba.assertTrue(motor.ejecutar_accion(*accion), f"[{self.nombre}] el motor rechazó {accion}")
        if jugador.sala is not sala:
            self.cambios_de_sala += 1
        jugador.vida = VIDA_DE_SOBRA

    def jugar(self, acciones):
        for _ in range(acciones):
            self.tocar_puertas()
            self.actuar_jugador()
            self.verificar_posiciones()
        motor = self.motor
        self.prueba.assertTrue(motor.jugador.esta_vivo())
        self.prueba.assertFalse(motor.victoria)


class TestEquivalenciaDesdeCero(unittest.TestCase):
    def test_fr016_fr028_sc003_compartida_igual_a_desde_cero_en_cada_turno(self):
        """T057 (FR-016, FR-028, SC-003): en partidas sintéticas de 8, 25 y 60 salas con costos distintos por
        sentido, varios cazadores de rangos 0 a 10**9, puertas que se cierran y abren durante el ciclo, cazadores
        activados con motor.activar_enemigo y el jugador moviéndose, la decisión de la estrategia compartida coincide
        con la referencia desde cero en el 100 % de los turnos (acción, dirección, sala de destino y costo), en al
        menos 1 000 turnos, con cobertura mínima de MOVER, ESPERAR, ATACAR, cierres, aperturas y cambios de sala."""
        total = {"turnos": 0, "MOVER": 0, "ESPERAR": 0, "ATACAR": 0, "cierres": 0, "aperturas": 0,
                 "cambios_de_sala": 0}
        por_escenario = []
        for nombre, semilla_cripta, salas, ida, vuelta, variacion, rangos, acciones in ESCENARIOS:
            cripta = cripta_terreno(semilla_cripta, salas, costo_ida=ida, costo_vuelta=vuelta, variacion=variacion)
            for semilla in SEMILLAS_PARTIDA:
                etiqueta = f"{nombre}, semilla {semilla}"
                with self.subTest(escenario=etiqueta):
                    partida = Partida(self, etiqueta, cripta, semilla, rangos)
                    partida.jugar(acciones)
                    por_escenario.append((etiqueta, partida.turnos, dict(partida.acciones),
                                          partida.ataques_sin_decidir, partida.cierres, partida.aperturas,
                                          partida.cambios_de_sala))
                    total["turnos"] += partida.turnos
                    for accion in partida.acciones:
                        total[accion] += partida.acciones[accion]
                    total["cierres"] += partida.cierres
                    total["aperturas"] += partida.aperturas
                    total["cambios_de_sala"] += partida.cambios_de_sala

        if os.environ.get("CAZADOR_EQUIVALENCIA_DETALLE"):
            for fila in por_escenario:
                print(fila)
            print(total)

        self.assertGreaterEqual(total["turnos"], 1000, "SC-003 pide al menos 1 000 turnos de cazadores comparados")
        self.assertGreaterEqual(total["MOVER"], 100)
        self.assertGreaterEqual(total["ESPERAR"], 100)
        self.assertGreaterEqual(total["ATACAR"], 30)
        self.assertGreaterEqual(total["cierres"], 50)
        self.assertGreaterEqual(total["aperturas"], 50)
        self.assertGreaterEqual(total["cambios_de_sala"], 100)


# ───────────────────────── T058 y T059: guardado, retroceso, --replay y línea de tiempo (capacidad 004) ─────────────────────────
#
# Dos criptas de ESCENARIOS (una con un rango pequeño frente a costos de 40 a 160, otra con costos uniformes y empates de
# ruta) se convierten en un paquete offline y se juegan con SesionLinea de tests/utiles_linea.py: partida real de
# ControladorPartida.nueva_partida, LineaTiempo propia, guardado CRPT 3 con guardar_motor y carga con cargar_partida y un
# gestor nuevo. Los cazadores son enemigos reales del paquete (una ficha «cazador» por rango); el registro de decisiones
# (T076) se enciende en cada motor antes de su primera acción.
#
# Una partida de referencia, jugada de corrido sin guardar ni retroceder, fija el guion (acciones del jugador, con un
# random.Random propio; nunca entra a la sala de salida) y las entradas del registro que produce cada acción. Las demás
# partidas juegan ese mismo guion y comparan, acción por acción, las entradas que produjo cada una.
#
# Lo que se compara de cada entrada es la decisión: (reloj, id del cazador, acción, sala de destino, dirección, costo
# base), sin el ciclo. El ciclo es un contador del motor que no se guarda en el CRPT 3 (vuelve a 0 al cargar) ni se
# revierte con el historial (solo crece): no es parte de la decisión.

from unittest import mock

import main
from Gestor import PreparadorPartida
from Modelo.DecisionCazador import DecisionCazador
from tests.utiles_linea import JUGADOR_RESISTENTE, SesionLinea, escribir_bitacora
from tests.utiles_niebla import CATALOGO_NIEBLA, LLAVE, PERGAMINO

ESCENARIOS_004 = ("8 salas", "25 salas, costos uniformes")
ACCIONES_004 = 40            # acciones del guion, además de recoger el pergamino
SEMILLA_004 = 5
PREFIJO_FICHA_004 = "ent_cazador_r"


def escenario(nombre):
    for fila in ESCENARIOS:
        if fila[0] == nombre:
            return fila
    raise KeyError(nombre)


def opciones_de_paquete(nombre):
    """Opciones de SesionLinea para la cripta del escenario `nombre`: sus salas (con la llave de la salida cambiada por
    la del catálogo de niebla), un cazador por rango y un pergamino de retroceso en la sala inicial. La mitad de los
    cazadores empieza en la sala inicial (activos desde el primer turno); los demás, en salas intermedias, se activan
    cuando el jugador entra."""
    _nombre, semilla_cripta, salas, ida, vuelta, variacion, rangos, _acciones = escenario(nombre)
    cripta = cripta_terreno(semilla_cripta, salas, costo_ida=ida, costo_vuelta=vuelta, variacion=variacion)
    detalles = cripta.detalles_json
    llave = detalles["llave_salida"]
    salas_json = []
    for sala in cripta.salas_json:
        salidas = {}
        for direccion in sala["salidas"]:
            datos = dict(sala["salidas"][direccion])
            if datos.get("llave") == llave:
                datos["llave"] = LLAVE
            salidas[direccion] = datos
        salas_json.append({"id": sala["id"], "nombre": sala["nombre"], "salidas": salidas})

    inicial, salida = detalles["sala_inicial"], detalles["sala_salida"]
    por_sala = {inicial: []}
    fichas = []
    for indice in range(len(rangos)):
        rango = rangos[indice]
        tipo = f"{PREFIJO_FICHA_004}{rango}"
        if all(ficha["id"] != tipo for ficha in fichas):
            fichas.append({"id": tipo, "clase": "enemigo", "nombre": "Cazador", "vida_max": 8, "ataque": 3,
                           "defensa": 0, "velocidad": 100, "comportamiento": "cazador", "rango": rango})
        sala = inicial if indice % 2 == 0 else 2 + (indice * 7) % (salas - 2)
        por_sala.setdefault(sala, []).append({"instancia": f"caz-{indice + 1}", "tipo": tipo})
    contenido = []
    for sala in por_sala:
        contenido.append({"sala": sala, "enemigos": por_sala[sala], "trampas": [],
                          "objetos": [PERGAMINO] if sala == inicial else []})
    return {
        "salas": salas_json, "contenido": contenido, "catalogo_extra": fichas, "jugador": JUGADOR_RESISTENTE,
        "sala_inicial": inicial, "sala_salida": salida, "llave_salida": LLAVE,
        "llaves": [{"id": LLAVE, "sala": ubicacion["sala"]} for ubicacion in cripta.llaves_json],
    }


def decision(entrada):
    """La decisión de una entrada del registro: todo menos el ciclo."""
    return entrada[1:]


def decisiones(entradas):
    return [decision(entrada) for entrada in entradas]


def aplanar(por_accion):
    return [entrada for entradas in por_accion for entrada in entradas]


class PartidaGuardable:
    """SesionLinea sobre el paquete de un escenario, con el registro de decisiones encendido y las entradas que produjo
    cada acción vigente (`por_accion[i]` es la acción i + 1 de la línea; la primera es recoger el pergamino)."""

    def __init__(self, prueba, nombre):
        self.prueba = prueba
        self.sesion = SesionLinea(k=3, semilla=SEMILLA_004, huellas=False, **opciones_de_paquete(nombre))
        prueba.addCleanup(self.sesion.cerrar)
        self.sesion.motor.activar_registro_decisiones()
        self.por_accion = []
        motor = self.sesion.motor
        pergamino = motor.obtener_objetos_suelo(motor.jugador.sala)[0]
        self.recoger = ("recoger", pergamino.instancia_id)
        self.hacer([self.recoger])

    @property
    def motor(self):
        return self.sesion.motor

    def hacer(self, acciones):
        for accion in acciones:
            motor = self.motor
            antes = len(motor.registro_decisiones)
            self.prueba.assertEqual(self.sesion.hacer([accion]), 1, f"el motor rechazó {accion}")
            self.por_accion.append(motor.registro_decisiones[antes:])

    def guardar_y_cargar(self):
        """Guarda, carga con un gestor nuevo y enciende el registro en el motor cargado (no viaja en el CRPT 3)."""
        self.sesion.guardar_y_cargar()
        self.prueba.assertIsNone(self.motor.registro_decisiones, "el registro no forma parte del guardado")
        self.motor.activar_registro_decisiones()

    def retroceder(self):
        """Retrocede una acción con el pergamino. Devuelve las entradas del registro tal como quedaron."""
        motor = self.motor
        acciones = self.sesion.linea.acciones
        self.prueba.assertTrue(self.sesion.retroceder(), "el motor rechazó retroceder")
        self.prueba.assertEqual(self.sesion.linea.acciones, acciones - 1)
        del self.por_accion[self.sesion.linea.acciones:]
        return list(motor.registro_decisiones)


def generar_guion(motor, cantidad, semilla):
    """Acciones del jugador para la partida de referencia: mover por una salida abierta que no lleve a la sala de salida
    (65 %) o esperar. random.Random propio, nunca motor.azar. Se ejecutan en `motor` a medida que se eligen."""
    azar = random.Random(semilla)
    guion = []
    for _ in range(cantidad):
        sala = motor.jugador.sala
        abiertas = [d for d in sorted(sala.salidas) if not sala.salidas[d].cerrada
                    and sala.salidas[d].sala_destino != motor.sala_salida]
        if abiertas and azar.random() < 0.65:
            guion.append(("mover", azar.choice(abiertas)))
        else:
            guion.append(("esperar", ""))
        yield guion[-1]


class BaseGuardadoYLinea(unittest.TestCase):
    """Una partida de referencia por escenario: el guion y las entradas de cada acción."""

    def referencia(self, nombre):
        partida = PartidaGuardable(self, nombre)
        guion = []
        for accion in generar_guion(partida.motor, ACCIONES_004, SEMILLA_004):
            partida.hacer([accion])
            guion.append(accion)
        self.assertTrue(partida.motor.jugador.esta_vivo())
        self.assertFalse(partida.motor.victoria)
        # cobertura: la prueba no pasa vacía
        acciones = [entrada[3] for entrada in aplanar(partida.por_accion)]
        self.assertGreater(acciones.count(DecisionCazador.MOVER), 0, f"[{nombre}] ningún MOVER en la referencia")
        self.assertGreater(acciones.count(DecisionCazador.ATACAR), 0, f"[{nombre}] ningún ATACAR en la referencia")
        return partida, guion

    def comparar_por_accion(self, nombre, obtenidas, esperadas, desde=0):
        """Cada acción produjo las mismas decisiones. `desde` es el índice de la primera acción de `obtenidas`."""
        self.assertEqual(len(obtenidas), len(esperadas) - desde)
        for indice in range(len(obtenidas)):
            self.assertEqual(decisiones(obtenidas[indice]), decisiones(esperadas[desde + indice]),
                             f"[{nombre}] acción {desde + indice + 1} de la línea")

    def contar(self, entradas, cuenta):
        for entrada in entradas:
            cuenta[entrada[3]] = cuenta.get(entrada[3], 0) + 1

    def exigir_cobertura(self, cuenta):
        self.assertGreater(cuenta.get(DecisionCazador.MOVER, 0), 0, "ningún MOVER comparado")
        self.assertGreater(cuenta.get(DecisionCazador.ATACAR, 0), 0, "ningún ATACAR comparado")


class TestGuardadoRetrocesoReplay(BaseGuardadoYLinea):

    def test_fr024_fr025_sc005_guardada_cargada_y_continuada_decide_igual(self):
        """T058 (a) (FR-024, FR-025, SC-005): la partida jugada hasta la mitad del guion, guardada (CRPT 3), cargada con
        un gestor nuevo y continuada con las mismas acciones produce, acción por acción, las mismas decisiones de los
        cazadores que la partida de referencia sin guardar (100 % de los turnos)."""
        cuenta = {}
        for nombre in ESCENARIOS_004:
            with self.subTest(escenario=nombre):
                referencia, guion = self.referencia(nombre)
                mitad = len(guion) // 2
                partida = PartidaGuardable(self, nombre)
                partida.hacer(guion[:mitad])
                partida.guardar_y_cargar()
                partida.hacer(guion[mitad:])
                self.assertEqual(partida.sesion.cargas, 1)
                self.comparar_por_accion(nombre, partida.por_accion, referencia.por_accion)
                self.assertGreater(len(aplanar(partida.por_accion[mitad + 1:])), 0,
                                   f"[{nombre}] ninguna decisión después de cargar")
                self.contar(aplanar(partida.por_accion), cuenta)
        self.exigir_cobertura(cuenta)

    def test_fr024_fr025_sc005_retrocedida_con_pergamino_y_vuelta_a_jugar_decide_igual(self):
        """T058 (b) (FR-024, FR-025, SC-005): la partida retrocedida una acción con el pergamino deja el registro igual
        al de la referencia hasta la acción anterior, y vuelta a jugar con las mismas acciones produce, acción por
        acción, las mismas decisiones."""
        cuenta = {}
        for nombre in ESCENARIOS_004:
            with self.subTest(escenario=nombre):
                referencia, guion = self.referencia(nombre)
                corte = len(guion) * 3 // 4
                partida = PartidaGuardable(self, nombre)
                partida.hacer(guion[:corte])
                tras_retroceder = partida.retroceder()
                # quedan recoger + guion[:corte - 1]: el registro es el de la referencia hasta ahí, entrada por entrada
                self.assertEqual(tras_retroceder, aplanar(referencia.por_accion[:corte]))
                self.assertGreater(len(aplanar(referencia.por_accion[corte:corte + 1])), 0,
                                   f"[{nombre}] la acción revertida no anotó decisiones: el retroceso no se prueba")
                partida.hacer(guion[corte - 1:])
                self.comparar_por_accion(nombre, partida.por_accion, referencia.por_accion)
                self.assertEqual(decisiones(partida.motor.registro_decisiones),
                                 decisiones(aplanar(referencia.por_accion)))
                self.contar(aplanar(partida.por_accion), cuenta)
        self.exigir_cobertura(cuenta)

    def test_fr024_fr025_sc005_replay_decide_igual(self):
        """T058 (c) (FR-024, FR-025, SC-005): la bitácora de la partida guardada y cargada (con @cargar) y la de la
        partida retrocedida, reproducidas con main.ejecutar_replay y un gestor nuevo, dan las mismas decisiones que la
        referencia. El registro se enciende en cada motor que crea el replay (el de la partida nueva y el de cada
        recarga), envolviendo preparar_partida y cargar_partida tal como los llama main."""
        cuenta = {}
        for nombre in ESCENARIOS_004:
            referencia, guion = self.referencia(nombre)
            esperadas = decisiones(aplanar(referencia.por_accion))
            mitad, corte = len(guion) // 2, len(guion) * 3 // 4

            guardada = PartidaGuardable(self, nombre)
            guardada.hacer(guion[:mitad])
            guardada.guardar_y_cargar()
            guardada.hacer(guion[mitad:])

            retrocedida = PartidaGuardable(self, nombre)
            retrocedida.hacer(guion[:corte])
            retrocedida.retroceder()
            retrocedida.hacer(guion[corte - 1:])

            for variante, partida, motores_esperados in (("guardada y cargada", guardada, 2),
                                                          ("retrocedida", retrocedida, 1)):
                with self.subTest(escenario=nombre, variante=variante):
                    sesion = partida.sesion
                    ruta = escribir_bitacora(sesion, os.path.join(sesion.partida.carpeta.name, "replay.log"))
                    motores = []

                    def encender(original):
                        def envoltura(*args, **kwargs):
                            motor = original(*args, **kwargs)
                            motor.activar_registro_decisiones()
                            motores.append(motor)
                            return motor
                        return envoltura

                    with mock.patch.object(main, "preparar_partida", encender(PreparadorPartida.preparar_partida)), \
                            mock.patch.object(main, "cargar_partida", encender(PreparadorPartida.cargar_partida)):
                        final = main.ejecutar_replay(ruta, sesion.partida.nuevo_gestor(iniciado=False))

                    self.assertEqual(len(motores), motores_esperados)
                    self.assertIs(final, motores[-1])
                    obtenidas = aplanar(motor.registro_decisiones for motor in motores)
                    self.assertEqual(decisiones(obtenidas), esperadas)
                    self.contar(obtenidas, cuenta)
        self.exigir_cobertura(cuenta)


class TestReconstruccionLinea(BaseGuardadoYLinea):

    def test_fr025_clon_antes_de_k_decide_igual_que_la_partida_desde_k(self):
        """T059 (FR-025): para cada acción k de la línea, el estado reconstruido con linea.clon_antes_de(k, motor),
        con el registro encendido y avanzado con las acciones vigentes k, k + 1, ..., produce, acción por acción, las
        mismas decisiones de los cazadores que la partida jugada desde k. La línea es la de una partida guardada y
        cargada a la mitad y retrocedida una vez después de cargar: los clones salen de las dos épocas y de la historia
        vigente tras el retroceso."""
        cuenta = {}
        for nombre in ESCENARIOS_004:
            with self.subTest(escenario=nombre):
                referencia, guion = self.referencia(nombre)
                mitad, corte = len(guion) // 2, len(guion) * 3 // 4
                partida = PartidaGuardable(self, nombre)
                partida.hacer(guion[:mitad])
                partida.guardar_y_cargar()
                partida.hacer(guion[mitad:corte])
                partida.retroceder()
                partida.hacer(guion[corte - 1:])
                linea = partida.sesion.linea
                vigentes = [partida.recoger] + guion
                self.assertEqual(linea.acciones, len(vigentes))

                for k in range(1, linea.acciones + 1):
                    clon = linea.clon_antes_de(k, partida.motor)
                    clon.activar_registro_decisiones()
                    obtenidas = []
                    for accion in vigentes[k - 1:]:
                        antes = len(clon.registro_decisiones)
                        self.assertTrue(clon.ejecutar_accion(*accion), f"[{nombre}] el clon {k} rechazó {accion}")
                        obtenidas.append(clon.registro_decisiones[antes:])
                    self.comparar_por_accion(f"{nombre}, clon antes de {k}", obtenidas, referencia.por_accion,
                                             desde=k - 1)
                    self.contar(aplanar(obtenidas), cuenta)
        self.exigir_cobertura(cuenta)


if __name__ == "__main__":
    unittest.main()
