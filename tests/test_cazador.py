# Pruebas de la historia US2 de la capacidad 003: el cazador persigue por la ruta más barata (T033 a T044), más la
# lectura del rango desde la ficha (T045). FR-009 a FR-021 y FR-034; escenarios 1 a 8 de la US2 y dos casos «Terreno y
# cazador» del Apéndice B.
#
# Regla de la decisión (data-model §8), en este orden:
#   1. misma sala que el jugador -> atacar (costo 100 de la Parte I);
#   2. sin ruta abierta, o distancia mínima d > rango -> esperar con costo 100;
#   3. si no, un paso por una ruta de costo d: a la vecina de menor id entre las que dan el mínimo y, entre salidas a
#      esa vecina, la de menor costo y luego N, S, E, O.
# El intervalo de toda acción es max(1, costo_base × 100 // velocidad); los cazadores de utiles_terreno tienen
# velocidad 100, así que el intervalo es el costo base.
#
# Cómo se observa: la decisión todavía no tiene un método fijo, así que estas pruebas no la llaman. Manejan la partida
# con motor.ejecutar_accion("esperar", None) / ("mover", d) / ("atacar", id) y miran cazador.sala,
# cazador.tiempo_siguiente, motor.reloj y los mensajes. Para ver qué salida cruzó un enemigo se envuelve
# motor.mover_enemigo en la instancia (ya existe y es por donde se mueven todos los enemigos). Para «no busca» se
# envuelven motor.grafo_cripta.aristas y motor.grafo_cripta.entrantes con un contador, en la instancia: cualquier
# estrategia (búsqueda adelante o campo al revés) usa una de las dos.
#
# Orden supuesto entre eventos del mismo instante (leído de Modelo/Evento.py y Modelo/AgendaEventos.py): la agenda es
# un montículo ordenado por (tiempo, secuencia), y la secuencia crece con cada programar_evento. Cuando el cazador
# actúa en t, se reprograma para t + c ANTES de que el jugador, en su turno de t, se programe para t + c'. Por eso, si
# los dos quedan en el mismo instante, actúa primero el cazador. Igual con motor.activar_enemigo(cazador) en el punto
# de decisión del jugador (reloj r): el cazador queda en r + 100 con secuencia menor que la del siguiente turno del
# jugador, y avanzar_hasta_jugador ejecuta su turno antes de devolver el control al jugador en r + 100.

import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import random
import unittest

from DTOS.ContenidoSala import ContenidoSala
from DTOS.FichaCatalogo import FichaCatalogo, FichaEnemigo
from DTOS.TrampaInstancia import TrampaInstancia
from Modelo.Conocimiento import EXPLORADA
from tests.test_ruta_contrato import DESEMPATES, invertido
from tests.utiles_terreno import CAZADOR, ID_JUGADOR, armar_motor, cripta_terreno, mapa_a_mano


# ───────────────────────── Utilidades ─────────────────────────

def sala_de(motor, id_sala):
    sala = motor.buscar_sala(motor.salas, id_sala)
    if sala is None:
        raise ValueError(f"La sala {id_sala!r} no existe")
    return sala


def cazadores_de(motor):
    """Los cazadores del motor, en el orden de `cazadores` de mapa_a_mano (caz-001, caz-002, ...)."""
    return [e for e in motor.enemigos if e.comportamiento == "cazador"]


def esperar(prueba, motor, veces=1):
    for _ in range(veces):
        prueba.assertTrue(motor.ejecutar_accion("esperar", None), "el motor rechazó «esperar»")


def agregar_enemigo(motor, id_enemigo, id_sala, comportamiento):
    """Agrega un enemigo dormido con las mismas estadísticas que el cazador de utiles_terreno (ataque 3, defensa 0,
    vida 8, velocidad 100), con su propia ficha FichaEnemigo.desde_json."""
    id_ficha = f"ent_{comportamiento}_{id_enemigo}"
    datos = dict(CAZADOR)
    datos.update({"id": id_ficha, "nombre": comportamiento.capitalize(), "comportamiento": comportamiento})
    motor.gestor_datos.fichas.append(FichaEnemigo.desde_json(datos))
    enemigo = motor.crear_enemigo(id_enemigo, id_ficha, None, sala_de(motor, id_sala))
    motor.registrar_enemigo(enemigo)
    return enemigo


def registrar_movimientos(motor):
    """Envuelve motor.mover_enemigo en la instancia. Devuelve la lista donde quedan (id, dirección, id destino, reloj)
    de cada movimiento de enemigo."""
    movimientos = []
    original = motor.mover_enemigo

    def envoltura(enemigo, salas, salida):
        direccion = None
        for d in enemigo.sala.salidas:
            if enemigo.sala.salidas[d] is salida:
                direccion = d
        resultado = original(enemigo, salas, salida)
        if resultado:
            movimientos.append((enemigo.id, direccion, enemigo.sala.id, motor.reloj))
        return resultado

    motor.mover_enemigo = envoltura
    return movimientos


def registrar_mensajes(motor):
    """Envuelve motor._mensaje en la instancia y devuelve la lista con todos los mensajes desde ese momento."""
    mensajes = []
    original = motor._mensaje

    def envoltura(texto):
        mensajes.append(texto)
        return original(texto)

    motor._mensaje = envoltura
    return mensajes


def contar_busquedas(motor):
    """Reemplaza aristas y entrantes de motor.grafo_cripta por envolturas contadoras (en la instancia). Devuelve una
    lista de un elemento con la cuenta."""
    cuenta = [0]
    grafo = motor.grafo_cripta
    for nombre in ("aristas", "entrantes"):
        original = getattr(grafo, nombre)

        def envoltura(*args, _original=original, **kwargs):
            cuenta[0] += 1
            return _original(*args, **kwargs)

        setattr(grafo, nombre, envoltura)
    return cuenta


def turnos_pendientes(motor, actor):
    """Eventos ACCION_ACTOR no cancelados de `actor` en la agenda."""
    return [e for e in motor.agenda.heap if e.actor is actor and e.tipo == "ACCION_ACTOR" and not e.cancelado]


# ───────────────────────── Mapas ─────────────────────────

# Apéndice B, «ruta de menos salas pero mayor costo vs. más salas y menor costo» (docstring de mapa_a_mano):
# 1 -> 2 -> 3 cuesta 250 + 250 = 500 (2 salidas); 1 -> 4 -> 5 -> 6 -> 3 cuesta 100 × 4 = 400 (4 salidas).
MAPA_DOS_RUTAS = [
    (1, [("E", 2, 250, False), ("S", 4, 100, False)]),
    (2, [("E", 3, 250, False)]),
    (3, []),
    (4, [("E", 5, 100, False)]),
    (5, [("E", 6, 100, False)]),
    (6, [("N", 3, 100, False)]),
]

# 1 -E(150)-> 2 -E(100)-> 3, sin vueltas: d(1, 3) = 250.
PASILLO_150 = [
    (1, [("E", 2, 150, False)]),
    (2, [("E", 3, 100, False)]),
    (3, []),
]

# 1 -E(300)-> 2 -E(200)-> 3: d(1, 3) = 500.
PASILLO_500 = [
    (1, [("E", 2, 300, False)]),
    (2, [("E", 3, 200, False)]),
    (3, []),
]


# ───────────────────────── T033 ─────────────────────────

class TestAtacaEnLaMismaSala(unittest.TestCase):
    def _comprobar_ataque(self, rango):
        motor = mapa_a_mano([(1, [("E", 2, 100, False)]), (2, [("O", 1, 100, False)])], sala_jugador=1,
                            cazadores=[(1, rango)])
        cazador = cazadores_de(motor)[0]
        self.assertTrue(cazador.activo, "el cazador en la sala inicial del jugador debería activarse al empezar")
        self.assertEqual(cazador.tiempo_siguiente, 100)
        mensajes = registrar_mensajes(motor)
        vida = motor.jugador.vida

        esperar(self, motor)

        self.assertEqual(motor.reloj, 100)
        self.assertLess(motor.jugador.vida, vida, "el cazador no dañó al jugador")
        self.assertTrue(any(m.startswith(f"{cazador.id} ataca a {ID_JUGADOR}") for m in mensajes), mensajes)
        self.assertIs(cazador.sala, sala_de(motor, 1))
        self.assertEqual(cazador.tiempo_siguiente, 200, "atacar cuesta 100 (Parte I)")

    def test_fr010_ataca_con_costo_100(self):
        """T033. Escenario 1 de la US2 (FR-010): un cazador en la sala del jugador lo ataca y su siguiente turno
        ocurre 100 después (costo de ataque de la Parte I)."""
        self._comprobar_ataque(400)

    def test_fr010_ataca_con_rango_0(self):
        """T033. Escenario 1 de la US2 (FR-010): con rango 0 también ataca si comparte sala, sin importar el rango."""
        self._comprobar_ataque(0)


