# Pruebas de la copia estructurada del estado (spec 004, T012, T015 y T016; Quickstart 12).
# Atiende: FR-017, FR-021, FR-008, PR-02. Sin red: criptas sintéticas y paquetes offline temporales.
#
# Escenarios con partidas por ControladorPartida.nueva_partida: usan la cripta de utiles_linea (SALAS_LINEA), que es
# resoluble, así que no hace falta `forzar=True` (FR-021 de la spec 002).

import copy
import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.CopiaEstado import (CAMPOS_MUTABLES_SALA, CAMPOS_MUTABLES_SALIDA, copiar, foto_cerradas, foto_rastros,
                                materializar)
from Modelo.Inventario import Inventario, NodoInventario
from Modelo.PuntoControl import SIN_RASTRO, PuntoControl
from Modelo.retroceso import Historial
from tests.utiles_linea import (GeneradorAcciones, agregar_cazador, agregar_enemigo, jugar, partida_linea,
                                preparar_motor_linea, resumen_ampliado)
from tests.utiles_terreno import armar_motor, cripta_terreno


def motor_sintetico(salas, semilla=1, espiar=False):
    """Motor sin red sobre una cripta sintética de `salas` salas, ya convertido en MotorLinea."""
    motor = armar_motor(cripta_terreno(semilla, salas), sala_jugador=1, cazadores=[], semilla=semilla)
    return preparar_motor_linea(motor, espiar=espiar)


def deepcopy_completo(motor):
    """`deepcopy` del motor entero, solo sin su gestor ni su restaurador (no son estado de la partida)."""
    memo = {}
    for colaborador in (motor.gestor_datos, motor.restaurador):
        if colaborador is not None:
            memo[id(colaborador)] = None
    return copy.deepcopy(motor, memo)


def nodo(numero, clase="objeto"):
    return NodoInventario(f"obj-{numero}", "itm_x", f"Objeto {numero}", 1, 1, clase)


