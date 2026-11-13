# Texto del resumen histórico (spec 004, T025; contracts/comandos-historia.md#salida-resumen-histórico-fr-006).
# Atiende: FR-006, FR-007. La función de módulo se llama sin instanciar `VistaConsola` (salvo para comparar el bloque del
# mapa con el del comando `mapa`). Sin red.

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from DTOS.MapaConocido import MapaConocido, SalaConocida, SalidaConocida
from DTOS.ResumenHistorico import ResumenHistorico
from Modelo.ResumenHistorico import resumir
from Vista import TextoResumen
from Vista.TextoResumen import lineas_mapa, lineas_resumen, texto_resumen
from Vista.VistaConsola import VistaConsola
from tests.utiles_linea import partida_con_linea

MAPA = MapaConocido(
    [SalaConocida(1, "Entrada", [SalidaConocida("E", 2, 100, "abierta")]),
     SalaConocida(2, "Pasillo", [SalidaConocida("O", 1, 100, "abierta"), SalidaConocida("E", 3, 250, "sin observar")])],
    [3])


def dto(referencia=("instante", 250), reloj=250, **cambios):
    campos = dict(sala=(2, "Pasillo"), vida=34, vida_max=40, ataque=6, defensa=1, velocidad=100, arma="Daga oxidada",
                  armadura=None, inventario=(("Daga oxidada", 1), ("Antorcha", 1), ("Pergamino de retroceso", 2)),
                  efectos=(("VENENO", (2, 80, 400)), ("APAGAR_ANTORCHA", (None,))),
                  enemigos=(("e-rata-1", "ent_rata", 8, 8),), mapa=MAPA, resultado=None)
    campos.update(cambios)
    return ResumenHistorico(referencia, reloj, **campos)


class PruebasTextoDelResumen(unittest.TestCase):

    def test_fr006_el_ejemplo_del_contrato(self):
        self.assertEqual(lineas_resumen(dto()), [
            "Historia — instante 250",
            "Sala 2: Pasillo",
            "Vida: 34/40   Ataque: 6   Defensa: 1   Velocidad: 100",
            "Equipo: arma Daga oxidada; armadura —",
            "Inventario (4): Daga oxidada, Antorcha, Pergamino de retroceso x2",
            "Efectos: veneno (2 de daño cada 80, hasta 400); antorcha encendida",
            "Enemigos en la sala: e-rata-1 (8/8)",
            "Mapa conocido:",
            "  Sala 1: Entrada",
            "    E -> sala 2   costo 100   abierta",
            "  Sala 2: Pasillo",
            "    O -> sala 1   costo 100   abierta",
            "    E -> sala 3   costo 250   sin observar",
            "Avistadas: 3",
        ])

    def test_fr006_las_cuatro_primeras_lineas_segun_la_referencia(self):
        self.assertEqual(lineas_resumen(dto(("instante", 250), 250))[0], "Historia — instante 250")
        self.assertEqual(lineas_resumen(dto(("accion", 3), 200))[0], "Historia — antes de la acción 3 (reloj 200)")
        self.assertEqual(lineas_resumen(dto(("actual", None), 700))[0], "Historia — estado actual (reloj 700)")
        self.assertEqual(lineas_resumen(dto(("final", None), 810))[0], "Historia — estado final (reloj 810)")
        with self.assertRaises(ValueError):
            lineas_resumen(dto(("rara", 1)))

    def test_fr006_sin_efectos_ni_enemigos(self):
        lineas = lineas_resumen(dto(efectos=(), enemigos=()))
        self.assertIn("Efectos: ninguno", lineas)
        self.assertIn("Enemigos en la sala: ninguno", lineas)

    def test_fr006_otros_efectos_y_sin_equipo_ni_inventario(self):
        lineas = lineas_resumen(dto(efectos=(("FIN_VELOCIDAD", (10, 300)), ("FIN_VELOCIDAD", (-20, 480))),
                                    arma=None, armadura="Cota", inventario=()))
        self.assertIn("Efectos: velocidad +10 (hasta 300); velocidad -20 (hasta 480)", lineas)
        self.assertIn("Equipo: arma —; armadura Cota", lineas)
        self.assertIn("Inventario (0): ninguno", lineas)

    def test_fr006_el_bloque_del_mapa_es_igual_al_del_comando_mapa(self):
        mostradas = []
        VistaConsola(salida=mostradas.append).mostrar_mapa(MAPA)
        self.assertEqual(lineas_mapa(MAPA), mostradas)
        lineas = lineas_resumen(dto())
        self.assertEqual(lineas[lineas.index("Mapa conocido:"):], mostradas)
        sin_mapa = MapaConocido([], [])
        mostradas.clear()
        VistaConsola(salida=mostradas.append).mostrar_mapa(sin_mapa)
        self.assertEqual(lineas_mapa(sin_mapa), mostradas)
        self.assertEqual(mostradas[-1], "Avistadas: ninguna")

    def test_fr006_resultado_solo_en_un_final_terminado(self):
        self.assertNotIn("Resultado", texto_resumen(dto()))
        self.assertTrue(texto_resumen(dto(("final", None), 810, resultado="victoria")).endswith("Resultado: victoria"))
        self.assertTrue(texto_resumen(dto(("final", None), 810, resultado="derrota")).endswith("Resultado: derrota"))

    def test_fr007_texto_resumen_es_las_lineas_unidas(self):
        self.assertEqual(texto_resumen(dto()), "\n".join(lineas_resumen(dto())))

    def test_fr006_es_una_funcion_de_modulo_y_no_instancia_la_vista(self):
        self.assertTrue(callable(TextoResumen.texto_resumen))
        with open(TextoResumen.__file__, encoding="utf-8") as archivo:
            importaciones = [linea for linea in archivo.read().splitlines()
                             if linea.startswith(("import ", "from "))]
        self.assertTrue(importaciones)
        for linea in importaciones:
            self.assertNotIn("VistaConsola", linea)
            self.assertNotIn("Modelo", linea, "el texto no tiene reglas de juego")
            self.assertNotIn("Controlador", linea)

    def test_fr007_el_dto_es_de_solo_lectura(self):
        resumen = dto()
        with self.assertRaises(AttributeError):
            resumen.vida = 1
        with self.assertRaises(AttributeError):
            resumen.nuevo = 1
        self.assertIsInstance(resumen.inventario, tuple)
        self.assertIsInstance(resumen.efectos, tuple)
        self.assertIsInstance(resumen.enemigos, tuple)