# ───────────────────────── T034 ─────────────────────────

class TestRutaMasBarataConMasSalas(unittest.TestCase):
    def test_fr011_fr013_apendice_b_menos_salas_mayor_costo_vs_mas_salas_menor_costo(self):
        """T034. Apéndice B, «ruta de menos salas pero mayor costo vs. más salas y menor costo»; escenario 2 de la US2
        (FR-011, FR-013): cazador en 1 con rango 400 y jugador en 3; la ruta 1-2-3 cuesta 500 y la 1-4-5-6-3 cuesta
        400. Da su primer paso hacia 4 (salida S, costo 100) y sigue la ruta de 400 hasta el jugador."""
        motor = mapa_a_mano(MAPA_DOS_RUTAS, sala_jugador=3, cazadores=[(1, 400)])
        cazador = cazadores_de(motor)[0]
        movimientos = registrar_movimientos(motor)
        motor.activar_enemigo(cazador)                 # primera acción en t = 100

        esperar(self, motor)
        self.assertEqual(motor.reloj, 100)
        self.assertEqual(cazador.sala.id, 4, "no tomó la ruta de costo 400")
        self.assertEqual(cazador.tiempo_siguiente, 200, "la salida 1 -S-> 4 cuesta 100")

        esperar(self, motor, 3)
        self.assertEqual(motor.reloj, 400)
        self.assertEqual(movimientos, [(cazador.id, "S", 4, 100), (cazador.id, "E", 5, 200),
                                       (cazador.id, "E", 6, 300), (cazador.id, "N", 3, 400)])


# ───────────────────────── T035 ─────────────────────────

class TestDesempate(unittest.TestCase):
    def _primer_paso(self, salas):
        """Cazador en 1 con rango 1000, jugador en 4. Devuelve (cazador, movimientos) tras su primer turno (t = 100)."""
        motor = mapa_a_mano(salas, sala_jugador=4, cazadores=[(1, 1000)])
        cazador = cazadores_de(motor)[0]
        movimientos = registrar_movimientos(motor)
        motor.activar_enemigo(cazador)
        esperar(self, motor)
        self.assertEqual(motor.reloj, 100)
        return cazador, movimientos

    def test_fr014_apendice_b_dos_vecinas_con_rutas_de_costo_minimo(self):
        """T035. Apéndice B, «dos vecinas con rutas de costo mínimo»; escenario 3 de la US2 (FR-014): desde 1, ir por 2
        o por 3 cuesta 200 en ambos casos; va a la vecina de menor id (2), aunque su salida (S) esté después de la de
        la vecina 3 (N) en el orden N, S, E, O."""
        cazador, movimientos = self._primer_paso([
            (1, [("N", 3, 100, False), ("S", 2, 100, False)]),
            (2, [("E", 4, 100, False)]),
            (3, [("E", 4, 100, False)]),
            (4, []),
        ])
        self.assertEqual(movimientos, [(cazador.id, "S", 2, 100)])
        self.assertEqual(cazador.tiempo_siguiente, 200)

    def test_fr014_dos_salidas_de_igual_costo_a_la_misma_vecina_usa_n_antes_que_s(self):
        """T035 (FR-014): dos salidas abiertas de 1 hacia la vecina 2 con el mismo costo (S declarada antes que N):
        usa la primera en el orden N, S, E, O, es decir, N."""
        cazador, movimientos = self._primer_paso([
            (1, [("S", 2, 100, False), ("N", 2, 100, False), ("E", 3, 100, False)]),
            (2, [("E", 4, 100, False)]),
            (3, [("E", 4, 150, False)]),
            (4, []),
        ])
        self.assertEqual(movimientos, [(cazador.id, "N", 2, 100)])
        self.assertEqual(cazador.tiempo_siguiente, 200)

    def test_fr014_entre_salidas_a_la_misma_vecina_gana_la_barata_aunque_vaya_despues(self):
        """T035 (FR-014): dos salidas de 1 hacia la vecina 2, N con costo 300 y S con costo 100: usa S, la más
        barata, aunque N vaya antes en el orden N, S, E, O; su siguiente turno ocurre 100 después."""
        cazador, movimientos = self._primer_paso([
            (1, [("N", 2, 300, False), ("S", 2, 100, False)]),
            (2, [("E", 4, 100, False)]),
            (4, []),
        ])
        self.assertEqual(movimientos, [(cazador.id, "S", 2, 100)])
        self.assertEqual(cazador.tiempo_siguiente, 200)

    def test_fr014_la_vecina_de_menor_id_no_gana_si_su_ruta_es_mas_cara(self):
        """T035 (FR-014): la vecina de menor id (2) solo gana entre las que dan el mínimo; por 2 la ruta cuesta 400 y
        por 3 cuesta 200, así que va a 3."""
        cazador, movimientos = self._primer_paso([
            (1, [("N", 2, 300, False), ("S", 3, 100, False)]),
            (2, [("E", 4, 100, False)]),
            (3, [("E", 4, 100, False)]),
            (4, []),
        ])
        self.assertEqual(movimientos, [(cazador.id, "S", 3, 100)])
        self.assertEqual(cazador.tiempo_siguiente, 200)


# ───────────────────────── T036 ─────────────────────────

class TestCostoDelPaso(unittest.TestCase):
    def test_fr013_paso_por_salida_de_costo_150(self):
        """T036. Escenario 4 de la US2 (FR-013): el cazador (velocidad 100) cruza una salida de costo 150 en t = 100 y
        su siguiente turno ocurre en t = 250, donde da el paso siguiente (costo 100, turno en 350)."""
        motor = mapa_a_mano(PASILLO_150, sala_jugador=3, cazadores=[(1, 1000)])
        cazador = cazadores_de(motor)[0]
        motor.activar_enemigo(cazador)

        esperar(self, motor)
        self.assertEqual(motor.reloj, 100)
        self.assertEqual(cazador.sala.id, 2)
        self.assertEqual(cazador.tiempo_siguiente, 250)

        esperar(self, motor)                                     # t = 200: todavía no le toca
        self.assertEqual(cazador.sala.id, 2)

        esperar(self, motor)                                     # t = 300: actuó en 250
        self.assertEqual(cazador.sala.id, 3)
        self.assertEqual(cazador.tiempo_siguiente, 350)


# ───────────────────────── T037 ─────────────────────────

class TestRangoExacto(unittest.TestCase):
    def test_fr012_distancia_igual_al_rango_se_mueve(self):
        """T037. Escenario 5 de la US2 (FR-012): d(1, 3) = 500 y rango 500; el cazador se mueve (paso de costo 300)."""
        motor = mapa_a_mano(PASILLO_500, sala_jugador=3, cazadores=[(1, 500)])
        cazador = cazadores_de(motor)[0]
        motor.activar_enemigo(cazador)

        esperar(self, motor)

        self.assertEqual(cazador.sala.id, 2)
        self.assertEqual(cazador.tiempo_siguiente, 400)

    def test_fr012_distancia_igual_al_rango_mas_uno_espera(self):
        """T037. Escenario 5 de la US2 (FR-012): d(1, 3) = 500 y rango 499; el cazador espera con costo 100, turno tras
        turno."""
        motor = mapa_a_mano(PASILLO_500, sala_jugador=3, cazadores=[(1, 499)])
        cazador = cazadores_de(motor)[0]
        motor.activar_enemigo(cazador)

        esperar(self, motor)
        self.assertEqual(cazador.sala.id, 1)
        self.assertEqual(cazador.tiempo_siguiente, 200)

        esperar(self, motor)
        self.assertEqual(cazador.sala.id, 1)
        self.assertEqual(cazador.tiempo_siguiente, 300)


