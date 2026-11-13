# Cantidad de pergaminos por instante (spec 004, T044; Escenario US2-8; Quickstart 7; FR-029; research R6). Sin red.

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.LineaTiempo import SeriePergaminos
from tests.test_linea_consulta import contenido
from tests.utiles_linea import huella, partida_con_linea


def pergaminos_mostrados(resumen):
    for nombre, cantidad in resumen.inventario:
        if nombre.startswith("Pergamino"):  # el nombre sale del catálogo (o «Pergamino de retroceso» si el clon no tiene uno)
            return cantidad
    return 0


class PruebasSerieDePergaminos(unittest.TestCase):

    def test_fr029_registrar_solo_agrega_si_la_cuenta_cambio(self):
        serie = SeriePergaminos(3)
        serie.registrar(1, 3)
        serie.registrar(2, 3)
        self.assertEqual((serie.serie_clave, serie.serie_cantidad), ([], []))
        serie.registrar(4, 2)
        serie.registrar(4, 1)          # dos cambios en la misma acción: se actualiza, la serie sigue creciendo estrictamente
        serie.registrar(6, 5)
        self.assertEqual((serie.serie_clave, serie.serie_cantidad), ([4, 6], [1, 5]))
        self.assertEqual(serie.ultima(), 5)

    def test_fr029_en_devuelve_la_ultima_clave_menor_o_igual_o_la_inicial(self):
        serie = SeriePergaminos(3)
        serie.registrar(4, 2)
        serie.registrar(7, 4)
        self.assertEqual([serie.en(c) for c in (0, 3, 4, 5, 6, 7, 99)], [3, 3, 2, 2, 2, 4, 4])

    def test_fr029_plegar_saca_las_claves_posteriores_y_agrega_solo_si_difiere(self):
        serie = SeriePergaminos(3)
        for clave, cantidad in ((2, 4), (5, 3), (8, 2)):
            serie.registrar(clave, cantidad)
        serie.plegar(6, 3)             # saca la clave 8; la cantidad vigente (3) es la de la clave 5: no agrega
        self.assertEqual((serie.serie_clave, serie.serie_cantidad), ([2, 5], [4, 3]))
        serie.plegar(6, 1)             # difiere: agrega (6, 1)
        self.assertEqual((serie.serie_clave, serie.serie_cantidad), ([2, 5, 6], [4, 3, 1]))
        serie.plegar(2, 4)             # saca 5 y 6; la cantidad en 2 ya es 4: no agrega
        self.assertEqual((serie.serie_clave, serie.serie_cantidad), ([2], [4]))
        serie.plegar(2, 0)             # misma clave que el último registro: lo actualiza
        self.assertEqual((serie.serie_clave, serie.serie_cantidad), ([2], [0]))
        serie.plegar(0, 3)             # saca todo; vuelve a la cantidad inicial: no agrega
        self.assertEqual((serie.serie_clave, serie.serie_cantidad), ([], []))

    def test_fr029_la_serie_es_estrictamente_creciente_con_cualquier_secuencia(self):
        serie = SeriePergaminos(0)
        pasos = [("r", 1, 1), ("r", 2, 2), ("p", 1, 1), ("r", 2, 0), ("r", 3, 3), ("p", 2, 0), ("r", 5, 2), ("p", 4, 2)]
        for tipo, clave, cantidad in pasos:
            serie.registrar(clave, cantidad) if tipo == "r" else serie.plegar(clave, cantidad)
            claves = serie.serie_clave
            for anterior, siguiente in zip(claves, claves[1:]):
                self.assertLess(anterior, siguiente)
            self.assertEqual(len(claves), len(serie.serie_cantidad))


