# Pruebas de la historia US1 de la capacidad 003: el terreno determina cuánto tarda moverse (T019 a T026).
# FR-002 a FR-007, FR-026; escenarios 1 a 7 de la US1 y dos casos «Terreno y cazador» del Apéndice B.
# Regla (FR-005, research R7): el intervalo de toda acción es max(1, costo_base × 100 // velocidad); para moverse,
# costo_base es motor.costo_salida(salida). Las demás acciones conservan su costo de la Parte I.
#
# Los motores se arman con tests/utiles_terreno.mapa_a_mano: sin red, salas cargadas y vacías, jugador de velocidad
# 100 en su primer punto de decisión (reloj 0). Los costos llegan a las salidas por Salida.desde_json. Los enemigos
# que no son cazadores se agregan con fichas FichaEnemigo.desde_json en el GestorTerreno del motor y
# motor.crear_enemigo, igual que los cazadores de utiles_terreno.
#
# Para medir solo el turno de un enemigo, las pruebas lo activan con motor.activar_enemigo (primera acción con costo
# 100, FR-034) y ejecutan los eventos de la agenda con motor.ejecu_sig_evento, mientras el jugador sigue en su punto
# de decisión y no tiene evento pendiente.

import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import unittest

from DTOS.FichaCatalogo import FichaCatalogo, FichaEnemigo
from Modelo.rutas_ir_a import Paso
from Modelo.Viaje import DESTINO
from tests.utiles_terreno import mapa_a_mano


# ───────────────────────── Utilidades ─────────────────────────

def sala_de(motor, id_sala):
    sala = motor.buscar_sala(motor.salas, id_sala)
    if sala is None:
        raise ValueError(f"La sala {id_sala!r} no existe")
    return sala


def agregar_enemigo(motor, id_enemigo, id_sala, comportamiento, velocidad=100, ataque=1, vida_max=50):
    """Agrega un enemigo dormido con su propia ficha (FichaEnemigo.desde_json), sin activarlo."""
    id_ficha = f"ent_{comportamiento}_{id_enemigo}"
    motor.gestor_datos.fichas.append(FichaEnemigo.desde_json({
        "id": id_ficha, "clase": "enemigo", "nombre": comportamiento.capitalize(), "vida_max": vida_max,
        "ataque": ataque, "defensa": 0, "velocidad": velocidad, "comportamiento": comportamiento,
    }))
    enemigo = motor.crear_enemigo(id_enemigo, id_ficha, None, sala_de(motor, id_sala))
    motor.registrar_enemigo(enemigo)
    return enemigo


def esperar_hasta(motor, tiempo):
    # Cada «esperar» cuesta 100 con velocidad 100 (Parte I).
    while motor.reloj < tiempo:
        assert motor.ejecutar_accion("esperar"), "el motor rechazó «esperar»"
    assert motor.reloj == tiempo, f"el reloj quedó en {motor.reloj}, no en {tiempo}"


def turno_enemigo(prueba, motor, enemigo):
    """Ejecuta el siguiente evento de la agenda, que debe ser el turno de `enemigo`."""
    evento = motor.agenda.siguiente()
    prueba.assertIsNotNone(evento, "la agenda está vacía")
    prueba.assertIs(evento.actor, enemigo, "el siguiente evento no es el turno del enemigo")
    prueba.assertTrue(motor.ejecu_sig_evento())


def ejecutar_hasta(motor, tiempo):
    # Ejecuta todos los eventos con tiempo ≤ `tiempo`.
    while True:
        evento = motor.agenda.siguiente()
        if evento is None or evento.tiempo > tiempo:
            return
        motor.ejecu_sig_evento()


# ───────────────────────── Mapas ─────────────────────────