# ───────────────────────── T038 ─────────────────────────

class TestJugadorCambiaDeSala(unittest.TestCase):
    def test_fr016_decide_con_la_sala_actual_del_jugador(self):
        """T038. Escenario 6 de la US2 (FR-016): cazador en 1 (rango 1000) y jugador en 3. En t = 100 el cazador va
        a 2 (ruta 1-2-3). Luego el jugador cruza la salida de un solo sentido 3 -E-> 5 (costo 600). En su turno de
        t = 200 el cazador decide con la sala nueva: va a 1 (ruta 2-1-4-5, costo 300; la de 2-3-5 cuesta 700), no a 3.
        Sigue hasta 5 en t = 400."""
        motor = mapa_a_mano([
            (1, [("N", 2, 100, False), ("S", 4, 100, False)]),
            (2, [("N", 3, 100, False), ("S", 1, 100, False)]),
            (3, [("S", 2, 100, False), ("E", 5, 600, False)]),
            (4, [("N", 1, 100, False), ("S", 5, 100, False)]),
            (5, [("N", 4, 100, False)]),
        ], sala_jugador=3, cazadores=[(1, 1000)])
        cazador = cazadores_de(motor)[0]
        movimientos = registrar_movimientos(motor)
        motor.activar_enemigo(cazador)

        esperar(self, motor)
        self.assertEqual(movimientos, [(cazador.id, "N", 2, 100)])

        self.assertTrue(motor.ejecutar_accion("mover", "E"))     # el jugador queda en 5; su turno vuelve en 700
        self.assertEqual(motor.jugador.sala.id, 5)
        self.assertEqual(motor.reloj, 700)
        self.assertEqual(movimientos[:4], [(cazador.id, "N", 2, 100), (cazador.id, "S", 1, 200),
                                           (cazador.id, "S", 4, 300), (cazador.id, "S", 5, 400)])
        self.assertEqual(len(movimientos), 4, "después de llegar a 5 debería atacar, no moverse")


# ───────────────────────── T039 ─────────────────────────

# 1 <-> 2 (100); desde 2 sale una salida de un sentido 2 -E-> 5 que cuesta 600; 2 <-> 3 <-> 4 y 4 <-> 5 cuestan 100.
# Desde 2, el cazador llega a 5 por 2-3-4-5 (300), más barato que 2-5 (600).
MAPA_ACTIVACION = [
    (1, [("E", 2, 100, False)]),
    (2, [("O", 1, 100, False), ("E", 5, 600, False), ("S", 3, 100, False)]),
    (3, [("N", 2, 100, False), ("E", 4, 100, False)]),
    (4, [("O", 3, 100, False), ("N", 5, 100, False)]),
    (5, [("S", 4, 100, False)]),
]


class TestActivacion(unittest.TestCase):
    def _motor(self):
        motor = mapa_a_mano(MAPA_ACTIVACION, sala_jugador=1, cazadores=[(2, 1000)])
        return motor, cazadores_de(motor)[0]

    def test_fr034_dormido_dentro_del_rango_no_actua_ni_busca(self):
        """T039. Escenario 7 de la US2 (FR-034): cazador dormido en 2, a distancia 100 del jugador y con rango 1000;
        el jugador nunca entra a su sala. Pasa el tiempo y el cazador no actúa, no se mueve y no consulta el grafo
        (0 llamadas a grafo_cripta.aristas y grafo_cripta.entrantes)."""
        motor, cazador = self._motor()
        cuenta = contar_busquedas(motor)
        movimientos = registrar_movimientos(motor)

        esperar(self, motor, 6)

        self.assertEqual(motor.reloj, 600)
        self.assertFalse(cazador.activo)
        self.assertEqual(cazador.sala.id, 2)
        self.assertEqual(movimientos, [])
        self.assertEqual(turnos_pendientes(motor, cazador), [])
        self.assertEqual(cuenta[0], 0, "un cazador dormido consultó el grafo")

    def test_fr034_al_entrar_el_jugador_se_activa_con_primera_accion_de_costo_100(self):
        """T039. Escenario 8 de la US2 (FR-034): el jugador entra a la sala del cazador en t = 0; el cazador queda
        activo, su primera acción ocurre en t = 100 (costo base 100: ataca) y la siguiente queda en 200."""
        motor, cazador = self._motor()
        mensajes = registrar_mensajes(motor)
        self.assertEqual(turnos_pendientes(motor, cazador), [])

        self.assertTrue(motor.ejecutar_accion("mover", "E"))

        self.assertTrue(cazador.activo)
        self.assertEqual(motor.reloj, 100)
        self.assertEqual(len([m for m in mensajes if m.startswith(f"{cazador.id} ataca")]), 1, mensajes)
        self.assertEqual(cazador.tiempo_siguiente, 200)

    def test_fr034_persigue_cuando_el_jugador_sale_dentro_del_rango(self):
        """T039. Escenario 8 de la US2 (FR-034): activado al entrar el jugador a 2, el jugador vuelve a 1 en t = 100;
        en su turno de t = 200 el cazador lo sigue a 1 (distancia 100 ≤ rango 1000) y consulta el grafo para ello."""
        motor, cazador = self._motor()
        self.assertTrue(motor.ejecutar_accion("mover", "E"))     # activa al cazador; ataca en 100
        cuenta = contar_busquedas(motor)
        movimientos = registrar_movimientos(motor)

        self.assertTrue(motor.ejecutar_accion("mover", "O"))     # jugador en 1; su turno vuelve en 200

        self.assertEqual(motor.reloj, 200)
        self.assertEqual(movimientos, [(cazador.id, "O", 1, 200)])
        self.assertGreater(cuenta[0], 0, "un cazador activo que se mueve debería consultar el grafo")

    def test_fr034_activo_sigue_activo_al_cambiar_de_sala(self):
        """T039 (FR-034): activado en 2, el jugador se va a 5 por la salida de un sentido 2 -E-> 5 (costo 600). El
        cazador recorre 3 y 4 (salas a las que el jugador nunca entró) y llega a 5, activo en todo momento."""
        motor, cazador = self._motor()
        self.assertTrue(motor.ejecutar_accion("mover", "E"))     # activa al cazador; ataca en 100
        movimientos = registrar_movimientos(motor)
        activo_al_moverse = []
        original = motor.mover_enemigo

        def mirar(enemigo, salas, salida):
            resultado = original(enemigo, salas, salida)
            activo_al_moverse.append(enemigo.activo)
            return resultado

        motor.mover_enemigo = mirar

        self.assertTrue(motor.ejecutar_accion("mover", "E"))     # jugador en 5; su turno vuelve en 700

        self.assertEqual(motor.reloj, 700)
        self.assertEqual(movimientos, [(cazador.id, "S", 3, 200), (cazador.id, "E", 4, 300),
                                       (cazador.id, "N", 5, 400)])
        self.assertEqual(activo_al_moverse, [True, True, True])
        self.assertTrue(cazador.activo)
        for id_sala in (3, 4):
            self.assertNotEqual(motor.conocimiento.estado(sala_de(motor, id_sala)), EXPLORADA,
                                f"el jugador no debería haber explorado la sala {id_sala}")
        self.assertEqual(len(turnos_pendientes(motor, cazador)), 1)


# ───────────────────────── T040 ─────────────────────────

