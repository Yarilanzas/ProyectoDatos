# La línea describe la historia tal como quedó tras usar pergaminos (spec 004, Historia 2; T037 a T042 y T045; Quickstart 5 y 6).
# Atiende: FR-004, FR-005, FR-014, FR-015, FR-016, FR-029. Sin red: cripta resoluble creada por
# ControladorPartida.nueva_partida. La referencia de «una partida que nunca hizo las acciones revertidas» es una partida
# gemela (misma semilla) que juega solo las acciones vigentes, con su propio motor espía.

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.LineaTiempo import ErrorReconstruccion, ReferenciaInvalida, TIPO_ACCION, TIPO_RETROCESO
from tests.test_linea_consulta import contenido, esperado_en
from tests.utiles_linea import huella, partida_con_linea, partida_linea
from tests.utiles_niebla import contenido_sala

ACC = [("esperar", ""), ("mover", "S"), ("esperar", ""), ("mover", "E"), ("esperar", ""), ("mover", "O")]


def sin_inventario(lineas):
    """Las líneas del resumen sin la del inventario: la cantidad de pergaminos es lo único que difiere de la gemela."""
    return [linea for linea in lineas if not linea.startswith("Inventario")]


def armar(pergaminos=2, **opciones):
    pl = partida_con_linea(k=3, pergaminos=pergaminos, **opciones)
    return pl


def acciones_vigentes(linea):
    return [(linea.guion_nombre[p], linea.guion_argumento[p]) for p in linea.vig_guion]


class BaseRetroceso(unittest.TestCase):

    def partida(self, pergaminos=2, **opciones):
        pl = armar(pergaminos, **opciones)
        self.addCleanup(pl.cerrar)
        return pl

    def comprobar_igual_a_la_gemela(self, pl, gemela, paso=13):
        """Todo `t` y todo `#k` de `pl` coincide con el de la gemela (salvo la línea del inventario)."""
        linea, motor, otra = pl.linea, pl.motor, gemela.motor
        self.assertEqual(linea.reloj_actual, gemela.linea.reloj_actual)
        self.assertEqual(linea.acciones, gemela.linea.acciones)
        instantes = set(range(0, linea.reloj_actual + 1, paso))
        instantes.update(reloj for reloj, _ in otra.instantaneas if reloj <= linea.reloj_actual)
        instantes.update(reloj for reloj, _ in otra.decisiones)
        for t in sorted(instantes):
            with self.subTest(t=t):
                resumen = linea.consultar_instante(t, motor)
                if t == linea.reloj_actual:
                    esperado = huella(otra)
                else:
                    esperado = esperado_en(otra, t)
                self.assertEqual(sin_inventario(contenido(resumen)), sin_inventario(esperado))
        for k in range(1, linea.acciones + 2):
            with self.subTest(k=k):
                resumen = linea.consultar_accion(k, motor)
                esperado = huella(otra) if k == linea.acciones + 1 else otra.decisiones[k - 1][1]
                self.assertEqual(sin_inventario(contenido(resumen)), sin_inventario(esperado))


class PruebasUnPergamino(BaseRetroceso):

    def setUp(self):
        self.pl = self.partida(pergaminos=2)
        self.assertEqual(self.pl.hacer(ACC), 6)
        self.reloj_antes = self.pl.linea.reloj_actual
        self.assertTrue(self.pl.retroceder())
        self.gemela = self.partida(pergaminos=2)
        self.assertEqual(self.gemela.hacer(ACC[:5]), 5)

    def test_us2_1_historia_numeral_6_es_el_estado_actual_y_numeral_7_se_rechaza(self):
        linea, motor = self.pl.linea, self.pl.motor
        self.assertEqual(linea.acciones, 5)
        actual = linea.consultar_accion(6, motor)
        self.assertEqual(actual.referencia, ("actual", None))
        self.assertEqual(contenido(actual), huella(motor))
        # sin reflejar la acción revertida (mover O): el jugador sigue en la sala 5
        self.assertEqual(actual.sala[0], 5)
        with self.assertRaises(ReferenciaInvalida):
            linea.consultar_accion(7, motor)
        self.assertEqual(sin_inventario(contenido(actual)), sin_inventario(huella(self.gemela.motor)))

    def test_us2_2_t_igual_al_reloj_anterior_a_revertir_se_rechaza(self):
        linea, motor = self.pl.linea, self.pl.motor
        self.assertLess(linea.reloj_actual, self.reloj_antes)
        with self.assertRaises(ReferenciaInvalida):
            linea.consultar_instante(self.reloj_antes, motor)
        with self.assertRaises(ReferenciaInvalida):
            linea.consultar_instante(linea.reloj_actual + 1, motor)

    def test_us2_2_para_todo_t_el_resumen_no_refleja_la_accion_revertida(self):
        self.comprobar_igual_a_la_gemela(self.pl, self.gemela)

    def test_us2_3_una_accion_distinta_tras_el_pergamino_se_ve_y_la_revertida_no(self):
        pl, gemela = self.pl, self.gemela
        nueva = [("esperar", "")]
        pl.hacer(nueva)
        gemela.hacer(nueva)
        self.assertEqual(acciones_vigentes(pl.linea), ACC[:5] + nueva)
        self.assertEqual(pl.linea.acciones, 6)
        # la numeración es la de la historia vigente: #6 es la acción nueva
        posicion = pl.linea.vig_guion[5]
        self.assertEqual((pl.linea.guion_nombre[posicion], pl.linea.guion_tipo[posicion]), ("esperar", TIPO_ACCION))
        self.comprobar_igual_a_la_gemela(pl, gemela)
        # un instante posterior al punto de retroceso refleja la acción nueva (esperar: el jugador sigue en la sala 5)
        despues = pl.linea.consultar_instante(pl.linea.reloj_actual - 1, pl.motor)
        self.assertEqual(despues.sala[0], 5)

    def test_us2_4_el_guion_conserva_lo_revertido_y_la_historia_vigente_no(self):
        linea = self.pl.linea
        self.assertEqual(linea.guion_tipo, [TIPO_ACCION] * 6 + [TIPO_RETROCESO])
        self.assertEqual(linea.guion_reloj[-1], 5)  # las acciones vigentes que quedan
        self.assertEqual(acciones_vigentes(linea), ACC[:5])


