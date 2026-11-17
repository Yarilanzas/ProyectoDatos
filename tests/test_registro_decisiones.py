# Pruebas del registro de decisiones de los cazadores (spec 003, T076; contracts/interfaz-cazador-linea.md §4;
# FR-024, FR-025). Partidas sintéticas de tests/utiles_terreno.py, varios cazadores con rangos distintos y la
# estrategia por defecto del motor.
#
# Interfaz que usan estas pruebas:
#   motor.registro_decisiones            -> None (apagado, por defecto) o lista de tuplas
#                                           (ciclo, reloj, id del cazador, acción, id de la sala de destino,
#                                            dirección de la salida o None, costo base)
#   motor.activar_registro_decisiones()  -> lo enciende con una lista vacía

import copy
import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.DecisionCazador import DecisionCazador
from tests.utiles_terreno import armar_motor, cripta_terreno

SEMILLA = 11
SALAS = 64              # cuadrícula de 8 × 8 en serpentina
SALA_JUGADOR = 28
# (sala, rango): uno pegado al jugador (llega y ataca), dos que persiguen, uno de rango grande lejos y uno de rango 0
CAZADORES = [(27, 150), (10, 300), (40, 800), (1, 5000), (60, 0)]
VIDA = 10 ** 6          # el jugador no muere durante las pruebas
ACCIONES = [("esperar", ""), ("mover", "E"), ("esperar", ""), ("mover", "O"), ("esperar", ""),
            ("mover", "N"), ("esperar", ""), ("mover", "S"), ("esperar", ""), ("esperar", ""),
            ("mover", "O"), ("esperar", ""), ("mover", "E"), ("esperar", ""), ("esperar", "")]
DIRECCIONES = ("N", "S", "E", "O")


def armar(encendido, cripta=None, otros=()):
    """Motor con los cazadores de CAZADORES, todos los enemigos activados y el jugador que no muere. ``cripta`` cambia
    la cripta (por omisión, cripta_terreno(SEMILLA, SALAS)). ``otros`` son pares (sala, comportamiento) de enemigos
    extra: utiles_terreno solo arma cazadores, así que se crean como cazadores y se les cambia el comportamiento antes
    de activarlos."""
    if cripta is None:
        cripta = cripta_terreno(SEMILLA, SALAS)
    motor = armar_motor(cripta, SALA_JUGADOR, CAZADORES + [(sala, 100) for sala, _ in otros])
    for indice in range(len(otros)):
        motor.enemigos[len(CAZADORES) + indice].comportamiento = otros[indice][1]
    motor.jugador.vida_max = VIDA
    motor.jugador.vida = VIDA
    for enemigo in motor.enemigos:
        motor.activar_enemigo(enemigo)
    if encendido:
        motor.activar_registro_decisiones()
    return motor


def jugar(motor, acciones=ACCIONES):
    for nombre, argumento in acciones:
        motor.ejecutar_accion(nombre, argumento)


def es_cazador(actor):
    return getattr(actor, "comportamiento", None) == "cazador"


def direccion_de(sala, salida):
    for direccion in DIRECCIONES:
        if sala.salidas.get(direccion) is salida:
            return direccion
    return None


def observar_turnos(motor):
    """Envuelve en la instancia ejecutar_evento, decidir_cazador, atacar y proxima_accion, y devuelve la lista donde se
    anota, por cada turno de un cazador, lo que el motor hizo de verdad: la tupla esperada en el registro y si el turno
    pasó por decidir_cazador."""
    observados = []
    turno = {}
    originales = (motor.ejecutar_evento, motor.decidir_cazador, motor.atacar, motor.proxima_accion)
    ejecutar, decidir, atacar, proxima = originales

    def decidir_envuelto(cazador):
        decision = decidir(cazador)
        turno["decision"] = decision
        return decision

    def atacar_envuelto(atacante, defensor):
        if atacante is turno.get("actor"):
            turno["ataco"] = True
        return atacar(atacante, defensor)

    def proxima_envuelta(actor, costo=100):
        if actor is turno.get("actor"):
            turno["costo"] = costo
        return proxima(actor, costo)

    def ejecutar_envuelto(evento):
        actor = evento.actor
        if not (es_cazador(actor) and actor.esta_vivo() and evento.tipo == "ACCION_ACTOR"):
            return ejecutar(evento)
        turno.clear()
        turno["actor"] = actor
        sala_antes = actor.sala
        resultado = ejecutar(evento)
        decision = turno.get("decision")
        if turno.get("ataco"):
            accion, direccion = "ATACAR", None
        elif actor.sala is not sala_antes:
            accion = "MOVER"
            direccion = direccion_de(sala_antes, decision.salida)
        else:
            accion, direccion = "ESPERAR", None
        observados.append(((motor.ciclo, motor.reloj, actor.id, accion, actor.sala.id, direccion, turno["costo"]),
                           decision))
        turno.clear()
        return resultado

    motor.ejecutar_evento = ejecutar_envuelto
    motor.decidir_cazador = decidir_envuelto
    motor.atacar = atacar_envuelto
    motor.proxima_accion = proxima_envuelta
    return observados