class TestNoDependeDelContenido(unittest.TestCase):
    CICLOS = 8

    def _recorrido(self, motor):
        """(reloj, sala del cazador, tiempo_siguiente del cazador) tras cada «esperar» del jugador."""
        cazador = cazadores_de(motor)[0]
        motor.activar_enemigo(cazador)
        recorrido = []
        for _ in range(self.CICLOS):
            esperar(self, motor)
            recorrido.append((motor.reloj, cazador.sala.id, cazador.tiempo_siguiente))
        return recorrido

    def _llenar(self, motor):
        # Enemigos dormidos en salas de las dos rutas.
        agregar_enemigo(motor, "gua-1", 4, "guardian")
        agregar_enemigo(motor, "err-1", 5, "errante")
        agregar_enemigo(motor, "ras-1", 2, "rastreador")
        # Objetos en el suelo (motor.objetos_suelo: [id_sala, [nodos]], como cargar_contenido_salas).
        motor.gestor_datos.fichas.append(FichaCatalogo.desde_json({
            "id": "poc_prueba", "clase": "pocion", "nombre": "Poción", "peso": 1, "valor": 1, "cura": 5,
        }))
        motor.objetos_suelo.append([5, [motor.crear_objeto("poc-1", "poc_prueba")]])
        motor.objetos_suelo.append([6, [motor.crear_objeto("poc-2", "poc_prueba")]])
        # Trampas (motor.contenidos_salas con TrampaInstancia; la ficha la pide activar_trampas_de_sala).
        motor.gestor_datos.fichas.append(FichaCatalogo.desde_json({
            "id": "tra_prueba", "clase": "trampa", "nombre": "Pinchos", "daño": 3,
        }))
        motor.contenidos_salas.append(ContenidoSala(4, [], [TrampaInstancia("tra-1", "tra_prueba")], []))
        motor.contenidos_salas.append(ContenidoSala(6, [], [TrampaInstancia("tra-2", "tra_prueba")], []))
        # Rastro (atributo `rastro` de la sala, como actualizar_rastro).
        for id_sala in (2, 4, 5, 6):
            sala_de(motor, id_sala).rastro = 0
        # Niebla: el jugador conoce todas las salas (en el otro motor, las de la ruta nunca se vieron).
        for sala in motor.salas:
            motor.conocimiento.entrar(sala, False, motor.historial)

    def test_fr015_contenido_y_niebla_no_cambian_la_decision(self):
        """T040 (FR-015): dos motores iguales con el mapa de T034 (cazador en 1, rango 400, jugador en 3); en uno, las
        salas de las rutas tienen enemigos dormidos, objetos, trampas y rastro, y el jugador las conoce todas; en el
        otro están vacías y las salas de la ruta nunca se vieron. Durante 8 ciclos, la secuencia de salas y tiempos
        del cazador es la misma, y el cazador sí se mueve."""
        limpio = mapa_a_mano(MAPA_DOS_RUTAS, sala_jugador=3, cazadores=[(1, 400)], semilla=5)
        lleno = mapa_a_mano(MAPA_DOS_RUTAS, sala_jugador=3, cazadores=[(1, 400)], semilla=5)
        for id_sala in (2, 4, 5, 6):
            self.assertNotEqual(limpio.conocimiento.estado(sala_de(limpio, id_sala)), EXPLORADA)
        self._llenar(lleno)
        self.assertEqual(lleno.conocimiento.estado(sala_de(lleno, 5)), EXPLORADA)

        recorrido_limpio = self._recorrido(limpio)
        recorrido_lleno = self._recorrido(lleno)

        self.assertEqual(recorrido_lleno, recorrido_limpio)
        self.assertEqual([sala for _, sala, _ in recorrido_limpio[:4]], [4, 5, 6, 3],
                         "el cazador no siguió la ruta de costo 400")


# ───────────────────────── T041 ─────────────────────────

class TestVariosCazadores(unittest.TestCase):
    def test_fr018_cada_uno_decide_con_su_sala_y_su_rango(self):
        """T041 (FR-018): en el mapa de T034, con el jugador en 3: A en 1 con rango 400, B en 2 con rango 250, C en 5
        con rango 100 y D en 5 con rango 200. En t = 100: A va a 4, B a 3, C espera (d = 200 > 100) y D va a 6
        (misma sala que C, otro rango). En t = 400, A, B y D están en la sala del jugador y C sigue en 5."""
        motor = mapa_a_mano(MAPA_DOS_RUTAS, sala_jugador=3, cazadores=[(1, 400), (2, 250), (5, 100), (5, 200)])
        a, b, c, d = cazadores_de(motor)
        motor.activar_enemigos([a, b, c, d])

        esperar(self, motor)
        self.assertEqual(motor.reloj, 100)
        self.assertEqual([a.sala.id, b.sala.id, c.sala.id, d.sala.id], [4, 3, 5, 6])
        self.assertEqual([a.tiempo_siguiente, b.tiempo_siguiente, c.tiempo_siguiente, d.tiempo_siguiente],
                         [200, 350, 200, 200])

        esperar(self, motor, 3)
        self.assertEqual(motor.reloj, 400)
        self.assertTrue(motor.jugador.esta_vivo())
        self.assertEqual([a.sala.id, b.sala.id, c.sala.id, d.sala.id], [3, 3, 5, 3])


# ───────────────────────── T042 ─────────────────────────

class TestCazadorMuerto(unittest.TestCase):
    def test_fr019_turno_pendiente_se_descarta(self):
        """T042 (FR-019): cazador activo en 1 (rango 1000, jugador en 3) con turno en t = 100. Un veneno de 100 lo
        mata en t = 80; su turno de t = 100 se descarta sin efecto: no se mueve, no consulta el grafo y no vuelve a
        actuar. En un motor gemelo sin veneno, el mismo cazador sí se mueve en t = 100."""
        gemelo = mapa_a_mano(PASILLO_150, sala_jugador=3, cazadores=[(1, 1000)])
        vivo = cazadores_de(gemelo)[0]
        gemelo.activar_enemigo(vivo)
        esperar(self, gemelo)
        self.assertEqual(vivo.sala.id, 2, "en el motor gemelo el cazador vivo debería moverse")

        motor = mapa_a_mano(PASILLO_150, sala_jugador=3, cazadores=[(1, 1000)])
        cazador = cazadores_de(motor)[0]
        motor.activar_enemigo(cazador)
        motor.aplicar_veneno(cazador, 100)
        cuenta = contar_busquedas(motor)
        movimientos = registrar_movimientos(motor)
        mensajes = registrar_mensajes(motor)

        esperar(self, motor, 5)

        self.assertFalse(cazador.esta_vivo())
        self.assertEqual(cazador.sala.id, 1)
        self.assertEqual(cazador.tiempo_siguiente, 100, "no se reprogramó después de morir")
        self.assertEqual(movimientos, [])
        self.assertEqual(cuenta[0], 0)
        self.assertEqual(turnos_pendientes(motor, cazador), [])
        self.assertEqual([m for m in mensajes if cazador.id in m],
                         [f"El veneno inflige 100 de daño a {cazador.id}.", f"{cazador.id} ha muerto."])
    def test_fr019_muerto_por_el_jugador_no_vuelve_a_actuar(self):
        """T042 (FR-019): el jugador mata a un cazador en su sala y luego se aleja dentro del rango; el cazador no
        vuelve a actuar. En un motor gemelo donde no lo mata, el cazador sí lo sigue."""
        mapa = [(1, [("E", 2, 100, False)]), (2, [("O", 1, 100, False)])]

        gemelo = mapa_a_mano(mapa, sala_jugador=1, cazadores=[(1, 1000)])
        vivo = cazadores_de(gemelo)[0]
        self.assertTrue(gemelo.ejecutar_accion("mover", "E"))
        esperar(self, gemelo)
        self.assertEqual(vivo.sala.id, 2, "en el motor gemelo el cazador vivo debería seguir al jugador")

        motor = mapa_a_mano(mapa, sala_jugador=1, cazadores=[(1, 1000)])
        cazador = cazadores_de(motor)[0]
        while cazador.esta_vivo():
            self.assertTrue(motor.ejecutar_accion("atacar", cazador.id))
        self.assertTrue(motor.jugador.esta_vivo())
        movimientos = registrar_movimientos(motor)
        mensajes = registrar_mensajes(motor)

        self.assertTrue(motor.ejecutar_accion("mover", "E"))
        esperar(self, motor, 4)

        self.assertEqual(cazador.sala.id, 1)
        self.assertEqual(movimientos, [])
        self.assertEqual(turnos_pendientes(motor, cazador), [])
        self.assertEqual([m for m in mensajes if cazador.id in m], [])


# ───────────────────────── T043 ─────────────────────────