class PruebasPergaminoRecogido(BaseRetroceso):
    """Caso de R5: el pergamino P se recoge en la acción 7 y se usa otro (Q); P sigue en el inventario."""

    def test_us2_4_p_sigue_en_el_inventario_y_la_accion_nueva_soltar_p_se_reconstruye(self):
        pl = self.partida(pergaminos=1, contenido=[contenido_sala(1, objetos=("itm_pergamino",))])
        motor = pl.motor
        suelo = motor.obtener_objetos_suelo(motor.jugador.sala)
        self.assertEqual(len(suelo), 1)
        id_p = suelo[0].instancia_id
        self.assertEqual(pl.hacer([("esperar", "")] * 6), 6)
        self.assertEqual(pl.hacer([("recoger", id_p)]), 1)        # acción 7
        self.assertEqual(pl.linea.acciones, 7)
        self.assertEqual(pl.linea.serie.ultima(), 2)               # Q y P
        self.assertTrue(pl.retroceder())                           # se usa Q: revierte «recoger» salvo P
        self.assertEqual(pl.linea.acciones, 6)
        self.assertEqual([n.instancia_id for n in motor.jugador.inventario], [id_p], "P debía seguir en el inventario")
        self.assertEqual(pl.linea.serie.ultima(), 1)
        # la acción 8 nueva es «soltar P»
        self.assertEqual(pl.hacer([("soltar", id_p)]), 1)
        linea = pl.linea
        self.assertEqual(linea.acciones, 7)
        # el estado reconstruido antes de la decisión 8 coincide con el real (el punto de control en 6 es del motor real)
        clon = linea.clon_antes_de(8, motor)
        try:
            self.assertEqual(huella(clon), huella(motor))
            self.assertEqual([n.instancia_id for n in clon.jugador.inventario], [])
        finally:
            linea._soltar_clon()
        # y antes de soltar, P estaba en el inventario del clon
        clon = linea.clon_antes_de(7, motor)
        try:
            self.assertEqual([n.instancia_id for n in clon.jugador.inventario], [id_p])
        finally:
            linea._soltar_clon()
        # sin el punto de control del motor real en 6, el clon no tendría P: el punto se reemplazó, no se dejó el anterior
        indice = linea.pc_accion.index(6)
        self.assertEqual([n.instancia_id for n in linea.pc_punto[indice].estado.jugador.inventario], [id_p])


class PruebasCincoPergaminosSeguidos(BaseRetroceso):

    def setUp(self):
        self.pl = self.partida(pergaminos=6, inventario_max=10, efectos=False)
        self.acciones = [("esperar", ""), ("mover", "S"), ("esperar", ""), ("mover", "E"), ("esperar", ""),
                         ("mover", "O"), ("esperar", ""), ("mover", "N"), ("esperar", ""), ("esperar", "")]
        self.assertEqual(self.pl.hacer(self.acciones), 10)
        for _ in range(5):
            self.assertTrue(self.pl.retroceder())

    def test_us2_5_quedan_cinco_acciones_numeral_6_es_el_actual_y_numeral_7_se_rechaza(self):
        linea, motor = self.pl.linea, self.pl.motor
        self.assertEqual(linea.acciones, 5)
        self.assertEqual(motor.acciones_jugador, 5)
        self.assertEqual(linea.consultar_accion(6, motor).referencia, ("actual", None))
        for k in range(7, 12):
            with self.assertRaises(ReferenciaInvalida):
                linea.consultar_accion(k, motor)
        self.assertEqual(acciones_vigentes(linea), self.acciones[:5])

    def test_us2_5_la_historia_vigente_es_la_de_una_partida_que_solo_hizo_cinco_acciones(self):
        gemela = self.partida(pergaminos=6, inventario_max=10, efectos=False)
        gemela.hacer(self.acciones[:5])
        self.comprobar_igual_a_la_gemela(self.pl, gemela, paso=29)

    def test_us2_6_un_sexto_retroceder_no_revierte_nada_y_la_linea_no_cambia(self):
        linea, motor = self.pl.linea, self.pl.motor

        def foto():
            return (list(linea.guion_tipo), list(linea.guion_nombre), list(linea.guion_argumento),
                    list(linea.guion_reloj), list(linea.guion_secuencia), list(linea.vig_guion),
                    list(linea.vig_reloj), list(linea.vig_sec), list(linea.pc_accion), list(linea.pc_reloj),
                    list(linea.serie_clave), list(linea.serie_cantidad), linea.reloj_actual)

        antes = foto()
        pergaminos = sum(1 for n in motor.jugador.inventario)
        reloj, acciones = motor.reloj, motor.acciones_jugador
        self.assertFalse(self.pl.retroceder(), "el sexto retroceder debía rechazarse (como en la Parte I)")
        self.assertEqual(foto(), antes)
        self.assertEqual((motor.reloj, motor.acciones_jugador), (reloj, acciones))
        self.assertEqual(sum(1 for n in motor.jugador.inventario), pergaminos, "se gastó un pergamino sin revertir")