def comprobar_contra_observados(prueba, motor, observados):
    """El registro es igual a los turnos observados y cada entrada concuerda con la DecisionCazador devuelta. Devuelve
    las acciones vistas, los ATACAR resueltos sin decidir_cazador y los costos de los MOVER."""
    prueba.assertEqual(motor.registro_decisiones, [esperado for esperado, _ in observados])
    acciones, ataques_sin_decidir, costos_mover = set(), 0, []
    for (_ciclo, _reloj, _id, accion, destino, direccion, costo), decision in observados:
        acciones.add(accion)
        if accion == "ATACAR":
            prueba.assertEqual((direccion, costo), (None, 100))
            if decision is None:
                ataques_sin_decidir += 1
        elif accion == "MOVER":
            prueba.assertEqual(decision.accion, DecisionCazador.MOVER)
            prueba.assertEqual(costo, decision.costo_base)
            prueba.assertEqual(decision.salida.sala_destino, destino)
            costos_mover.append(costo)
        else:
            prueba.assertEqual(costo, 100)
            prueba.assertIsNone(direccion)
            prueba.assertEqual(decision.accion, DecisionCazador.ESPERAR)
    return acciones, ataques_sin_decidir, costos_mover


def contar_turnos(motor):
    """Envuelve ejecutar_evento en la instancia y devuelve la lista de ids de los actores que tuvieron un turno
    (ACCION_ACTOR de un enemigo vivo). Debe aplicarse antes de observar_turnos para no perder los turnos de cazador."""
    turnos = []
    ejecutar = motor.ejecutar_evento

    def envuelto(evento):
        actor = evento.actor
        if evento.tipo == "ACCION_ACTOR" and actor is not motor.jugador and getattr(actor, "esta_vivo", None) \
                and actor.esta_vivo():
            turnos.append(actor.id)
        return ejecutar(evento)

    motor.ejecutar_evento = envuelto
    return turnos


def cambios_de_decision(motor):
    """Cambios del historial que deshacen una anotación del registro."""
    return [cambio for intervalo in motor.historial._intervalos for cambio in intervalo
            if cambio.description.startswith("decisión de")]


class TestRegistroApagado(unittest.TestCase):
    def test_fr024_apagado_por_defecto_y_no_cambia_el_estado(self):
        """T076 (contrato §4, «Activable»): el registro está apagado por defecto (None). Con la misma semilla y las
        mismas acciones, motor.obtener_estado_resumen() (reloj, secuencia, azar, enemigos, eventos, puertas...) es el
        mismo apagado que encendido, y apagado no anota nada en el historial."""
        apagado = armar(encendido=False)
        self.assertIsNone(apagado.registro_decisiones)
        encendido = armar(encendido=True)
        self.assertEqual(encendido.registro_decisiones, [])

        for nombre, argumento in ACCIONES:
            self.assertEqual(apagado.ejecutar_accion(nombre, argumento),
                             encendido.ejecutar_accion(nombre, argumento))
            self.assertEqual(apagado.obtener_estado_resumen(), encendido.obtener_estado_resumen())

        self.assertIsNone(apagado.registro_decisiones)
        self.assertEqual(cambios_de_decision(apagado), [])
        self.assertGreater(len(encendido.registro_decisiones), 0)

    def test_fr021_no_consume_azar(self):
        """T076 (contrato §3): motor.azar.getstate() es el mismo con el registro apagado y encendido, después de cada
        acción."""
        apagado, encendido = armar(encendido=False), armar(encendido=True)
        self.assertEqual(apagado.azar.getstate(), encendido.azar.getstate())
        for accion in ACCIONES:
            jugar(apagado, [accion])
            jugar(encendido, [accion])
            self.assertEqual(apagado.azar.getstate(), encendido.azar.getstate())