class TestMensajes(unittest.TestCase):
    MAPA = [(1, [("E", 2, 100, False)]), (2, [("O", 1, 100, False)])]

    def _normalizados(self, mensajes, id_enemigo):
        return [m.replace(id_enemigo, "<enemigo>") for m in mensajes]

    def test_fr020_al_entrar_a_la_sala_del_jugador_mismo_mensaje_que_un_errante(self):
        """T043 (FR-020): un enemigo en 2, cuya única salida lleva a la sala del jugador (1), entra en t = 100. Un
        cazador (rango 100) produce los mismos mensajes que un errante, con su id cambiado."""
        motor_errante = mapa_a_mano(self.MAPA, sala_jugador=1)
        errante = agregar_enemigo(motor_errante, "err-1", 2, "errante")
        motor_errante.activar_enemigo(errante)
        mensajes_errante = registrar_mensajes(motor_errante)
        esperar(self, motor_errante)
        self.assertEqual(errante.sala.id, 1)

        motor = mapa_a_mano(self.MAPA, sala_jugador=1, cazadores=[(2, 100)])
        cazador = cazadores_de(motor)[0]
        motor.activar_enemigo(cazador)
        mensajes = registrar_mensajes(motor)
        esperar(self, motor)

        self.assertEqual(cazador.sala.id, 1)
        self.assertEqual(self._normalizados(mensajes, cazador.id),
                         self._normalizados(mensajes_errante, errante.id))
        self.assertIn("<enemigo> entra a la sala.", self._normalizados(mensajes, cazador.id))

    def test_fr020_al_atacar_mismo_mensaje_que_un_guardian(self):
        """T043 (FR-020): un enemigo en la sala del jugador ataca en t = 100 y t = 200. Con la misma semilla y las
        mismas estadísticas (ataque 3, defensa 0), el cazador produce los mismos mensajes que un guardián, con su id
        cambiado. Se compara con el guardián porque no consume azar antes de atacar (el errante sí, al elegir
        salida), y el daño depende del azar.

        «Salir de la sala del jugador» no se prueba: por la regla 1 un cazador en la sala del jugador siempre ataca,
        y cuando se mueve, la sala que deja nunca es la del jugador. Se comprueba que nunca aparece ese mensaje."""
        motor_guardian = mapa_a_mano(self.MAPA, sala_jugador=1, semilla=3)
        guardian = agregar_enemigo(motor_guardian, "gua-1", 1, "guardian")
        motor_guardian.activar_enemigo(guardian)
        mensajes_guardian = registrar_mensajes(motor_guardian)
        esperar(self, motor_guardian, 2)

        motor = mapa_a_mano(self.MAPA, sala_jugador=1, cazadores=[(1, 0)], semilla=3)
        cazador = cazadores_de(motor)[0]
        mensajes = registrar_mensajes(motor)
        esperar(self, motor, 2)

        normalizados = self._normalizados(mensajes, cazador.id)
        self.assertEqual(normalizados, self._normalizados(mensajes_guardian, guardian.id))
        self.assertEqual(len([m for m in normalizados if m.startswith("<enemigo> ataca a")]), 2, normalizados)
        self.assertNotIn("<enemigo> sale de la sala.", normalizados)


# ───────────────────────── T044 ─────────────────────────

class TestSinAzar(unittest.TestCase):
    # Atacar no se prueba: MotorSimulacion.atacar calcula el daño con self.azar.randint(0, 4) (Parte I), así que un
    # ataque de cualquier enemigo consume azar. FR-021 se refiere a la decisión del cazador; se prueban mover y
    # esperar, que no tienen ningún componente al azar.

    def test_fr021_moverse_no_consume_azar(self):
        """T044 (FR-021): el estado de motor.azar es el mismo antes y después de un turno en que el cazador se mueve
        (el turno del jugador, «esperar», no consume azar)."""
        motor = mapa_a_mano(PASILLO_150, sala_jugador=3, cazadores=[(1, 1000)])
        cazador = cazadores_de(motor)[0]
        motor.activar_enemigo(cazador)
        antes = motor.azar.getstate()

        esperar(self, motor)

        self.assertEqual(cazador.sala.id, 2, "el cazador no se movió")
        self.assertEqual(motor.azar.getstate(), antes)

    def test_fr021_esperar_no_consume_azar(self):
        """T044 (FR-021): el estado de motor.azar es el mismo antes y después de varios turnos en que el cazador espera
        porque la distancia (250) supera su rango (200)."""
        motor = mapa_a_mano(PASILLO_150, sala_jugador=3, cazadores=[(1, 200)])
        cazador = cazadores_de(motor)[0]
        motor.activar_enemigo(cazador)
        antes = motor.azar.getstate()

        esperar(self, motor, 3)

        self.assertEqual(cazador.sala.id, 1)
        self.assertEqual(cazador.tiempo_siguiente, 400, "debería haber esperado en 100, 200 y 300")
        self.assertEqual(motor.azar.getstate(), antes)


# ───────────────────────── T045 ─────────────────────────

class TestRangoDeLaFicha(unittest.TestCase):
    def test_fr009_el_enemigo_guarda_el_rango_de_su_ficha(self):
        """T045 (FR-009): un enemigo creado con motor.crear_enemigo desde una ficha de cazador con rango R guarda
        enemigo.rango == R, incluido R = 0."""
        motor = mapa_a_mano(PASILLO_150, sala_jugador=3, cazadores=[(1, 0), (2, 250), (1, 1000)])
        self.assertEqual([c.rango for c in cazadores_de(motor)], [0, 250, 1000])

        id_ficha = motor.gestor_datos.ficha_cazador(77)
        enemigo = motor.crear_enemigo("caz-suelto", id_ficha, None, sala_de(motor, 2))
        self.assertEqual(enemigo.rango, 77)


# ═════════════════════════ Estrategias de decisión (T047, T049) ═════════════════════════
#
# Interfaz que usan estas pruebas (se llaman directamente, sin pasar por la agenda):
#   motor.decidir_cazador_individual(cazador)  -> DecisionCazador (búsqueda desde cero, T046)
#   motor.decidir_cazador_compartida(cazador)  -> DecisionCazador (campo compartido, T047)
#   motor.decidir_cazador(cazador)             -> según motor.estrategia_cazador ("individual" por defecto, o
#                                                 "compartida")
#   DecisionCazador: accion ("ATACAR", "ESPERAR", "MOVER"), salida (la Salida del motor que se cruza, o None) y
#   costo_base.
#
# Los cazadores se activan con motor.activar_enemigo antes de decidir: la cota del campo es el mayor rango entre los
# cazadores activos y vivos (data-model §5), y un cazador dormido no decide (FR-034).

def contar_entrantes(motor):
    """Reemplaza motor.grafo_cripta.entrantes por una envoltura contadora (en la instancia). Solo el campo compartido
    (búsqueda al revés) la usa; la búsqueda individual usa aristas."""
    cuenta = [0]
    grafo = motor.grafo_cripta
    original = grafo.entrantes

    def envoltura(*args, **kwargs):
        cuenta[0] += 1
        return original(*args, **kwargs)

    grafo.entrantes = envoltura
    return cuenta


def direccion_de(sala, salida):
    for direccion in sala.salidas:
        if sala.salidas[direccion] is salida:
            return direccion
    return None


def firma(motor, cazador, decision):
    """(accion, dirección de la salida en la sala del cazador o None, id de la sala destino o None, costo_base)."""
    if decision.salida is None:
        return (decision.accion, None, None, decision.costo_base)
    return (decision.accion, direccion_de(cazador.sala, decision.salida), motor._destino(decision.salida).id,
            decision.costo_base)


class ConDecision(unittest.TestCase):
    def assertMismaDecision(self, motor, cazador, una, otra, contexto=""):
        """Misma acción, la MISMA Salida (identidad) y el mismo costo_base."""
        self.assertEqual(una.accion, otra.accion, contexto)
        self.assertIs(una.salida, otra.salida, contexto)
        self.assertEqual(una.costo_base, otra.costo_base, contexto)
        self.assertEqual(firma(motor, cazador, una), firma(motor, cazador, otra), contexto)