class PruebasIntervalosDescartados(BaseRetroceso):

    def test_fr015_tras_un_retroceso_no_quedan_acciones_ni_puntos_huerfanos(self):
        pl = self.partida(pergaminos=3)
        linea, motor = pl.linea, pl.motor
        pl.hacer(ACC)
        self.assertEqual(linea.pc_accion, [0, 3, 6])
        self.assertTrue(pl.retroceder())
        self.assertTrue(pl.retroceder())   # quedan 4
        nuevo_n = linea.acciones
        self.assertEqual(nuevo_n, 4)
        for accion in linea.pc_accion:
            self.assertLessEqual(accion, nuevo_n)
        self.assertEqual(linea.pc_accion, sorted(linea.pc_accion))
        self.assertEqual(linea.pc_accion[-1], nuevo_n, "falta el punto del motor real en nuevo_n")
        self.assertEqual(len(linea.vig_guion), nuevo_n)
        self.assertEqual(len(linea.vig_reloj), nuevo_n)
        self.assertEqual(len(linea.vig_sec), nuevo_n)
        self.assertEqual(linea.pc_punto[-1].accion, nuevo_n)
        self.assertEqual((linea.pc_punto[-1].reloj, linea.pc_punto[-1].secuencia), linea.sello_de(nuevo_n + 1))
        # el sello de la decisión actual es el del motor ya retrocedido
        self.assertEqual((motor.reloj, motor.secuencia), linea.sello_de(nuevo_n + 1))

    def test_fr016_consultar_accion_acciones_mas_uno_es_igual_al_motor_vivo(self):
        """La prueba que detecta una mutación no reportada a `historial.registrar`: tras cada paso (acciones, retrocesos y
        acciones nuevas) el estado reconstruido antes de la decisión actual es igual al del motor real."""
        pl = self.partida(pergaminos=3)
        linea, motor = pl.linea, pl.motor

        def comprobar():
            clon = linea.clon_antes_de(linea.acciones + 1, motor)
            try:
                self.assertEqual(huella(clon), huella(motor))
                self.assertEqual(sin_inventario(huella(clon)), sin_inventario(contenido(
                    linea.consultar_accion(linea.acciones + 1, motor))))
            finally:
                linea._soltar_clon()

        pasos = [("hacer", ACC[:4]), ("retroceder", None), ("hacer", [("esperar", ""), ("mover", "E")]),
                 ("retroceder", None), ("retroceder", None), ("hacer", ACC[2:6])]
        for paso, argumento in pasos:
            if paso == "hacer":
                pl.hacer(argumento)
            else:
                self.assertTrue(pl.retroceder())
            with self.subTest(paso=paso, acciones=linea.acciones):
                comprobar()

    def test_fr016_cota_de_puntos_de_control(self):
        """C <= ceil(n / K) + 1 + L + P con L = 0 cargas y P usos del pergamino."""
        pl = self.partida(pergaminos=4)
        linea = pl.linea
        usos = 0
        for lote in (ACC, ACC[:3], ACC[1:4]):
            pl.hacer(lote)
            if pl.retroceder():
                usos += 1
        n, k = linea.acciones, linea.k
        self.assertLessEqual(linea.cantidad_puntos, -(-n // k) + 1 + usos)

    def test_fr014_registrar_accion_rechaza_retroceder(self):
        pl = self.partida(pergaminos=1)
        with self.assertRaises(ValueError):
            pl.linea.registrar_accion(pl.motor, "retroceder", "")

    def test_fr015_un_retroceso_imposible_en_la_linea_es_un_error_de_reconstruccion(self):
        pl = self.partida(pergaminos=1)
        pl.hacer(ACC[:2])
        pl.motor.acciones_jugador = 99  # el motor dice que hay más acciones que antes: no es un retroceso
        with self.assertRaises(ErrorReconstruccion):
            pl.linea.registrar_retroceso(pl.motor)


if __name__ == "__main__":
    unittest.main()