class TestRegistroEncendido(unittest.TestCase):
    def test_fr025_cada_entrada_coincide_con_lo_que_hizo_el_motor(self):
        """T076 (contrato §4, «Qué anota»): cada entrada coincide con el turno observado: ataque real, movimiento real
        (sala de destino y dirección de la salida cruzada) y costo con el que se reprogramó; MOVER y ESPERAR coinciden
        con la DecisionCazador devuelta; los turnos de ATACAR resueltos por accion_enemigo (sin decidir_cazador) también
        se anotan. Ciclo y reloj no decrecen."""
        motor = armar(encendido=True)
        observados = observar_turnos(motor)
        jugar(motor)

        acciones, ataques_sin_decidir, _costos = comprobar_contra_observados(self, motor, observados)
        self.assertEqual(acciones, {"ATACAR", "MOVER", "ESPERAR"})
        self.assertGreater(ataques_sin_decidir, 0, "ningún ATACAR resuelto por accion_enemigo")

        claves = [(entrada[0], entrada[1]) for entrada in motor.registro_decisiones]
        self.assertEqual(claves, sorted(claves), "ciclo y reloj deben crecer juntos")
        ciclos = [entrada[0] for entrada in motor.registro_decisiones]
        self.assertGreaterEqual(len(set(ciclos)), len(ACCIONES) // 2)

    def test_fr025_costos_distintos_quedan_en_el_registro(self):
        """T076 (FR-005, FR-007): con costos que varían por salida y por sentido (cripta_terreno con costo_ida=120,
        costo_vuelta=80, variacion=40), el registro sigue igual a los turnos observados y el costo base de cada MOVER es
        el de la salida cruzada: al menos un MOVER cuesta distinto de 100 y hay al menos dos costos distintos entre los
        MOVER (con todas las salidas a 100, un registro que anotara siempre 100 pasaría)."""
        cripta = cripta_terreno(SEMILLA, SALAS, costo_ida=120, costo_vuelta=80, variacion=40)
        motor = armar(encendido=True, cripta=cripta)
        observados = observar_turnos(motor)
        jugar(motor)

        _acciones, _ataques, costos_mover = comprobar_contra_observados(self, motor, observados)
        self.assertTrue(any(costo != 100 for costo in costos_mover), f"todos los MOVER cuestan 100: {costos_mover}")
        self.assertGreaterEqual(len(set(costos_mover)), 2, f"un solo costo entre los MOVER: {costos_mover}")
        for _ciclo, _reloj, id_cazador, accion, destino, direccion, costo in motor.registro_decisiones:
            if accion == "MOVER":
                origen = None
                for sala in motor.salas:
                    salida = sala.salidas.get(direccion)
                    if salida is not None and salida.sala_destino == destino and salida.costo == costo:
                        origen = sala
                        break
                self.assertIsNotNone(origen, f"ninguna salida {direccion} hacia {destino} cuesta {costo}")

    def test_fr018_solo_anota_cazadores(self):
        """T076 (contrato §4, «Qué anota»): con un errante y un guardián activos además de los cazadores, todos los ids
        del registro son de cazadores, los no cazadores tuvieron turnos y los cazadores tienen entradas. Los errantes
        consumen el azar del motor: obtener_estado_resumen() es el mismo con el registro apagado y encendido."""
        otros = [(36, "errante"), (50, "guardian")]
        apagado = armar(encendido=False, otros=otros)
        encendido = armar(encendido=True, otros=otros)
        no_cazadores = [e.id for e in encendido.enemigos if e.comportamiento != "cazador"]
        self.assertEqual(len(no_cazadores), 2)
        turnos = contar_turnos(encendido)

        for nombre, argumento in ACCIONES:
            self.assertEqual(apagado.ejecutar_accion(nombre, argumento),
                             encendido.ejecutar_accion(nombre, argumento))
            self.assertEqual(apagado.obtener_estado_resumen(), encendido.obtener_estado_resumen())

        cazadores = [e.id for e in encendido.enemigos if e.comportamiento == "cazador"]
        ids_registro = [entrada[2] for entrada in encendido.registro_decisiones]
        self.assertGreater(len(ids_registro), 0)
        self.assertTrue(all(id_actor in cazadores for id_actor in ids_registro),
                        f"ids que no son de cazadores en el registro: {set(ids_registro) - set(cazadores)}")
        for id_otro in no_cazadores:
            self.assertIn(id_otro, turnos, f"{id_otro} no tuvo turnos")
        self.assertEqual(len(ids_registro), sum(1 for id_actor in turnos if id_actor in cazadores))

    def test_fr024_iniciar_partida_reinicia_el_registro_encendido(self):
        """T076: iniciar_partida deja vacío un registro encendido (solo las decisiones de la partida nueva) y deja
        apagado uno apagado."""
        motor = armar(encendido=True)
        jugar(motor, ACCIONES[:3])
        self.assertGreater(len(motor.registro_decisiones), 0)
        otro = armar(encendido=False)
        motor.iniciar_partida(otro.jugador, otro.salas, [])
        self.assertEqual(motor.registro_decisiones, [])

        apagado = armar(encendido=False)
        apagado.iniciar_partida(otro.jugador, otro.salas, [])
        self.assertIsNone(apagado.registro_decisiones)


class TestRegistroReversible(unittest.TestCase):
    def test_fr024_retroceso_deja_el_registro_del_estado_al_que_se_vuelve(self):
        """T076 (contrato §4, «Reversible con la historia»): tras cada retroceso con el Historial del motor
        (motor.historial.deshacer_ultimo(), lo mismo que hace el pergamino), el registro es igual, entrada por entrada,
        al que tenía en el estado al que se volvió, y el resto del estado también."""
        motor = armar(encendido=True)
        fotos = []  # una por acción aceptada: un comando rechazado no abre intervalo en el historial
        for nombre, argumento in ACCIONES:
            foto = (list(motor.registro_decisiones), motor.obtener_estado_resumen())
            if motor.ejecutar_accion(nombre, argumento):
                fotos.append(foto)

        retrocesos = 0
        while motor.historial.puede_deshacer():
            motor.historial.deshacer_ultimo()
            retrocesos += 1
            registro, resumen = fotos[-retrocesos]
            self.assertEqual(motor.registro_decisiones, registro)
            self.assertEqual(motor.obtener_estado_resumen(), resumen)
        self.assertGreater(retrocesos, 0)

    def test_fr024_retroceso_y_nueva_accion_anotan_la_historia_vigente(self):
        """T076: después de retroceder, la acción nueva anota sus decisiones sobre la historia vigente: el registro
        coincide con el de un motor que nunca hizo la acción revertida (sin el ciclo, que solo crece). Solo «esperar»,
        que siempre se acepta, para que cada acción abra su intervalo."""
        esperar = [("esperar", "")]
        motor = armar(encendido=True)
        jugar(motor, esperar * 6)
        self.assertTrue(motor.historial.deshacer_ultimo())
        jugar(motor, esperar)

        directo = armar(encendido=True)
        jugar(directo, esperar * 6)
        self.assertEqual([entrada[1:] for entrada in motor.registro_decisiones],
                         [entrada[1:] for entrada in directo.registro_decisiones])


class TestRegistroClon(unittest.TestCase):
    def test_fr025_clon_tiene_registro_propio_y_avanza_igual(self):
        """T076 (contrato §4, «Dónde vive»): copy.deepcopy(motor) con el registro encendido da al clon un registro
        propio, igual al del original; lo que se anota en el clon no cambia el del original, y continuando los dos con
        las mismas acciones los registros coinciden entrada por entrada."""
        motor = armar(encendido=True)
        jugar(motor, ACCIONES[:5])
        clon = copy.deepcopy(motor)

        self.assertIsNot(clon.registro_decisiones, motor.registro_decisiones)
        self.assertEqual(clon.registro_decisiones, motor.registro_decisiones)

        antes = list(motor.registro_decisiones)
        jugar(clon, ACCIONES[5:8])
        self.assertEqual(motor.registro_decisiones, antes)
        self.assertGreater(len(clon.registro_decisiones), len(antes))

        jugar(motor, ACCIONES[5:8])
        self.assertEqual(motor.registro_decisiones, clon.registro_decisiones)
        jugar(motor, ACCIONES[8:])
        jugar(clon, ACCIONES[8:])
        self.assertEqual(motor.registro_decisiones, clon.registro_decisiones)


if __name__ == "__main__":
    unittest.main()