# ───────────────────────── T049 ─────────────────────────

def mapa_de_caso(ids, aristas):
    """Salas de mapa_a_mano para un caso de DESEMPATES: cada sala lleva sus salidas en el orden de `aristas`, y las
    que no tienen ninguna van con lista vacía."""
    salas = []
    for id_sala in ids:
        salidas = [(direccion, destino, costo, False)
                   for origen, direccion, destino, costo in aristas if origen == id_sala]
        salas.append((id_sala, salidas))
    return salas


class TestTablaDeDesempates(ConDecision):
    def test_fr014_fr021_tabla_de_desempates_con_las_dos_estrategias(self):
        """T049 (FR-014, FR-021): cada caso de la tabla de desempates del contrato de 001 (DESEMPATES de
        tests/test_ruta_contrato.py), con las salidas en el orden dado y en el invertido, corre contra la decisión del
        cazador (en `origen`, rango 10**9; jugador en `destino`) con las dos estrategias. Cada una elige la dirección y
        la vecina de `esperado`, con costo_base igual al costo de esa salida, y las dos coinciden en accion, salida
        (misma Salida) y costo_base."""
        for numero, (ids, aristas, origen, destino, esperado) in enumerate(DESEMPATES):
            for orden, lista in (("dado", list(aristas)), ("invertido", invertido(aristas))):
                with self.subTest(caso=numero, orden=orden):
                    motor = mapa_a_mano(mapa_de_caso(ids, lista), sala_jugador=destino, cazadores=[(origen, 10 ** 9)])
                    cazador = cazadores_de(motor)[0]
                    motor.activar_enemigo(cazador)
                    direccion, vecina, _ = esperado

                    individual = motor.decidir_cazador_individual(cazador)
                    compartida = motor.decidir_cazador_compartida(cazador)

                    salida = cazador.sala.salidas[direccion]
                    for nombre, decision in (("individual", individual), ("compartida", compartida)):
                        self.assertEqual(decision.accion, "MOVER", nombre)
                        self.assertIs(decision.salida, salida, nombre)
                        self.assertEqual(motor._destino(decision.salida).id, vecina, nombre)
                        self.assertEqual(decision.costo_base, motor.costo_salida(salida), nombre)
                    self.assertMismaDecision(motor, cazador, individual, compartida)


# ───────────────────────── T047 ─────────────────────────