def pasillo(costo_ida, costo_vuelta=None, velocidad_jugador=None, sala_jugador=1):
    """Sala 1 -E-> sala 2 con `costo_ida`, y la vuelta 2 -O-> 1 con `costo_vuelta` (por defecto, el mismo)."""
    vuelta = costo_ida if costo_vuelta is None else costo_vuelta
    motor = mapa_a_mano([
        (1, [("E", 2, costo_ida, False)]),
        (2, [("O", 1, vuelta, False)]),
    ], sala_jugador=sala_jugador)
    if velocidad_jugador is not None:
        # En su punto de decisión el jugador no tiene evento pendiente: solo cambia la velocidad.
        motor.cambiar_velocidad(motor.jugador, velocidad_jugador)
    return motor


def cruce(costos, semilla=1):
    """Sala 2 con cuatro salidas de costos distintos hacia 1 (O), 3 (E), 4 (S) y 5 (N); el jugador está en 1.

    `costos` es un dict destino → costo (None = sin declarar). Cada sala vecina tiene una salida de vuelta a 2.
    """
    return mapa_a_mano([
        (1, [("E", 2, costos[1], False)]),
        (2, [("N", 5, costos[5], False), ("S", 4, costos[4], False), ("E", 3, costos[3], False),
             ("O", 1, costos[1], False)]),
        (3, [("O", 2, costos[3], False)]),
        (4, [("N", 2, costos[4], False)]),
        (5, [("S", 2, costos[5], False)]),
    ], sala_jugador=1, semilla=semilla)


COSTOS_CRUCE = {1: 300, 3: 150, 4: 50, 5: 700}
SIN_COSTOS_CRUCE = {1: None, 3: None, 4: None, 5: None}


# ───────────────────────── T019 ─────────────────────────

class TestCostoDeSalidaJugador(unittest.TestCase):
    def test_fr004_fr005_jugador_cruza_salida_de_costo_300(self):
        """T019. Escenario 1 de la US1 (FR-004, FR-005): el jugador con velocidad 100 cruza una salida de costo 300
        y su siguiente turno ocurre 300 unidades después."""
        motor = pasillo(300)
        self.assertEqual(motor.reloj, 0)
        self.assertEqual(motor.costo_salida(sala_de(motor, 1).salidas["E"]), 300)

        self.assertTrue(motor.ejecutar_accion("mover", "E"))

        self.assertEqual(motor.jugador.sala.id, 2)
        self.assertEqual(motor.jugador.tiempo_siguiente, 300)
        self.assertEqual(motor.reloj, 300)


# ───────────────────────── T020 ─────────────────────────

class TestSalidaSinCosto(unittest.TestCase):
    def test_fr002_jugador_cruza_salida_sin_costo_declarado(self):
        """T020. Escenario 2 de la US1 (FR-002): una salida sin costo declarado vale 100; el jugador con velocidad
        100 la cruza y su siguiente turno ocurre 100 unidades después, igual que en la Parte I."""
        motor = pasillo(None)
        self.assertEqual(motor.costo_salida(sala_de(motor, 1).salidas["E"]), 100)

        self.assertTrue(motor.ejecutar_accion("mover", "E"))

        self.assertEqual(motor.jugador.sala.id, 2)
        self.assertEqual(motor.reloj, 100)

    def test_fr002_errante_cruza_salida_sin_costo_declarado(self):
        """T020. Escenario 2 de la US1 (FR-002): «cualquier actor»; un errante de velocidad 100 cruza una salida sin
        costo declarado y su siguiente turno ocurre 100 unidades después."""
        motor = mapa_a_mano([
            (1, [("E", 2, None, False)]),
            (2, [("E", 3, None, False)]),
            (3, []),
        ], sala_jugador=1)
        errante = agregar_enemigo(motor, "err-1", 2, "errante")
        motor.activar_enemigo(errante)

        turno_enemigo(self, motor, errante)

        self.assertEqual(motor.reloj, 100)
        self.assertEqual(errante.sala.id, 3)
        self.assertEqual(errante.tiempo_siguiente, 200)


# ───────────────────────── T021 ─────────────────────────

