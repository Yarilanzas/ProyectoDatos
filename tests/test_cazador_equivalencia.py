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


if __name__ == "__main__":
    unittest.main()