class TestCampoCompartido(ConDecision):
    # Cazadores en MAPA_DOS_RUTAS con el jugador en 3. Distancias hasta 3: d(1) = 400, d(2) = 250, d(4) = 300,
    # d(5) = 200, d(6) = 100. Hay rangos 0, iguales y menores que la distancia, y uno en la sala del jugador.
    CAZADORES_DOS_RUTAS = [(1, 400), (1, 399), (2, 0), (2, 250), (5, 100), (4, 300), (6, 99), (3, 0)]

    def _dos_rutas(self, cazadores=None):
        motor = mapa_a_mano(MAPA_DOS_RUTAS, sala_jugador=3,
                            cazadores=self.CAZADORES_DOS_RUTAS if cazadores is None else cazadores)
        lista = cazadores_de(motor)
        motor.activar_enemigos(lista)
        return motor, lista

    def _comparar_todos(self, motor, cazadores):
        acciones = []
        for cazador in cazadores:
            with self.subTest(cazador=cazador.id, sala=cazador.sala.id, rango=cazador.rango):
                individual = motor.decidir_cazador_individual(cazador)
                compartida = motor.decidir_cazador_compartida(cazador)
                self.assertMismaDecision(motor, cazador, individual, compartida)
                acciones.append(individual.accion)
        return acciones

    def test_fr016_fr018_misma_decision_en_el_mapa_de_dos_rutas(self):
        """T047 (FR-016, FR-018): en el mapa de T034, con ocho cazadores de rangos distintos (0, iguales y menores que
        la distancia, y uno en la sala del jugador), la estrategia compartida da la misma decisión que la individual
        para cada uno. Se comprueba que hay al menos un ATACAR, un ESPERAR y un MOVER."""
        motor, cazadores = self._dos_rutas()
        acciones = self._comparar_todos(motor, cazadores)
        self.assertIn("ATACAR", acciones)
        self.assertIn("ESPERAR", acciones)
        self.assertIn("MOVER", acciones)

    def test_fr016_fr018_misma_decision_en_cripta_con_puertas_cerradas_al_azar(self):
        """T047 (FR-016, FR-018): en criptas de cripta_terreno con costos variados y puertas cerradas al azar
        (random.Random local con semilla fija, cerrando con motor._escribir_cerrada después de armar el motor), con
        cazadores de rangos 0, 60, 150, 300, 700 y 10**6 en salas distintas, las dos estrategias coinciden."""
        movimientos = 0
        esperas = 0
        for semilla in (3, 17, 29):
            cripta = cripta_terreno(semilla, 40, variacion=60)
            azar = random.Random(semilla * 7 + 1)
            salas_cazadores = [azar.randrange(2, 41) for _ in range(6)]
            rangos = [0, 60, 150, 300, 700, 10 ** 6]
            motor = armar_motor(cripta, 1, list(zip(salas_cazadores, rangos)))
            for sala in motor.salas:
                for direccion in sala.salidas:
                    salida = sala.salidas[direccion]
                    if not salida.cerrada and azar.random() < 0.25:
                        motor._escribir_cerrada(salida, True)
            cazadores = cazadores_de(motor)
            motor.activar_enemigos(cazadores)
            with self.subTest(semilla=semilla):
                acciones = self._comparar_todos(motor, cazadores)
                movimientos += acciones.count("MOVER")
                esperas += acciones.count("ESPERAR")
        self.assertGreater(movimientos, 0, "ningún cazador se movió: la prueba no compara pasos")
        self.assertGreater(esperas, 0, "ningún cazador esperó: la prueba no compara esperas")

    def test_fr033_un_campo_por_ciclo(self):
        """T047 (FR-033): con cuatro cazadores y el motor en un mismo ciclo, la primera decisión compartida consulta
        motor.grafo_cripta.entrantes y las tres siguientes no la vuelven a consultar."""
        motor, cazadores = self._dos_rutas([(1, 400), (5, 100), (4, 300), (2, 250)])
        cuenta = contar_entrantes(motor)

        motor.decidir_cazador_compartida(cazadores[0])
        primera = cuenta[0]
        self.assertGreater(primera, 0, "la primera decisión compartida no calculó el campo")

        for cazador in cazadores[1:]:
            motor.decidir_cazador_compartida(cazador)
        self.assertEqual(cuenta[0], primera, "se recalculó el campo dentro del mismo ciclo")

    def test_fr016_nuevo_ciclo_recalcula(self):
        """T047 (FR-016): tras motor.ejecutar_accion("esperar", None) empieza otro ciclo y la siguiente decisión
        compartida vuelve a consultar entrantes; la decisión coincide con la individual."""
        motor, cazadores = self._dos_rutas([(1, 400), (5, 100)])
        cazador = cazadores[0]
        cuenta = contar_entrantes(motor)
        motor.decidir_cazador_compartida(cazador)
        antes = cuenta[0]
        ciclo = motor.ciclo

        esperar(self, motor)                        # el cazador de 1 pasa a 4; sigue lejos del jugador

        self.assertGreater(motor.ciclo, ciclo)
        cuenta_tras_turnos = cuenta[0]
        compartida = motor.decidir_cazador_compartida(cazador)
        self.assertGreater(cuenta[0], max(antes, cuenta_tras_turnos), "no se recalculó en el ciclo nuevo")
        self.assertMismaDecision(motor, cazador, motor.decidir_cazador_individual(cazador), compartida)

    def test_fr016_cambio_de_puerta_en_el_mismo_ciclo_recalcula(self):
        """T047 (FR-016): dentro de un mismo ciclo, cerrar la puerta 6 -N-> 3 (fuera de la sala del cazador) con
        motor._escribir_cerrada invalida el campo: la cuenta de entrantes crece y el cazador de 1 (rango 400) pasa de
        MOVER hacia 4 a ESPERAR (la única ruta que queda cuesta 500). Al reabrirla vuelve a MOVER hacia 4."""
        motor, cazadores = self._dos_rutas([(1, 400), (5, 100)])
        cazador = cazadores[0]
        puerta = sala_de(motor, 6).salidas["N"]
        cuenta = contar_entrantes(motor)

        antes = motor.decidir_cazador_compartida(cazador)
        self.assertEqual(firma(motor, cazador, antes), ("MOVER", "S", 4, 100))
        calculos = cuenta[0]

        motor._escribir_cerrada(puerta, True)
        cerrada = motor.decidir_cazador_compartida(cazador)
        self.assertGreater(cuenta[0], calculos, "no se recalculó tras cerrar una puerta")
        self.assertEqual(firma(motor, cazador, cerrada), ("ESPERAR", None, None, 100))
        self.assertMismaDecision(motor, cazador, motor.decidir_cazador_individual(cazador), cerrada)
        calculos = cuenta[0]

        motor._escribir_cerrada(puerta, False)
        abierta = motor.decidir_cazador_compartida(cazador)
        self.assertGreater(cuenta[0], calculos, "no se recalculó tras abrir la puerta")
        self.assertEqual(firma(motor, cazador, abierta), ("MOVER", "S", 4, 100))

    def test_fr016_rango_mayor_que_la_cota_fuerza_recalculo(self):
        """T047 (FR-016): el campo se calcula decidiendo con el único cazador activo, en 5 con rango 100 (cota 100).
        Luego se activa otro, en 1 con rango 400, que necesita ver hasta 400: la decisión compartida recalcula y da
        la misma decisión que la individual (MOVER hacia 4)."""
        motor = mapa_a_mano(MAPA_DOS_RUTAS, sala_jugador=3, cazadores=[(5, 100), (1, 400)])
        pequeno, grande = cazadores_de(motor)
        motor.activar_enemigo(pequeno)
        cuenta = contar_entrantes(motor)

        motor.decidir_cazador_compartida(pequeno)
        calculos = cuenta[0]
        motor.activar_enemigo(grande)
        compartida = motor.decidir_cazador_compartida(grande)

        self.assertGreater(cuenta[0], calculos, "un rango mayor que la cota no forzó el recálculo")
        individual = motor.decidir_cazador_individual(grande)
        self.assertEqual(firma(motor, grande, individual), ("MOVER", "S", 4, 100))
        self.assertMismaDecision(motor, grande, individual, compartida)

    def test_fr033_busqueda_individual_intercalada_no_deja_campo_viejo(self):
        """T047 (FR-033): una búsqueda individual reutiliza el espacio del motor; la siguiente decisión compartida no
        lee un campo pisado. Con el mismo cazador: compartida, individual y compartida coinciden. Con otro cazador en
        medio (en 5, cuya búsqueda adelante deja vigentes otras salas): la segunda compartida del primero sigue igual."""
        motor, cazadores = self._dos_rutas([(1, 400), (5, 1000)])
        primero, otro = cazadores

        with self.subTest(caso="mismo cazador"):
            una = motor.decidir_cazador_compartida(primero)
            individual = motor.decidir_cazador_individual(primero)
            otra = motor.decidir_cazador_compartida(primero)
            self.assertMismaDecision(motor, primero, una, individual)
            self.assertMismaDecision(motor, primero, individual, otra)

        with self.subTest(caso="otro cazador en medio"):
            una = motor.decidir_cazador_compartida(primero)
            motor.decidir_cazador_individual(otro)
            otra = motor.decidir_cazador_compartida(primero)
            self.assertMismaDecision(motor, primero, una, otra)
            self.assertEqual(firma(motor, primero, otra), ("MOVER", "S", 4, 100))
    def test_fr016_puerta_escrita_sin_el_metodo_unico_se_ve_al_empezar_otro_ciclo(self):
        """T047 (FR-016): la carga de partida escribe `Salida.cerrada` sin pasar por _escribir_cerrada, así que
        version_puertas no cambia. Lo que protege al campo en ese caso es `ciclo`: con la puerta de 6 -N-> 3 cerrada
        directamente y otro ciclo empezado (ciclo + 1, sin mover a nadie), la decisión compartida refleja la puerta y
        coincide con la individual, que siempre lee el estado en vivo."""
        motor, cazadores = self._dos_rutas([(1, 400), (5, 100)])
        cazador = cazadores[0]
        puerta = sala_de(motor, 6).salidas["N"]

        antes = motor.decidir_cazador_compartida(cazador)
        self.assertEqual(firma(motor, cazador, antes), ("MOVER", "S", 4, 100))
        version = motor.version_puertas

        puerta.cerrada = True
        self.assertEqual(motor.version_puertas, version, "escribir cerrada a mano no debería tocar version_puertas")
        motor.ciclo += 1

        despues = motor.decidir_cazador_compartida(cazador)
        self.assertEqual(firma(motor, cazador, despues), ("ESPERAR", None, None, 100))
        self.assertMismaDecision(motor, cazador, motor.decidir_cazador_individual(cazador), despues)

    def test_fr016_otra_sala_del_jugador_recalcula_el_campo(self):
        """T047 (FR-016): el campo es hacia la sala del jugador con que se calculó. Si el jugador aparece en otra sala
        (aquí se le cambia la sala directamente, sin empezar otro ciclo ni cambiar una puerta), la decisión compartida
        recalcula: desde 1, con el jugador en 2 la salida E cuesta 250 y es la mejor; con el jugador en 3 era S."""
        motor, cazadores = self._dos_rutas([(1, 1000)])
        cazador = cazadores[0]

        antes = motor.decidir_cazador_compartida(cazador)
        self.assertEqual(firma(motor, cazador, antes), ("MOVER", "S", 4, 100))

        motor.jugador.sala = sala_de(motor, 2)

        despues = motor.decidir_cazador_compartida(cazador)
        self.assertEqual(firma(motor, cazador, despues), ("MOVER", "E", 2, 250))
        self.assertMismaDecision(motor, cazador, motor.decidir_cazador_individual(cazador), despues)
    def test_fr016_despacho_segun_estrategia(self):
        """T047, T048 (FR-016): por defecto motor.estrategia_cazador es "individual" y decidir_cazador no consulta
        entrantes; con "compartida", decidir_cazador sí la consulta y da la misma decisión."""
        motor, cazadores = self._dos_rutas([(1, 400), (5, 100)])
        cazador = cazadores[0]
        cuenta = contar_entrantes(motor)

        self.assertEqual(motor.estrategia_cazador, "individual")
        por_defecto = motor.decidir_cazador(cazador)
        self.assertEqual(cuenta[0], 0, "la estrategia individual consultó entrantes")

        motor.estrategia_cazador = "compartida"
        compartida = motor.decidir_cazador(cazador)
        self.assertGreater(cuenta[0], 0, "con estrategia compartida no se consultó entrantes")
        self.assertMismaDecision(motor, cazador, por_defecto, compartida)


# ═════════════════════════ US3: el cazador espera cuando no hay ruta (T050 a T054) ═════════════════════════

# ───────────────────────── T050 ─────────────────────────

class TestSinRutaAbierta(unittest.TestCase):
    def test_fr012_fr017_apendice_b_sin_ruta_abierta(self):
        """T050. Apéndice B, «sin ruta abierta»; escenario 1 de la US3 (FR-012, FR-017): las dos rutas del cazador (en
        1, rango 10**6) al jugador (en 3) pasan por puertas cerradas (2 -E-> 3 y 4 -E-> 3). El cazador espera con
        costo 100 turno tras turno, y ninguna puerta cambia: el estado `cerrada` de cada salida y
        motor.version_puertas son los mismos antes y después."""
        motor = mapa_a_mano([
            (1, [("E", 2, 100, False), ("S", 4, 100, False)]),
            (2, [("E", 3, 100, True), ("O", 1, 100, False)]),
            (3, []),
            (4, [("E", 3, 100, True), ("N", 1, 100, False)]),
        ], sala_jugador=3, cazadores=[(1, 10 ** 6)])
        cazador = cazadores_de(motor)[0]
        puertas = [(sala.id, d, sala.salidas[d].cerrada) for sala in motor.salas for d in sala.salidas]
        version = motor.version_puertas
        motor.activar_enemigo(cazador)

        for turno in range(1, 4):
            esperar(self, motor)
            self.assertEqual(cazador.sala.id, 1)
            self.assertEqual(cazador.tiempo_siguiente, 100 * (turno + 1))

        self.assertEqual([(sala.id, d, sala.salidas[d].cerrada) for sala in motor.salas for d in sala.salidas],
                         puertas)
        self.assertEqual(motor.version_puertas, version)