class PruebasPergaminosPorInstante(unittest.TestCase):

    def test_us2_8_tres_pergaminos_se_gastan_dos_y_el_pasado_muestra_tres(self):
        pl = partida_con_linea(k=3, pergaminos=3, efectos=False)
        self.addCleanup(pl.cerrar)
        linea, motor = pl.linea, pl.motor
        pl.hacer([("esperar", ""), ("mover", "S"), ("esperar", ""), ("mover", "E")])
        reloj_t = linea.vig_reloj[2]                 # una decisión previa a los retrocesos
        self.assertEqual(pergaminos_mostrados(linea.consultar_instante(reloj_t, motor)), 3)
        self.assertTrue(pl.retroceder())
        self.assertTrue(pl.retroceder())
        self.assertEqual(linea.acciones, 2)
        self.assertEqual(sum(1 for n in motor.jugador.inventario if n.clase == "pergamino_retroceso"), 1)

        # antes de la posición a la que se retrocedió: lo que el jugador tenía entonces (3)
        self.assertEqual(pergaminos_mostrados(linea.consultar_accion(1, motor)), 3)
        self.assertEqual(pergaminos_mostrados(linea.consultar_accion(2, motor)), 3)
        self.assertEqual(pergaminos_mostrados(linea.consultar_instante(0, motor)), 3)
        entre = linea.vig_reloj[1] - 1
        self.assertEqual(pergaminos_mostrados(linea.consultar_instante(entre, motor)), 3)
        # en la posición a la que se retrocedió (#3) rige la última ocurrencia: el presente (1)
        self.assertEqual(pergaminos_mostrados(linea.consultar_accion(3, motor)), 1)
        self.assertEqual(pergaminos_mostrados(linea.consultar_instante(linea.reloj_actual, motor)), 1)
        # la cantidad real sigue siendo la actual
        self.assertEqual(sum(1 for n in motor.jugador.inventario if n.clase == "pergamino_retroceso"), 1)
        self.assertEqual(linea.serie_clave, [2])
        self.assertEqual(linea.serie_cantidad, [1])
        self.assertLessEqual(linea.serie_clave[-1], linea.acciones)

    def test_us2_8_el_pergamino_recogido_aparece_desde_su_accion(self):
        from tests.utiles_niebla import contenido_sala
        pl = partida_con_linea(k=3, pergaminos=0, efectos=False, contenido=[contenido_sala(1, objetos=("itm_pergamino",))])
        self.addCleanup(pl.cerrar)
        linea, motor = pl.linea, pl.motor
        id_p = motor.obtener_objetos_suelo(motor.jugador.sala)[0].instancia_id
        pl.hacer([("esperar", ""), ("esperar", ""), ("recoger", id_p), ("esperar", ""), ("esperar", "")])
        self.assertEqual(linea.serie_clave, [3])
        self.assertEqual(linea.serie_cantidad, [1])
        self.assertEqual([pergaminos_mostrados(linea.consultar_accion(k, motor)) for k in range(1, 7)],
                         [0, 0, 0, 1, 1, 1])
        # durante la acción 3 (recoger) ya se ve el pergamino; en su decisión, todavía no
        d3 = linea.vig_reloj[2]
        self.assertEqual(pergaminos_mostrados(linea.consultar_instante(d3, motor)), 0)
        self.assertEqual(pergaminos_mostrados(linea.consultar_instante(d3 + 1, motor)), 1)

    def test_us2_8_el_resumen_usa_la_serie_y_no_la_del_clon(self):
        """Tras un retroceso el clon rehace solo las acciones vigentes; la cantidad sale de la serie, no del clon."""
        pl = partida_con_linea(k=3, pergaminos=2, efectos=False)
        self.addCleanup(pl.cerrar)
        linea, motor = pl.linea, pl.motor
        pl.hacer([("esperar", ""), ("esperar", ""), ("esperar", "")])
        self.assertTrue(pl.retroceder())
        clon = linea.clon_antes_de(2, motor)
        try:
            en_el_clon = sum(1 for n in clon.jugador.inventario if n.clase == "pergamino_retroceso")
        finally:
            linea._soltar_clon()
        self.assertEqual(en_el_clon, 2)
        self.assertEqual(pergaminos_mostrados(linea.consultar_accion(2, motor)), 2)
        self.assertEqual(contenido(linea.consultar_accion(linea.acciones + 1, motor)), huella(motor))


class PruebasNombreDelPergamino(unittest.TestCase):
    """El resumen muestra el pergamino con el mismo nombre que el inventario vivo (``nodo.nombre``, como `_texto_nodo` de la
    vista), no con una constante cuando el clon no tiene uno."""

    def test_us2_8_el_nombre_es_el_del_nodo_vivo_y_se_conserva_aunque_el_clon_no_tenga_pergamino(self):
        from tests.utiles_niebla import contenido_sala
        from Vista.VistaConsola import VistaConsola
        from Modelo.ResumenHistorico import resumir
        pl = partida_con_linea(k=3, pergaminos=0, efectos=False, contenido=[contenido_sala(1, objetos=("itm_pergamino",))])
        self.addCleanup(pl.cerrar)
        linea, motor = pl.linea, pl.motor
        suelo = motor.obtener_objetos_suelo(motor.jugador.sala)[0]
        nombre_vivo = suelo.nombre
        self.assertEqual(nombre_vivo, "Pergamino")  # el del catálogo de prueba, no la constante del resumen
        pl.hacer([("esperar", ""), ("recoger", suelo.instancia_id), ("esperar", "")])
        self.assertEqual(linea.serie.nombre, nombre_vivo)
        # así lo muestra el inventario vivo
        self.assertTrue(VistaConsola()._texto_nodo(next(iter(motor.jugador.inventario))).startswith(nombre_vivo))
        for k in (3, 4):
            resumen = linea.consultar_accion(k, motor)
            self.assertIn((nombre_vivo, 1), resumen.inventario)
        # un clon sin pergamino (el motor de la partida antes de recoger) con la cantidad de la serie usa el mismo nombre
        clon = linea.clon_antes_de(2, motor)
        try:
            self.assertEqual(sum(1 for n in clon.jugador.inventario if n.clase == "pergamino_retroceso"), 0)
            resumen = resumir(clon, 1, ("instante", 1), pergaminos=2, nombre_pergamino=linea.serie.nombre)
        finally:
            linea._soltar_clon()
        self.assertIn((nombre_vivo, 2), resumen.inventario)
        # sin nombre conocido (la línea nunca vio un pergamino), la constante
        clon = linea.clon_antes_de(2, motor)
        try:
            sin_nombre = resumir(clon, 1, ("instante", 1), pergaminos=2)
        finally:
            linea._soltar_clon()
        self.assertIn(("Pergamino de retroceso", 2), sin_nombre.inventario)


if __name__ == "__main__":
    unittest.main()