class TestAmbosSentidos(unittest.TestCase):
    def test_fr003_mismo_costo_en_ambos_sentidos_ambos_tardan_250(self):
        """T021. Escenario 3 de la US1 (FR-003): los datos traen 250 en ambos sentidos de A–B; un actor cruza A→B
        y otro B→A, ambos con velocidad 100, y los dos tardan 250. Cada actor usa el costo de la salida que cruza."""
        ida = pasillo(250, sala_jugador=1)      # A = 1, B = 2
        vuelta = pasillo(250, sala_jugador=2)

        self.assertTrue(ida.ejecutar_accion("mover", "E"))
        self.assertTrue(vuelta.ejecutar_accion("mover", "O"))

        self.assertIsNot(ida.jugador, vuelta.jugador)
        self.assertEqual(ida.jugador.sala.id, 2)
        self.assertEqual(vuelta.jugador.sala.id, 1)
        self.assertEqual(ida.reloj, 250)
        self.assertEqual(vuelta.reloj, 250)


# ───────────────────────── T022 ─────────────────────────

class TestVelocidadAltaCostoUno(unittest.TestCase):
    def test_fr005_apendice_b_jugador_velocidad_1000_costo_1_intervalo_1(self):
        """T022. Apéndice B, «actor de velocidad alta cruza salida de costo 1»; escenario 4 de la US1 (FR-005):
        velocidad 1 000 y costo 1 dan intervalo max(1, 1 × 100 // 1 000) = 1, nunca 0."""
        motor = pasillo(1, velocidad_jugador=1000)
        self.assertEqual(motor.jugador.velocidad, 1000)

        self.assertTrue(motor.ejecutar_accion("mover", "E"))

        self.assertEqual(motor.jugador.sala.id, 2)
        self.assertEqual(motor.reloj, 1)

    def test_fr005_apendice_b_errante_velocidad_1000_costo_1_intervalo_1(self):
        """T022. Apéndice B, «actor de velocidad alta cruza salida de costo 1» (FR-005), con un enemigo: un errante
        de velocidad 1 000 cruza una salida de costo 1 y su siguiente turno ocurre 1 unidad después, nunca 0."""
        motor = mapa_a_mano([
            (1, [("E", 2, 100, False)]),
            (2, [("E", 3, 1, False)]),
            (3, []),
        ], sala_jugador=1)
        errante = agregar_enemigo(motor, "err-1", 2, "errante", velocidad=1000)
        motor.activar_enemigo(errante)            # primera acción: max(1, 100 × 100 // 1 000) = 10
        self.assertEqual(errante.tiempo_siguiente, 10)

        turno_enemigo(self, motor, errante)

        self.assertEqual(motor.reloj, 10)
        self.assertEqual(errante.sala.id, 3)
        self.assertEqual(errante.tiempo_siguiente, 11)


# ───────────────────────── T023 ─────────────────────────

class TestCambioDeVelocidadDuranteMovimiento(unittest.TestCase):
    def test_fr007_apendice_b_jugador_cambia_velocidad_tras_salida_de_costo_400(self):
        """T023. Apéndice B, «cambia la velocidad de un actor que cruza una salida costosa»; escenario 5 de la US1
        (FR-007): con velocidad 100 cruza una salida de costo 400 en t = 1 000 (próximo turno en 1 400); en
        t = 1 100 su velocidad pasa a 200 y su próximo turno queda en 1 100 + max(1, 300 × 100 // 200) = 1 250.

        El cambio de velocidad es un evento FIN_VELOCIDAD de la agenda, el mismo que cierra una poción."""
        motor = pasillo(400)
        esperar_hasta(motor, 1000)
        motor.programar_evento(1100, "FIN_VELOCIDAD", motor.jugador, -100)   # 100 - (-100) = 200

        self.assertTrue(motor.ejecutar_accion("mover", "E"))

        self.assertEqual(motor.jugador.sala.id, 2)
        self.assertEqual(motor.jugador.velocidad, 200)
        self.assertEqual(motor.reloj, 1250)
        self.assertEqual(motor.jugador.tiempo_siguiente, 1250)

    def test_fr007_apendice_b_errante_cambia_velocidad_tras_salida_de_costo_400(self):
        """T023. Apéndice B, «cambia la velocidad de un actor que cruza una salida costosa» (FR-007), con un
        enemigo: un errante de velocidad 100 cruza una salida de costo 400 en t = 1 000; en t = 1 100 su velocidad
        pasa a 200; su próximo turno queda en 1 250."""
        motor = mapa_a_mano([
            (1, [("E", 2, 100, False)]),
            (2, [("O", 1, 100, False)]),
            (3, [("S", 4, 400, False)]),
            (4, [("N", 3, 400, False)]),
        ], sala_jugador=1)
        errante = agregar_enemigo(motor, "err-1", 3, "errante")
        esperar_hasta(motor, 900)
        motor.activar_enemigo(errante)            # primera acción en 900 + 100 = 1 000

        turno_enemigo(self, motor, errante)
        self.assertEqual(motor.reloj, 1000)
        self.assertEqual(errante.sala.id, 4)
        motor.programar_evento(1100, "FIN_VELOCIDAD", errante, -100)

        ejecutar_hasta(motor, 1100)

        self.assertEqual(errante.tiempo_siguiente, 1250)
        self.assertEqual(errante.velocidad, 200)
        self.assertEqual(errante.sala.id, 4)       # no vuelve a la sala anterior ni repite el movimiento


