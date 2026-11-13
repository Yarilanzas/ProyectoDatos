# Las consultas de la línea no cambian el presente (spec 004, T022; Quickstart 2; SC-004; FR-008, FR-009).
# Se fotografía todo lo observable del motor vivo, de la bitácora y de la línea antes y después de consultas aceptadas y
# rechazadas. Sin red: cripta resoluble creada por ControladorPartida.nueva_partida.

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Controlador.ControladorPartida import ControladorPartida
from Modelo.LineaTiempo import ErrorReconstruccion, LineaTiempo, ReferenciaInvalida
from tests.utiles_linea import (GeneradorAcciones, agregar_enemigo, huella, partida_linea, preparar_motor_linea,
                                resumen_ampliado)


class ControladorConLinea(ControladorPartida):
    # imita el enganche de T035 (que aún no está hecho): registra cada acción aceptada en la línea
    def _accion(self, nombre, argumento, comentario=None):
        aceptada = super()._accion(nombre, argumento, comentario)
        if aceptada:
            self.linea.registrar_accion(self.motor, nombre, argumento)
        return aceptada


def texto_bitacora(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return archivo.read()


def fotografia(partida, linea):
    """Todo lo observable del presente: reloj, acciones, bitácora, guion, conocimiento, mensajes, rastros, posición,
    vida, inventario, efectos, enemigos (todo en resumen_ampliado + huella) e historial de retroceso."""
    motor = partida.motor
    historial = motor.historial
    return {
        "resumen": resumen_ampliado(motor),
        "huella": huella(motor),
        "reloj": motor.reloj,
        "acciones": motor.acciones_jugador,
        "bitacora": texto_bitacora(partida.ruta_bitacora),
        "guion": (list(linea.guion_tipo), list(linea.guion_nombre), list(linea.guion_argumento),
                  list(linea.guion_reloj), list(linea.guion_secuencia)),
        "vigente": (list(linea.vig_guion), list(linea.vig_reloj), list(linea.vig_sec)),
        "puntos": list(linea.pc_accion),
        "historial": (len(historial._intervalos), historial.puede_deshacer()),
        "sala": motor.jugador.sala.id,
        "vida": motor.jugador.vida,
        "enemigos": [(e.id, e.vida, e.sala.id) for e in motor.enemigos],
        "agenda": [(ev.tiempo, ev.secuencia, ev.tipo, ev.cancelado) for ev in motor.agenda.heap],
    }


class EspiaDeAgenda:
    """Cuenta las llamadas a `siguiente()` y `esta_vacia()` de la agenda del motor vivo (no son de solo lectura:
    `AgendaEventos.siguiente()` saca del montículo los cancelados de la raíz)."""

    def __init__(self, agenda):
        self.llamadas = 0
        self.agenda = agenda
        agenda.siguiente = self._contar(agenda.siguiente)
        agenda.esta_vacia = self._contar(agenda.esta_vacia)

    def _contar(self, funcion):
        def espia(*args, **kwargs):
            self.llamadas += 1
            return funcion(*args, **kwargs)
        return espia

    def quitar(self):
        del self.agenda.siguiente
        del self.agenda.esta_vacia


class PruebasSoloLectura(unittest.TestCase):

    def setUp(self):
        self.partida = partida_linea(semilla=9)
        self.addCleanup(self.partida.cerrar)
        controlador = self.partida.controlador
        controlador.__class__ = ControladorConLinea
        self.motor = preparar_motor_linea(controlador.motor, espiar=False)
        # un enemigo errante que consume azar y un efecto: el presente tiene de todo
        agregar_enemigo(self.motor, "err-001", 4, "errante")
        self.motor.aplicar_veneno(self.motor.jugador, 2)
        self.linea = LineaTiempo(k=3, gestor_historico=self.partida.nuevo_gestor_historico())
        controlador.linea = self.linea
        self.linea.iniciar(self.motor)
        generador = GeneradorAcciones(9)
        aceptadas = 0
        while aceptadas < 14:
            nombre, argumento = generador.siguiente(self.motor)
            antes = self.motor.acciones_jugador
            controlador.ejecutar(nombre if argumento == "" else f"{nombre} {argumento}")
            aceptadas += self.motor.acciones_jugador - antes
        self.assertGreater(self.linea.cantidad_puntos, 3)

    def _consultas_aceptadas(self):
        linea, motor = self.linea, self.motor
        resultados = []
        for k in range(1, linea.acciones + 2):
            resultados.append(linea.consultar_accion(k, motor))
        for t in range(0, linea.reloj_actual + 1, 37):
            resultados.append(linea.consultar_instante(t, motor))
        resultados.append(linea.consultar_instante(linea.reloj_actual, motor))
        return resultados

    def _consultas_rechazadas(self):
        linea, motor = self.linea, self.motor
        rechazos = 0
        for llamada in (lambda: linea.consultar_instante(linea.reloj_actual + 1, motor),
                        lambda: linea.consultar_instante(-5, motor),
                        lambda: linea.consultar_accion(0, motor),
                        lambda: linea.consultar_accion(linea.acciones + 2, motor)):
            with self.assertRaises(ReferenciaInvalida):
                llamada()
            rechazos += 1
        return rechazos

    def test_us1_5_consultas_aceptadas_dejan_el_presente_identico(self):
        antes = fotografia(self.partida, self.linea)
        self.assertGreater(len(self._consultas_aceptadas()), 20)
        self.assertEqual(fotografia(self.partida, self.linea), antes)

    def test_us1_5_consultas_rechazadas_dejan_el_presente_identico(self):
        antes = fotografia(self.partida, self.linea)
        self.assertEqual(self._consultas_rechazadas(), 4)
        self.assertEqual(fotografia(self.partida, self.linea), antes)

    def test_us1_5_una_reconstruccion_que_falla_tambien_deja_el_presente_identico(self):
        antes = fotografia(self.partida, self.linea)
        self.linea.vig_sec[1] += 1  # el sello de la decisión 2 ya no coincide: la re-simulación diverge
        try:
            with self.assertRaises(ErrorReconstruccion):
                self.linea.consultar_accion(3, self.motor)  # desde el punto 0: rehace 1 y 2
        finally:
            self.linea.vig_sec[1] -= 1
        self.assertEqual(fotografia(self.partida, self.linea), antes)

    def test_sc004_consultar_accion_acciones_mas_uno_devuelve_el_estado_vivo_sin_ejecutar_nada(self):
        antes = fotografia(self.partida, self.linea)
        resumen = self.linea.consultar_accion(self.linea.acciones + 1, self.motor)
        self.assertEqual(resumen.referencia, ("actual", None))
        self.assertEqual(resumen.reloj, self.motor.reloj)
        self.assertEqual(fotografia(self.partida, self.linea), antes)

    def test_sc004_ninguna_consulta_llama_siguiente_ni_esta_vacia_sobre_el_motor_vivo(self):
        espia = EspiaDeAgenda(self.motor.agenda)
        try:
            self._consultas_aceptadas()
            self._consultas_rechazadas()
            self.linea.clon_antes_de(3, self.motor)
            self.linea._soltar_clon()
        finally:
            llamadas = espia.llamadas
            espia.quitar()
        self.assertEqual(llamadas, 0, "una consulta tocó la agenda del motor vivo con siguiente() o esta_vacia()")

    def test_fr008_una_consulta_no_cambia_la_agenda_del_vivo_ni_con_cancelados_en_la_raiz(self):
        # un evento cancelado en la raíz: siguiente() lo sacaría del montículo. Las consultas no deben notarlo.
        motor = self.motor
        evento = motor.programar_evento(motor.reloj + 1, "REARMAR_TRAMPA", None)
        evento.cancelar()
        antes = [(ev.tiempo, ev.secuencia, ev.cancelado) for ev in motor.agenda.heap]
        self._consultas_aceptadas()
        self.assertEqual([(ev.tiempo, ev.secuencia, ev.cancelado) for ev in motor.agenda.heap], antes)
        self.assertIn(evento, motor.agenda.heap)

    def test_sc004_el_motor_vivo_sigue_jugando_igual_despues_de_consultar(self):
        """Dos partidas idénticas, una consultada y otra no, siguen idénticas al seguir jugando (el azar no se tocó)."""
        gemela = partida_linea(semilla=9)
        self.addCleanup(gemela.cerrar)
        motor_gemelo = preparar_motor_linea(gemela.motor, espiar=False)
        agregar_enemigo(motor_gemelo, "err-001", 4, "errante")
        motor_gemelo.aplicar_veneno(motor_gemelo.jugador, 2)
        generador = GeneradorAcciones(9)
        while motor_gemelo.acciones_jugador < self.motor.acciones_jugador:
            nombre, argumento = generador.siguiente(motor_gemelo)
            motor_gemelo.ejecutar_accion(nombre, argumento)
        self.assertEqual(resumen_ampliado(motor_gemelo), resumen_ampliado(self.motor))

        self._consultas_aceptadas()
        generador_a = GeneradorAcciones(77)
        generador_b = GeneradorAcciones(77)
        for _ in range(10):
            a = generador_a.siguiente(self.motor)
            self.assertEqual(a, generador_b.siguiente(motor_gemelo))
            self.assertEqual(self.motor.ejecutar_accion(*a), motor_gemelo.ejecutar_accion(*a))
        self.assertEqual(resumen_ampliado(motor_gemelo), resumen_ampliado(self.motor))


if __name__ == "__main__":
    unittest.main()