class PruebasResumenDesdeElMotor(unittest.TestCase):

    def setUp(self):
        self.pl = partida_con_linea(k=3)
        self.addCleanup(self.pl.cerrar)
        self.pl.jugar(hasta_reloj=500)
        self.motor = self.pl.motor

    def test_fr006_el_reloj_mostrado_es_el_consultado_y_no_el_del_ultimo_evento(self):
        linea = self.pl.linea
        consultado = None
        for t in range(1, linea.reloj_actual):
            if t not in [reloj for reloj, _ in self.motor.decisiones]:
                consultado = t
                break
        resumen = linea.consultar_instante(consultado, self.motor)
        self.assertEqual(resumen.reloj, consultado)
        # el motor vivo está en otro reloj; con referencia final el título muestra el reloj dado, no el del motor
        final = resumir(self.motor, consultado, ("final", None))
        self.assertNotEqual(self.motor.reloj, consultado)
        self.assertIn(f"(reloj {consultado})", lineas_resumen(final)[0])
        accion = linea.consultar_accion(2, self.motor)
        self.assertIn(f"(reloj {linea.vig_reloj[1]})", lineas_resumen(accion)[0])

    def test_fr006_resultado_victoria_y_derrota_solo_en_final_y_actual(self):
        self.assertIsNone(resumir(self.motor, 1, ("final", None)).resultado)
        self.motor.victoria = True
        try:
            self.assertEqual(resumir(self.motor, 1, ("final", None)).resultado, "victoria")
            self.assertEqual(resumir(self.motor, 1, ("actual", None)).resultado, "victoria")
            self.assertIsNone(resumir(self.motor, 1, ("instante", 1)).resultado)
            self.assertIsNone(resumir(self.motor, 1, ("accion", 1)).resultado)
        finally:
            self.motor.victoria = False
        self.motor.jugador.vivo = False
        try:
            self.assertEqual(resumir(self.motor, 1, ("final", None)).resultado, "derrota")
        finally:
            self.motor.jugador.vivo = True

    def test_fr028_los_pergaminos_pueden_venir_de_la_serie(self):
        base = resumir(self.motor, 1, ("instante", 1))
        self.assertNotIn("Pergamino de retroceso", [nombre for nombre, _ in base.inventario])
        con_serie = resumir(self.motor, 1, ("instante", 1), pergaminos=3)
        self.assertIn(("Pergamino de retroceso", 3), con_serie.inventario)
        sin = resumir(self.motor, 1, ("instante", 1), pergaminos=0)
        self.assertNotIn("Pergamino de retroceso", [nombre for nombre, _ in sin.inventario])

    def test_fr006_enemigos_en_orden_por_id_y_efectos_del_jugador(self):
        from tests.utiles_linea import agregar_enemigo
        sala = self.motor.jugador.sala.id
        for nombre in ("zeta", "alfa", "medio"):
            agregar_enemigo(self.motor, nombre, sala, "guardian")
        ids = [e[0] for e in resumir(self.motor, 1, ("instante", 1)).enemigos]
        self.assertEqual(ids, sorted(ids))
        self.assertGreaterEqual(len(ids), 3)


if __name__ == "__main__":
    unittest.main()