# ───────────────────────── T024 ─────────────────────────

class TestEnemigosDecidenComoEnLaParteI(unittest.TestCase):
    SEMILLAS = (1, 2, 3, 4, 5, 6, 7, 8)

    def _primer_movimiento(self, costos, comportamiento, semilla):
        # El enemigo empieza en la sala 2 del cruce, se activa en t = 0 y actúa en t = 100.
        motor = cruce(costos, semilla=semilla)
        enemigo = agregar_enemigo(motor, "ene-1", 2, comportamiento)
        motor.activar_enemigo(enemigo)
        turno_enemigo(self, motor, enemigo)
        self.assertEqual(motor.reloj, 100)
        return enemigo

    def test_fr006_errante_elige_como_en_la_parte_i_y_tarda_el_costo_de_la_salida(self):
        """T024. Escenario 6 de la US1 (FR-006): con la misma semilla, un errante elige el mismo destino que en una
        cripta sin costos declarados (Parte I), y su siguiente turno ocurre según el costo de la salida que cruzó."""
        for semilla in self.SEMILLAS:
            with self.subTest(semilla=semilla):
                parte_i = self._primer_movimiento(SIN_COSTOS_CRUCE, "errante", semilla)
                terreno = self._primer_movimiento(COSTOS_CRUCE, "errante", semilla)

                self.assertEqual(parte_i.tiempo_siguiente, 200)
                self.assertEqual(terreno.sala.id, parte_i.sala.id)
                self.assertEqual(terreno.tiempo_siguiente, 100 + COSTOS_CRUCE[terreno.sala.id])

    def test_fr006_rastreador_elige_como_en_la_parte_i_y_tarda_el_costo_de_la_salida(self):
        """T024. Escenario 6 de la US1 (FR-006): con la misma semilla, un rastreador sigue el rastro igual que en una
        cripta sin costos declarados (Parte I), aunque esa salida sea la más cara, y su siguiente turno ocurre según
        el costo de la salida que cruzó."""
        for semilla in self.SEMILLAS[:2]:
            with self.subTest(semilla=semilla):
                parte_i = self._primer_movimiento(SIN_COSTOS_CRUCE, "rastreador", semilla)
                terreno = self._primer_movimiento(COSTOS_CRUCE, "rastreador", semilla)

                self.assertEqual(parte_i.sala.id, 1)    # el rastro del jugador está en la sala 1
                self.assertEqual(parte_i.tiempo_siguiente, 200)
                self.assertEqual(terreno.sala.id, parte_i.sala.id)
                self.assertEqual(terreno.tiempo_siguiente, 100 + COSTOS_CRUCE[1])


# ───────────────────────── T025 ─────────────────────────