# ───────────────────────── T051 ─────────────────────────

class TestRutaMasCaraQueElRango(unittest.TestCase):
    MAPA = [
        (1, [("E", 2, 300, False)]),
        (2, [("E", 3, 300, False)]),
        (3, []),
    ]

    def test_fr012_apendice_b_ruta_mas_barata_cuesta_mas_que_el_rango(self):
        """T051. Apéndice B, «ruta más barata cuesta más que el rango»; escenario 2 de la US3 (FR-012): la única ruta
        cuesta 600 y el rango es 500; el cazador espera con costo 100 turno tras turno."""
        motor = mapa_a_mano(self.MAPA, sala_jugador=3, cazadores=[(1, 500)])
        cazador = cazadores_de(motor)[0]
        motor.activar_enemigo(cazador)

        esperar(self, motor)
        self.assertEqual(cazador.sala.id, 1)
        self.assertEqual(cazador.tiempo_siguiente, 200)
        esperar(self, motor)
        self.assertEqual(cazador.sala.id, 1)
        self.assertEqual(cazador.tiempo_siguiente, 300)

    def test_fr012_contraste_con_rango_600_se_mueve(self):
        """T051, contraste (FR-012): con la misma ruta de 600 y rango 600, el cazador se mueve a 2 (salida de costo
        300; siguiente turno en 400)."""
        motor = mapa_a_mano(self.MAPA, sala_jugador=3, cazadores=[(1, 600)])
        cazador = cazadores_de(motor)[0]
        motor.activar_enemigo(cazador)

        esperar(self, motor)

        self.assertEqual(cazador.sala.id, 2)
        self.assertEqual(cazador.tiempo_siguiente, 400)


# ───────────────────────── T052 ─────────────────────────

class TestPuertaQueSeAbre(unittest.TestCase):
    # 1 -E(100)-> 2 -E(400)-> 3 cuesta 500; 1 -S(100)-> 4 -E(100, cerrada)-> 3 cuesta 200 cuando se abre.
    MAPA = [
        (1, [("E", 2, 100, False), ("S", 4, 100, False)]),
        (2, [("E", 3, 400, False)]),
        (3, []),
        (4, [("E", 3, 100, True)]),
    ]

    def _esperando(self, rango):
        motor = mapa_a_mano(self.MAPA, sala_jugador=3, cazadores=[(1, rango)])
        cazador = cazadores_de(motor)[0]
        motor.activar_enemigo(cazador)
        esperar(self, motor)                                      # t = 100: espera (500 > rango)
        self.assertEqual(cazador.sala.id, 1)
        self.assertEqual(cazador.tiempo_siguiente, 200)
        motor._escribir_cerrada(sala_de(motor, 4).salidas["E"], False)   # entre sus turnos de 100 y 200
        esperar(self, motor)                                      # t = 200: vuelve a decidir
        return cazador

    def test_fr016_persigue_cuando_la_puerta_se_abre_y_la_ruta_cabe_en_el_rango(self):
        """T052. Escenario 3 de la US3 (FR-016): con rango 300, el cazador espera en t = 100 (la ruta abierta cuesta
        500); la puerta 4 -E-> 3 se abre antes de su turno de t = 200, la ruta nueva cuesta 200 ≤ 300 y en t = 200 va
        a 4 (costo 100, siguiente turno en 300)."""
        cazador = self._esperando(300)
        self.assertEqual(cazador.sala.id, 4)
        self.assertEqual(cazador.tiempo_siguiente, 300)

    def test_fr016_la_puerta_se_abre_pero_la_ruta_supera_el_rango(self):
        """T052, variante (FR-016): con rango 150, la ruta nueva de 200 también supera el rango; tras abrirse la
        puerta, el cazador sigue esperando con costo 100."""
        cazador = self._esperando(150)
        self.assertEqual(cazador.sala.id, 1)
        self.assertEqual(cazador.tiempo_siguiente, 300)


# ───────────────────────── T053 ─────────────────────────

class TestRangoCero(unittest.TestCase):
    def test_fr012_rango_cero_en_otra_sala_espera(self):
        """T053. Escenario 4 de la US3 (FR-012): un cazador con rango 0 en una sala vecina a la del jugador (salida de
        costo 1) espera con costo 100 turno tras turno."""
        motor = mapa_a_mano([(1, [("E", 2, 1, False)]), (2, [("O", 1, 1, False)])], sala_jugador=2,
                            cazadores=[(1, 0)])
        cazador = cazadores_de(motor)[0]
        motor.activar_enemigo(cazador)

        for turno in range(1, 4):
            esperar(self, motor)
            self.assertEqual(cazador.sala.id, 1)
            self.assertEqual(cazador.tiempo_siguiente, 100 * (turno + 1))


# ───────────────────────── T054 ─────────────────────────

class TestNoUsaLlaves(unittest.TestCase):
    # mapa_a_mano no deja poner llave en una salida (solo dirección, destino, costo y cerrada). Se usa cripta_terreno
    # con una llave: en generar_cripta, la sala de salida (la última) es la única de su región y TODAS las puertas que
    # entran a ella están cerradas y piden detalles.llave_salida (Salida.llave). El jugador empieza en la sala de
    # salida; el cazador porta esa llave en su botín (FichaEnemigo con "suelta", como los enemigos que sueltan llaves
    # en la Parte I) y su única forma de llegar es por una de esas puertas.

    def test_fr017_porta_la_llave_y_no_abre(self):
        """T054 (FR-017): un cazador (rango 10**6) que porta en su botín la llave de las puertas cerradas que entran a
        la sala del jugador no las abre ni las usa: espera con costo 100 turno tras turno, las puertas siguen
        cerradas, motor.version_puertas no cambia y la llave sigue en su botín."""
        cripta = cripta_terreno(5, 12)
        salida_id = cripta.detalles.sala_salida
        llave = cripta.detalles.llave_salida
        motor = armar_motor(cripta, salida_id, [])

        puertas = [sala.salidas[d] for sala in motor.salas for d in sala.salidas
                   if motor._destino(sala.salidas[d]).id == salida_id]
        self.assertTrue(puertas, "la sala de salida no tiene puertas de entrada")
        for puerta in puertas:
            self.assertTrue(puerta.cerrada)
            self.assertEqual(puerta.llave, llave)
        origen = None
        for sala in motor.salas:
            for d in sala.salidas:
                if sala.salidas[d] in puertas:
                    origen = sala
        self.assertIsNotNone(origen)

        gestor = motor.gestor_datos
        gestor.fichas.append(FichaCatalogo.desde_json({
            "id": llave, "clase": "llave", "nombre": "Llave de salida", "peso": 1, "valor": 1, "abre": llave,
        }))
        datos = dict(CAZADOR)
        datos.update({"id": "ent_cazador_llave", "rango": 10 ** 6, "suelta": [llave]})
        gestor.fichas.append(FichaEnemigo.desde_json(datos))
        cazador = motor.crear_enemigo("caz-llave", "ent_cazador_llave", None, origen)
        motor.registrar_enemigo(cazador)
        self.assertEqual([(n.tipo_id, n.clase) for n in cazador.botin], [(llave, "llave")])

        version = motor.version_puertas
        motor.activar_enemigo(cazador)
        for turno in range(1, 4):
            esperar(self, motor)
            self.assertIs(cazador.sala, origen)
            self.assertEqual(cazador.tiempo_siguiente, 100 * (turno + 1))

        self.assertTrue(all(puerta.cerrada for puerta in puertas))
        self.assertEqual(motor.version_puertas, version)
        self.assertEqual([n.tipo_id for n in cazador.botin], [llave])


if __name__ == "__main__":
    unittest.main()