def inventario_largo(cantidad):
    inventario = Inventario(cantidad + 10)
    for numero in range(cantidad):
        inventario.recoge(nodo(numero, "arma" if numero == 3 else "objeto"))
    # cursor en medio y un arma equipada: los cinco punteros del inventario deben re-ligarse
    for _ in range(cantidad // 2):
        inventario.avanza()
    return inventario


def ids_inventario(inventario):
    return [n.instancia_id for n in inventario]


class PruebasOraculoDeLaCopia(unittest.TestCase):
    """T012: la copia estructurada frente a `deepcopy` completo del motor (FR-017, FR-021, FR-008)."""

    def test_fr017_copia_estructurada_igual_a_deepcopy_completo_hasta_60_salas(self):
        for salas in (20, 60):
            with self.subTest(salas=salas):
                motor = motor_sintetico(salas, semilla=salas)
                gestor = motor.gestor_datos
                generador = GeneradorAcciones(salas)
                for _ in range(4):
                    jugar(motor, generador, 7)
                    esperado = resumen_ampliado(deepcopy_completo(motor))
                    clon = materializar(copiar(motor), gestor)
                    self.assertEqual(resumen_ampliado(clon), esperado)
                    self.assertEqual(resumen_ampliado(clon), resumen_ampliado(motor))

    def test_fr017_con_muchas_salas_la_estructurada_funciona_y_deepcopy_completo_no(self):
        """Medido sobre main (GrafoCripta de A incluido) con cripta_terreno: `deepcopy` completo del motor aún funciona con
        200 salas y lanza RecursionError desde unas 400. Se prueba con 200 (la estructurada funciona) y con 600 (además
        `deepcopy` completo falla). La spec decía «200»: esa cifra era de una exploración previa, otra topología."""
        for salas in (200, 600):
            with self.subTest(salas=salas):
                motor = motor_sintetico(salas, semilla=5)
                gestor = motor.gestor_datos
                jugar(motor, GeneradorAcciones(5), 15)
                clon = materializar(copiar(motor), gestor)
                self.assertEqual(resumen_ampliado(clon), resumen_ampliado(motor))
                if salas >= 600:
                    with self.assertRaises(RecursionError):
                        copy.deepcopy(motor)

    def test_fr021_el_clon_sigue_igual_que_el_vivo_al_rehacer_las_mismas_acciones(self):
        motor = motor_sintetico(20, semilla=3, espiar=True)
        gestor = motor.gestor_datos
        generador = GeneradorAcciones(11)
        jugar(motor, generador, 10)
        clon = materializar(copiar(motor), gestor)
        for nombre, argumento in jugar(motor, generador, 15):
            self.assertTrue(clon.ejecutar_accion(nombre, argumento))
        self.assertEqual(resumen_ampliado(clon), resumen_ampliado(motor))

    def test_fr008_materializar_y_consultar_no_cambian_el_motor_vivo(self):
        motor = motor_sintetico(20, semilla=4)
        gestor = motor.gestor_datos
        jugar(motor, GeneradorAcciones(4), 12)
        antes = resumen_ampliado(motor)
        rastros = foto_rastros(motor)
        cerradas = foto_cerradas(motor)
        # una sala nunca visitada: «puede no existir» el atributo rastro
        sin_rastro = [s for s in motor.salas if not hasattr(s, "rastro")]
        self.assertTrue(sin_rastro, "la prueba necesita una sala nunca visitada")

        punto = copiar(motor)
        clon = materializar(punto, gestor)
        jugar(clon, GeneradorAcciones(99), 20)  # el clon juega y cambia sus puertas y rastros

        self.assertEqual(resumen_ampliado(motor), antes)
        self.assertEqual(foto_rastros(motor), rastros)
        self.assertEqual(foto_cerradas(motor), cerradas)
        for sala in sin_rastro:
            self.assertFalse(hasattr(sala, "rastro"), "el clon creó `rastro` en una sala del vivo")

    def test_fr017_constantes_de_campos_mutables(self):
        from Modelo import CopiaEstado
        self.assertEqual(CAMPOS_MUTABLES_SALA, ("rastro",))
        self.assertEqual(CAMPOS_MUTABLES_SALIDA, ("cerrada",))
        # constante: la fija Salida.__init__ y copy.copy la conserva; no se fotografía
        self.assertNotIn("cerrada_en_esqueleto", CAMPOS_MUTABLES_SALIDA)
        self.assertNotIn("cerrada_en_esqueleto", CAMPOS_MUTABLES_SALA)
        self.assertTrue(hasattr(CopiaEstado, "materializar"))

    def test_fr017_historial_gestor_y_restaurador_del_clon(self):
        motor = motor_sintetico(20, semilla=6)
        jugar(motor, GeneradorAcciones(6), 8)
        class GestorMinimo:
            estado_juego = None

            def conectar_estado_juego(self, estado):
                self.estado_juego = estado

        historico = GestorMinimo()
        abiertas = []

        def abrir_copia(ruta):
            abiertas.append(ruta)
            return ("restaurador de la época", ruta)

        clon = materializar(copiar(motor), historico, abrir_copia, "copia.cripta")
        self.assertIsInstance(clon.historial, Historial)
        self.assertFalse(clon.historial.puede_deshacer())
        self.assertIsNot(clon.historial, motor.historial)
        self.assertIs(clon.gestor_datos, historico)
        self.assertIs(historico.estado_juego, clon)
        self.assertEqual(clon.restaurador, ("restaurador de la época", "copia.cripta"))
        self.assertEqual(abiertas, ["copia.cripta"])
        # sin copia privada, el clon no hereda el restaurador del vivo
        motor.restaurador = object()
        self.assertIsNone(materializar(copiar(motor), historico).restaurador)
        self.assertIsNone(copiar(motor).estado.restaurador)
        self.assertIsNone(copiar(motor).estado.gestor_datos)

    def test_fr021_oraculo_con_eventos_pendientes_y_azar(self):
        """El oráculo incluye REARMAR_TRAMPA, VENENO, FIN_VELOCIDAD, APAGAR_ANTORCHA y un enemigo «errante», que sí
        consume `azar` (`salida_errante` usa `azar.choice`). Hay una acción que consume azar en el juego."""
        partida = partida_linea(espiar=True)
        self.addCleanup(partida.cerrar)
        motor = partida.motor
        gestor = partida.nuevo_gestor()
        agregar_enemigo(motor, "err-001", 6, "errante")
        generador = GeneradorAcciones(21)

        self.assertTrue(motor.ejecutar_accion("mover", "E"))
        self.assertTrue(motor.ejecutar_accion("mover", "S"))  # sala 5: dispara la trampa y programa REARMAR_TRAMPA
        motor.aplicar_veneno(motor.jugador, 2)
        motor.aplicar_velocidad_temporal(motor.jugador, 10, 600)
        motor.jugador.antorcha_encendida = True
        motor.programar_evento(motor.reloj + 450, "APAGAR_ANTORCHA", motor.jugador)

        tipos = [ev.tipo for ev in motor.agenda.heap if not ev.cancelado]
        for esperado in ("REARMAR_TRAMPA", "VENENO", "FIN_VELOCIDAD", "APAGAR_ANTORCHA"):
            self.assertIn(esperado, tipos)

        azar_inicial = motor.azar.getstate()
        for _ in range(5):
            punto = copiar(motor)
            esperado = resumen_ampliado(deepcopy_completo(motor))
            self.assertEqual(resumen_ampliado(materializar(punto, gestor)), esperado)
            jugar(motor, generador, 4)
        self.assertNotEqual(motor.azar.getstate(), azar_inicial, "ninguna acción consumió azar: el oráculo no lo prueba")


class PruebasInventarioLargo(unittest.TestCase):
    """T015 y T016 (g): copiar y materializar con inventarios largos, sin recursión (T003 midió RecursionError desde 165)."""

    def _motor_con_inventario(self, cantidad):
        motor = motor_sintetico(20, semilla=2)
        motor.jugador.inventario = inventario_largo(cantidad)
        motor.jugador.inventario._arma_equipada = next(n for n in motor.jugador.inventario if n.clase == "arma")
        return motor

    def _comprobar_copia(self, original, copia):
        self.assertEqual(ids_inventario(copia), ids_inventario(original))
        self.assertEqual(copia._cantidad, original._cantidad)
        self.assertEqual(copia._cursor.instancia_id, original._cursor.instancia_id)
        self.assertEqual(copia._arma_equipada.instancia_id, original._arma_equipada.instancia_id)
        self.assertEqual(copia._cola.instancia_id, original._cola.instancia_id)
        nodos_originales = list(original)
        for propio, ajeno in zip(copia, nodos_originales):
            self.assertIsNot(propio, ajeno, "la copia comparte un nodo con el original")
        # todos los punteros apuntan a nodos de la copia
        propios = list(copia)
        for puntero in (copia._cabeza, copia._cola, copia._cursor, copia._arma_equipada):
            self.assertTrue(any(puntero is n for n in propios))
        # y los enlaces dobles están bien
        for izquierda, derecha in zip(propios, propios[1:]):
            self.assertIs(izquierda.siguiente, derecha)
            self.assertIs(derecha.anterior, izquierda)
        # leerla hacia atrás desde la cola recorre lo mismo
        atras = []
        actual = copia._cola
        while actual is not None:
            atras.append(actual.instancia_id)
            actual = actual.anterior
        self.assertEqual(atras, list(reversed(ids_inventario(original))))

    def test_fr017_copiar_inventarios_de_200_y_400_nodos(self):
        for cantidad in (200, 400):
            with self.subTest(nodos=cantidad):
                motor = self._motor_con_inventario(cantidad)
                punto = copiar(motor)
                self._comprobar_copia(motor.jugador.inventario, punto.estado.jugador.inventario)

    def test_fr017_materializar_inventarios_de_200_y_400_nodos(self):
        for cantidad in (200, 400):
            with self.subTest(nodos=cantidad):
                motor = self._motor_con_inventario(cantidad)
                clon = materializar(copiar(motor), motor.gestor_datos)
                self._comprobar_copia(motor.jugador.inventario, clon.jugador.inventario)
                # el clon tiene sus propios nodos también frente al punto de control
                punto = copiar(motor)
                clon2 = materializar(punto, motor.gestor_datos)
                for propio, del_punto in zip(clon2.jugador.inventario, punto.estado.jugador.inventario):
                    self.assertIsNot(propio, del_punto)


class PruebasFotoYPuntoDeControl(unittest.TestCase):

    def test_fr017_el_punto_guarda_el_sello_y_la_foto(self):
        motor = motor_sintetico(20, semilla=8)
        jugar(motor, GeneradorAcciones(8), 6)
        punto = copiar(motor, epoca=2)
        self.assertIsInstance(punto, PuntoControl)
        self.assertEqual(punto.accion, motor.acciones_jugador)
        self.assertEqual((punto.reloj, punto.secuencia), (motor.reloj, motor.secuencia))
        self.assertEqual(punto.epoca, 2)
        self.assertEqual(len(punto.foto_rastros), len(motor.salas))
        self.assertEqual(len(punto.foto_cerradas), sum(len(s.salidas) for s in motor.salas))
        self.assertIn(SIN_RASTRO, punto.foto_rastros)
        self.assertEqual(copiar(motor, accion=99).accion, 99)

    def test_fr017_ciclo_y_version_puertas_viajan_en_el_punto_y_no_se_comparan(self):
        motor = motor_sintetico(20, semilla=9)
        jugar(motor, GeneradorAcciones(9), 10)
        punto = copiar(motor)
        self.assertEqual((punto.estado.ciclo, punto.estado.version_puertas), (motor.ciclo, motor.version_puertas))
        clon = materializar(punto, motor.gestor_datos)
        self.assertEqual((clon.ciclo, clon.version_puertas), (motor.ciclo, motor.version_puertas))
        # solo crecen: el clon no los baja; jugar más los sube en el clon y no en el vivo
        ciclo_vivo, version_viva = motor.ciclo, motor.version_puertas
        jugar(clon, GeneradorAcciones(1), 10)
        self.assertGreater(clon.ciclo, ciclo_vivo)
        self.assertEqual((motor.ciclo, motor.version_puertas), (ciclo_vivo, version_viva))

    def test_fr017_grafo_y_espacio_de_busqueda_del_clon_son_propios_y_apuntan_al_clon(self):
        motor = motor_sintetico(20, semilla=10)
        jugar(motor, GeneradorAcciones(10), 5)
        clon = materializar(copiar(motor), motor.gestor_datos)
        self.assertIsNot(clon.grafo_cripta, motor.grafo_cripta)
        self.assertIsNot(clon.espacio_busqueda, motor.espacio_busqueda)
        self.assertIs(clon.grafo_cripta._destino_de.__self__, clon)
        self.assertIs(clon.grafo_cripta._costo_de.__self__, clon)
        propias = [s for s in clon.salas]
        for sala in clon.salas:
            for _direccion, origen, _costo in clon.grafo_cripta.entrantes(sala):
                self.assertTrue(any(origen is p for p in propias), "el grafo del clon apunta a una sala del vivo")
            for _direccion, destino, _costo in clon.grafo_cripta.aristas(sala):
                self.assertTrue(any(destino is p for p in propias), "el grafo del clon apunta a una sala del vivo")
        # las puertas del clon se leen en vivo: cerrar una en el clon no cambia las aristas del vivo
        sala = clon.salas[0]
        antes_vivo = len(motor.grafo_cripta.aristas(motor.salas[0]))
        for salida in sala.salidas.values():
            salida.cerrada = True
        self.assertEqual(len(clon.grafo_cripta.aristas(sala)), 0)
        self.assertEqual(len(motor.grafo_cripta.aristas(motor.salas[0])), antes_vivo)


class PruebasMaterializarEnPartidaReal(unittest.TestCase):
    """T016: clones de una partida creada por ControladorPartida.nueva_partida (cripta resoluble)."""

    def setUp(self):
        self.partida = partida_linea(espiar=True)
        self.addCleanup(self.partida.cerrar)
        self.motor = self.partida.motor

    def test_fr017_a_clon_sobre_sala_con_trampa_con_gestor_historico(self):
        """Sin gestor el clon lanza RuntimeError al entrar en la sala con trampa; con gestor_historico juega.
        La sala 5 ya está cargada en el vivo y su trampa ya se rearmó: el clon la dispara otra vez."""
        for accion in (("mover", "E"), ("mover", "S"), ("mover", "N")):
            self.assertTrue(self.motor.ejecutar_accion(*accion))
        for _ in range(4):
            self.assertTrue(self.motor.ejecutar_accion("esperar"))
        self.assertTrue(self.motor.contenido_disponible(5))
        punto = copiar(self.motor)

        sin_gestor = materializar(punto, None)
        with self.assertRaisesRegex(RuntimeError, "No hay gestor de datos para consultar la ficha de la trampa."):
            sin_gestor.ejecutar_accion("mover", "S")

        clon = materializar(punto, self.partida.nuevo_gestor())
        vida = clon.jugador.vida
        self.assertTrue(clon.ejecutar_accion("mover", "S"))
        self.assertEqual(clon.jugador.sala.id, 5)
        self.assertLess(clon.jugador.vida, vida)  # la trampa disparó

        # el vivo no se enteró
        self.assertEqual(self.motor.jugador.sala.id, 2)

    def test_fr017_b_sala_sin_contenido_cargado_se_resuelve_desde_el_disco(self):
        self.assertFalse(self.motor.contenido_disponible(2))
        punto = copiar(self.motor)
        sin_gestor = materializar(punto, None)
        self.assertFalse(sin_gestor.ejecutar_accion("mover", "E"))
        self.assertIn("El contenido de esa sala aún no está disponible.", sin_gestor.mensajes.ultimos())

        clon = materializar(punto, self.partida.nuevo_gestor())
        self.assertTrue(clon.ejecutar_accion("mover", "E"))
        self.assertTrue(clon.contenido_disponible(2))
        self.assertFalse(self.motor.contenido_disponible(2), "el clon cargó una sala en el vivo")

    def test_fr017_c_cerrar_puerta_pendiente_no_cierra_la_del_vivo(self):
        salida_viva = self.motor.salas[0].salidas["E"]
        self.assertFalse(salida_viva.cerrada)
        self.motor.programar_evento(self.motor.reloj + 150, "CERRAR_PUERTA", salida_viva)
        clon = materializar(copiar(self.motor), self.partida.nuevo_gestor())
        evento = next(ev for ev in clon.agenda.heap if ev.tipo == "CERRAR_PUERTA")
        self.assertIsNot(evento.actor, salida_viva, "el evento del clon apunta a la salida del vivo")
        self.assertIs(evento.actor, clon.salas[0].salidas["E"])

        self.assertTrue(clon.ejecutar_accion("esperar"))
        self.assertTrue(clon.ejecutar_accion("esperar"))
        self.assertTrue(clon.salas[0].salidas["E"].cerrada)
        self.assertFalse(salida_viva.cerrada, "el clon cerró la puerta del motor vivo")

    def test_fr008_d_eco_es_false_en_el_clon_aunque_el_vivo_tenga_eco(self):
        self.motor.eco = True
        clon = materializar(copiar(self.motor), self.partida.nuevo_gestor())
        self.assertFalse(clon.eco)
        self.assertTrue(self.motor.eco)

    def test_fr008_e_un_solo_clon_vivo_por_gestor_historico(self):
        gestor = self.partida.nuevo_gestor()
        punto = copiar(self.motor)
        primero = materializar(punto, gestor)
        self.assertIs(gestor.estado_juego, primero)
        segundo = materializar(punto, gestor)
        self.assertIs(gestor.estado_juego, segundo)
        self.assertIsNot(primero, segundo)

    def test_fr008_f_sala_sin_atributo_rastro_el_clon_no_lo_crea(self):
        sin_rastro = [s.id for s in self.motor.salas if not hasattr(s, "rastro")]
        self.assertIn(6, sin_rastro)
        punto = copiar(self.motor)
        self.assertIn(SIN_RASTRO, punto.foto_rastros)
        # el vivo la visita después de la foto: el clon sigue sin el atributo
        self.assertTrue(self.motor.ejecutar_accion("mover", "E"))
        clon = materializar(punto, self.partida.nuevo_gestor())
        for sala in clon.salas:
            if sala.id in sin_rastro:
                self.assertFalse(hasattr(sala, "rastro"), f"el clon creó rastro en la sala {sala.id}")
        self.assertTrue(hasattr(self.motor.salas[1], "rastro"))

    def test_fr017_g_el_clon_tiene_sus_propias_salas_y_salidas(self):
        clon = materializar(copiar(self.motor), self.partida.nuevo_gestor())
        for sala_viva, sala_clon in zip(self.motor.salas, clon.salas):
            self.assertIsNot(sala_viva, sala_clon)
            self.assertIsNot(sala_viva.salidas, sala_clon.salidas)
            for direccion in sala_viva.salidas:
                self.assertIsNot(sala_viva.salidas[direccion], sala_clon.salidas[direccion])
        self.assertIs(clon._indice_origen, clon.salas)
        self.assertIs(clon.jugador.sala, clon.salas[0])
        for enemigo in clon.enemigos:
            self.assertTrue(any(enemigo.sala is s for s in clon.salas))

    def test_fr025_el_cazador_doble_decide_igual_en_el_clon(self):
        agregar_cazador(self.motor, "caz-001", 6)
        jugar(self.motor, GeneradorAcciones(31), 6)
        clon = materializar(copiar(self.motor), self.partida.nuevo_gestor())
        antes = len(self.motor.decisiones_cazador)
        self.assertEqual(clon.decisiones_cazador, self.motor.decisiones_cazador)
        self.assertIsNot(clon.decisiones_cazador, self.motor.decisiones_cazador)
        generador = GeneradorAcciones(32)
        for nombre, argumento in jugar(self.motor, generador, 12):
            self.assertTrue(clon.ejecutar_accion(nombre, argumento))
        self.assertEqual(clon.decisiones_cazador, self.motor.decisiones_cazador)
        self.assertEqual(resumen_ampliado(clon), resumen_ampliado(self.motor))
        self.assertGreaterEqual(len(self.motor.decisiones_cazador), antes)


if __name__ == "__main__":
    unittest.main()