class TestAccionesQueNoSonMoverse(unittest.TestCase):
    def _sala_cara(self):
        # El jugador en la sala 1, cuyas salidas cuestan 300.
        return mapa_a_mano([
            (1, [("E", 2, 300, False), ("S", 3, 300, False)]),
            (2, [("O", 1, 300, False)]),
            (3, [("N", 1, 300, False)]),
        ], sala_jugador=1)

    def test_fr005_esperar_conserva_su_costo_en_sala_de_salidas_caras(self):
        """T025. Escenario 7 de la US1 (FR-005): esperar cuesta 100, como en la Parte I, aunque las salidas de la
        sala cuesten 300."""
        motor = self._sala_cara()
        self.assertTrue(motor.ejecutar_accion("esperar"))
        self.assertEqual(motor.reloj, 100)

    def test_fr005_atacar_conserva_su_costo_en_sala_de_salidas_caras(self):
        """T025. Escenario 7 de la US1 (FR-005): atacar cuesta 100, como en la Parte I, aunque las salidas de la sala
        cuesten 300."""
        motor = self._sala_cara()
        guardian = agregar_enemigo(motor, "gua-1", 1, "guardian")
        motor.activar_enemigo(guardian)

        self.assertTrue(motor.ejecutar_accion("atacar", "gua-1"))

        self.assertEqual(motor.reloj, 100)
        self.assertEqual(motor.jugador.tiempo_siguiente, 100)

    def test_fr005_usar_objeto_conserva_su_costo_en_sala_de_salidas_caras(self):
        """T025. Escenario 7 de la US1 (FR-005): usar un objeto cuesta 50 (COSTO_USAR), como en la Parte I, aunque
        las salidas de la sala cuesten 300."""
        motor = self._sala_cara()
        motor.gestor_datos.fichas.append(FichaCatalogo.desde_json({
            "id": "poc_prueba", "clase": "pocion", "nombre": "Poción", "peso": 1, "valor": 1, "cura": 5,
        }))
        self.assertTrue(motor.jugador.inventario.recoge(motor.crear_objeto("poc-1", "poc_prueba")))

        self.assertTrue(motor.ejecutar_accion("usar", "poc-1"))

        self.assertEqual(motor.reloj, 50)


# ───────────────────────── T026 ─────────────────────────

def hacia_el_este(grafo, origen, destino):
    """Buscador inyectado con la firma de primer_paso: siempre toma la salida E de `origen`, si existe y es
    transitable en el grafo conocido. `primer_paso` todavía no existe (T062 de 001)."""
    for direccion, vecina, costo in grafo.aristas(origen):
        if direccion == "E":
            return Paso(direccion, vecina, costo)
    return None


class TestViajeIrA(unittest.TestCase):
    def test_fr004_fr026_cada_paso_de_ir_a_avanza_el_costo_de_su_salida(self):
        """T026. FR-004 y FR-026: cada paso de un viaje «ir a» es un `mover` y avanza el reloj según el costo de la
        salida de ese paso (300 y luego 150). Usa el buscador inyectado de Viaje porque primer_paso aún no existe."""
        motor = mapa_a_mano([
            (1, [("E", 2, 300, False)]),
            (2, [("O", 1, 300, False), ("E", 3, 150, False)]),
            (3, [("O", 2, 150, False)]),
        ], sala_jugador=1)
        # Explora hasta la sala 3 y vuelve a la 1, para que «ir a 3» se acepte (destino explorado, FR-022).
        for direccion in ("E", "E", "O", "O"):
            self.assertTrue(motor.ejecutar_accion("mover", direccion))
        self.assertEqual(motor.jugador.sala.id, 1)

        viaje, rechazo = motor.preparar_viaje("3", buscar=hacia_el_este)
        self.assertIsNone(rechazo)

        pasos = []
        while viaje.motivo is None:
            paso = viaje.siguiente_paso()
            self.assertIsNotNone(paso)
            antes = motor.reloj
            aceptado = motor.ejecutar_accion("mover", paso.direccion)
            viaje.terminar_paso(aceptado)
            pasos.append((paso.direccion, motor.jugador.sala.id, motor.reloj - antes))

        self.assertEqual(viaje.motivo, DESTINO)
        self.assertEqual(pasos, [("E", 2, 300), ("E", 3, 150)])


if __name__ == "__main__":
    unittest.main()
