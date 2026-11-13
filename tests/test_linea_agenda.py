# Pruebas de AgendaConCorte (spec 004, T026; FR-001, FR-002). Sin red.

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.AgendaConCorte import AgendaConCorte
from Modelo.AgendaEventos import AgendaEventos
from Modelo.Evento import Evento
from Modelo.LineaTiempo import LineaTiempo
from tests.utiles_linea import partida_con_linea


def agenda_con(tiempos, corte):
    agenda = AgendaEventos()
    for secuencia, tiempo in enumerate(tiempos):
        agenda.agregar(Evento(tiempo, secuencia, "X"))
    agenda.__class__ = AgendaConCorte
    agenda.corte = corte
    return agenda


class PruebasAgendaConCorte(unittest.TestCase):

    def test_fr001_siguiente_devuelve_none_si_el_proximo_evento_pasa_del_corte(self):
        agenda = agenda_con([300, 500], corte=250)
        self.assertIsNone(agenda.siguiente())
        self.assertTrue(agenda.esta_vacia())
        self.assertIsNone(agenda.extraer())
        self.assertEqual(len(agenda.heap), 2, "los eventos ocultos no se pierden")

    def test_fr001_un_evento_con_tiempo_igual_al_corte_se_entrega(self):
        agenda = agenda_con([250, 300], corte=250)
        self.assertEqual(agenda.siguiente().tiempo, 250)
        self.assertEqual(agenda.extraer().tiempo, 250)
        self.assertIsNone(agenda.siguiente())
        self.assertEqual([ev.tiempo for ev in agenda.heap], [300])

    def test_fr001_entrega_en_orden_hasta_el_corte(self):
        agenda = agenda_con([400, 100, 300, 200, 500], corte=300)
        entregados = []
        while agenda.siguiente() is not None:
            entregados.append(agenda.extraer().tiempo)
        self.assertEqual(entregados, [100, 200, 300])

    def test_fr001_sin_corte_se_comporta_como_agenda_eventos(self):
        agenda = agenda_con([300, 100], corte=None)
        self.assertEqual(agenda.siguiente().tiempo, 100)
        self.assertEqual(agenda.extraer().tiempo, 100)
        self.assertEqual(agenda.extraer().tiempo, 300)
        self.assertIsNone(agenda.siguiente())

    def test_fr001_los_cancelados_que_siguen_en_el_monticulo_no_se_pierden(self):
        """Como en AgendaEventos, solo se limpian los cancelados que llegan a la raíz; los demás quedan."""
        agenda = AgendaEventos()
        primero, segundo, tercero = Evento(100, 0, "X"), Evento(200, 1, "X"), Evento(900, 2, "X")
        for ev in (primero, segundo, tercero):
            agenda.agregar(ev)
        segundo.cancelar()  # en el montículo, pero no en la raíz
        agenda.__class__ = AgendaConCorte
        agenda.corte = 250
        self.assertIs(agenda.siguiente(), primero)
        self.assertEqual(len(agenda.heap), 3, "se perdió un cancelado que no estaba en la raíz")
        self.assertIs(agenda.extraer(), primero)
        # ahora el cancelado llega a la raíz: lo limpia el comportamiento heredado y no hay más hasta el corte
        self.assertIsNone(agenda.siguiente())
        self.assertEqual([ev.tiempo for ev in agenda.heap], [900])

    def test_fr002_la_subclase_solo_la_usa_el_clon_y_la_partida_real_no(self):
        pl = partida_con_linea(k=3)
        self.addCleanup(pl.cerrar)
        pl.jugar(hasta_reloj=500)
        motor = pl.motor
        self.assertIs(type(motor.agenda), AgendaEventos)
        for t in (50, 150, 250, 350):
            pl.linea.consultar_instante(t, motor)
            self.assertIs(type(motor.agenda), AgendaEventos, "la consulta cambió la agenda del motor vivo")
            self.assertFalse(isinstance(motor.agenda, AgendaConCorte))
        clon = pl.linea.clon_antes_de(2, motor)
        try:
            self.assertIs(type(clon.agenda), AgendaEventos)
            clon.agenda.__class__ = AgendaConCorte
            clon.agenda.corte = 0
            self.assertIs(type(motor.agenda), AgendaEventos)
        finally:
            pl.linea._soltar_clon()


if __name__ == "__main__":
    unittest.main()
