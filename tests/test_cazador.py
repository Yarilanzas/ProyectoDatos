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

import unittest

from DTOS.ContenidoSala import ContenidoSala
from DTOS.FichaCatalogo import FichaCatalogo, FichaEnemigo
from DTOS.TrampaInstancia import TrampaInstancia
from Modelo.Conocimiento import EXPLORADA
from tests.utiles_terreno import CAZADOR, ID_JUGADOR, mapa_a_mano


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


if __name__ == "__main__":
    unittest.main()
