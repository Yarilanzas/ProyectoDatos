# Épocas y cargas de la línea de tiempo (spec 004, T068; FR-017, FR-022, FR-030; Historia 5).
# Una carga abre una época: la línea registra CARGA en el guion, toma un punto de control del motor **cargado** y guarda la
# copia privada del archivo que se cargó. Sin red: la partida y los archivos viven en una carpeta temporal propia.
# Contrato: contracts/interfaz-linea.md («registrar_carga», «a_registro», «desde_registro», «cerrar»).

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.BusquedaBinaria import ultimo_menor_o_igual
from Modelo.LineaTiempo import LineaTiempo, TIPO_ACCION, TIPO_CARGA, TIPO_RETROCESO
from Persistencia.RegistroLinea import ACCION, CARGA, RETROCESO
from tests.test_linea_consulta import contenido
from tests.utiles_linea import SesionLinea, partida_linea


class BaseEpoca(unittest.TestCase):

    def sesion(self, k=3, pergaminos=0, semilla=3):
        sesion = SesionLinea(k=k, semilla=semilla, pergaminos=pergaminos)
        self.addCleanup(sesion.cerrar)
        return sesion

    def comprobar_todas_las_decisiones(self, sesion):
        """Cada `#k` y cada instante de decisión devuelven el estado que se vio justo antes de esa acción, también los de
        antes de una carga."""
        linea, motor = sesion.linea, sesion.motor
        self.assertEqual(len(sesion.decisiones), linea.acciones)
        for k in range(1, linea.acciones + 1):
            reloj, esperado = sesion.decisiones[k - 1]
            with self.subTest(k=k):
                self.assertEqual(contenido(linea.consultar_accion(k, motor)), esperado)
            with self.subTest(t=reloj):
                self.assertEqual(contenido(linea.consultar_instante(reloj, motor)), esperado)


class PruebasRegistrarCarga(BaseEpoca):

    def test_fr022_agrega_carga_al_guion_con_el_reloj_cargado(self):
        sesion = self.sesion()
        sesion.jugar(5)
        antes = len(sesion.linea.guion_tipo)
        sesion.guardar_y_cargar()
        linea = sesion.linea
        self.assertEqual(len(linea.guion_tipo), antes + 1)
        self.assertEqual(linea.guion_tipo[-1], TIPO_CARGA)
        self.assertEqual(linea.guion_reloj[-1], sesion.motor.reloj)

    def test_fr022_la_carga_no_cambia_la_historia_vigente(self):
        sesion = self.sesion()
        sesion.jugar(5)
        vigentes = (list(sesion.linea.vig_guion), list(sesion.linea.vig_reloj), list(sesion.linea.vig_sec))
        sesion.guardar_y_cargar()
        linea = sesion.linea
        self.assertEqual((linea.vig_guion, linea.vig_reloj, linea.vig_sec), vigentes)
        self.assertEqual(linea.acciones, 5)

    def test_fr017_abre_una_epoca_con_la_copia_privada(self):
        sesion = self.sesion()
        linea = sesion.linea
        self.assertEqual((linea.epocas_accion, linea.epocas_ruta), ([0], [None]))
        sesion.jugar(5)
        copia = sesion.guardar_y_cargar()
        self.assertEqual((linea.epocas_accion, linea.epocas_ruta), ([0, 5], [None, copia]))
        sesion.jugar(2)
        segunda = sesion.guardar_y_cargar()
        self.assertEqual((linea.epocas_accion, linea.epocas_ruta), ([0, 5, 7], [None, copia, segunda]))

    def test_fr017_toma_un_punto_del_motor_cargado_en_la_accion_n(self):
        sesion = self.sesion(k=3)
        sesion.jugar(5)            # el último punto regular está en la acción 3
        linea = sesion.linea
        puntos = linea.cantidad_puntos
        sesion.guardar_y_cargar()
        self.assertEqual(linea.cantidad_puntos, puntos + 1)
        self.assertEqual(linea.pc_accion[-1], 5)
        self.assertEqual(linea.pc_epoca[-1], 1)
        self.assertEqual(linea.pc_reloj[-1], sesion.motor.reloj)
        punto = linea.pc_punto[-1]
        self.assertEqual((punto.accion, punto.epoca, punto.reloj), (5, 1, sesion.motor.reloj))
        self.assertEqual(punto.secuencia, sesion.motor.secuencia)

    def test_fr017_un_punto_regular_en_la_misma_accion_queda_y_la_busqueda_devuelve_el_ultimo(self):
        sesion = self.sesion(k=3)
        sesion.jugar(6)            # 6 es múltiplo de K: ya hay un punto regular en la acción 6
        linea = sesion.linea
        self.assertEqual(linea.pc_accion[-1], 6)
        puntos = linea.cantidad_puntos
        sesion.guardar_y_cargar()
        self.assertEqual(linea.cantidad_puntos, puntos + 1)
        self.assertEqual(linea.pc_accion[-2:], [6, 6])                 # repetidos, no decrecientes
        self.assertEqual(linea.pc_epoca[-2:], [0, 1])
        indice = ultimo_menor_o_igual(linea.pc_accion, 6)
        self.assertEqual(indice, len(linea.pc_accion) - 1)
        self.assertEqual(linea.pc_epoca[indice], 1)                    # el de la carga, no el regular
        for anterior, siguiente in zip(linea.pc_accion, linea.pc_accion[1:]):
            self.assertLessEqual(anterior, siguiente)

    def test_fr017_dos_cargas_seguidas_en_la_misma_accion(self):
        sesion = self.sesion(k=3)
        sesion.jugar(4)
        sesion.guardar_y_cargar()
        sesion.guardar_y_cargar()
        linea = sesion.linea
        self.assertEqual(linea.epocas_accion, [0, 4, 4])
        self.assertEqual(linea.pc_accion[-2:], [4, 4])
        self.assertEqual(linea.pc_epoca[-2:], [1, 2])
        self.assertEqual(linea.guion_tipo[-2:], [TIPO_CARGA, TIPO_CARGA])

    def test_fr022_registrar_carga_exige_iniciar(self):
        partida = partida_linea()
        self.addCleanup(partida.cerrar)
        linea = LineaTiempo(k=3, gestor_historico=partida.nuevo_gestor_historico())
        with self.assertRaises(RuntimeError):
            linea.registrar_carga(partida.motor, None)

    def test_fr017_sin_copia_privada_la_epoca_queda_sin_ruta(self):
        sesion = self.sesion()
        sesion.jugar(3)
        sesion.linea.registrar_carga(sesion.motor, None)   # un motor sin restaurador: no hay salas pendientes
        self.assertEqual(sesion.linea.epocas_ruta, [None, None])
        self.assertEqual(sesion.linea.epocas_accion, [0, 3])


class PruebasHistoriaAntesYDespuesDeCargar(BaseEpoca):

    def test_fr022_la_linea_anterior_a_la_carga_queda_intacta(self):
        sesion = self.sesion()
        sesion.jugar(8)
        linea = sesion.linea
        antes = [(k, contenido(linea.consultar_accion(k, sesion.motor))) for k in range(1, linea.acciones + 1)]
        reloj = linea.reloj_actual
        pasos = [t for t in range(0, reloj, 17)]
        instantes_antes = [(t, contenido(linea.consultar_instante(t, sesion.motor))) for t in pasos]
        sesion.guardar_y_cargar()
        for k, esperado in antes:
            with self.subTest(k=k):
                self.assertEqual(contenido(linea.consultar_accion(k, sesion.motor)), esperado)
        for t, esperado in instantes_antes:
            with self.subTest(t=t):
                self.assertEqual(contenido(linea.consultar_instante(t, sesion.motor)), esperado)

    def test_fr022_tras_cargar_y_continuar_cada_decision_es_la_que_se_vio(self):
        sesion = self.sesion(k=3)
        sesion.jugar(7)
        sesion.guardar_y_cargar()
        sesion.jugar(8)
        self.assertEqual(sesion.linea.acciones, 15)
        self.comprobar_todas_las_decisiones(sesion)

    def test_fr022_dos_cargas_con_acciones_entre_ellas(self):
        sesion = self.sesion(k=4)
        sesion.jugar(5)
        sesion.guardar_y_cargar()
        sesion.jugar(6)
        sesion.guardar_y_cargar()
        sesion.jugar(5)
        self.assertEqual(sesion.linea.epocas_accion, [0, 5, 11])
        self.comprobar_todas_las_decisiones(sesion)

    def test_fr017_el_instante_actual_tras_cargar_es_el_motor_cargado(self):
        sesion = self.sesion()
        sesion.jugar(4)
        sesion.guardar_y_cargar()
        linea, motor = sesion.linea, sesion.motor
        self.assertEqual(linea.reloj_actual, motor.reloj)
        resumen = linea.consultar_instante(motor.reloj, motor)
        self.assertEqual(resumen.referencia, ("actual", None))
        self.assertEqual(linea.consultar_accion(linea.acciones + 1, motor).referencia, ("actual", None))

    def test_fr030_el_primer_retroceder_tras_cargar_se_rechaza_como_en_la_parte_i(self):
        sesion = self.sesion(pergaminos=2)
        sesion.jugar(4)
        sesion.guardar_y_cargar()
        linea = sesion.linea
        guion = len(linea.guion_tipo)
        acciones = linea.acciones
        # el historial de retroceso no se guarda: el motor cargado no tiene nada que revertir
        self.assertFalse(sesion.motor.ejecutar_accion("retroceder", ""))
        self.assertFalse(sesion.retroceder())
        self.assertEqual((len(linea.guion_tipo), linea.acciones), (guion, acciones))

    def test_fr030_tras_cargar_y_jugar_un_retroceso_vuelve_a_funcionar(self):
        sesion = self.sesion(pergaminos=2, k=3)
        base = sesion.linea.acciones                  # las acciones que recogieron los pergaminos
        sesion.jugar(4)
        sesion.guardar_y_cargar()
        sesion.jugar(3)
        self.assertTrue(sesion.retroceder())
        linea = sesion.linea
        self.assertEqual(linea.guion_tipo[-1], TIPO_RETROCESO)
        self.assertEqual(linea.acciones, base + 6)
        # los retrocesos no deshacen la época anterior: el pasado de antes de la carga sigue igual
        for k in range(1, linea.acciones + 1):
            reloj, esperado = sesion.decisiones[k - 1]
            with self.subTest(k=k):
                self.assertEqual(contenido(linea.consultar_accion(k, sesion.motor)), esperado)


class PruebasRegistroYCierre(BaseEpoca):

    def test_fr022_a_registro_guarda_el_guion_completo_con_retrocesos_y_cargas(self):
        sesion = self.sesion(pergaminos=2, k=3)
        sesion.jugar(4)
        self.assertTrue(sesion.retroceder())
        sesion.jugar(2)
        sesion.guardar_y_cargar()
        sesion.jugar(2)
        registro = sesion.linea.a_registro()
        linea = sesion.linea
        self.assertEqual(registro.k, 3)
        self.assertEqual(len(registro.registros), len(linea.guion_tipo))
        tipos = [entrada[0] for entrada in registro.registros]
        self.assertEqual(tipos.count(RETROCESO), 1)
        self.assertEqual(tipos.count(CARGA), 1)
        for posicion in range(len(linea.guion_tipo)):
            entrada = registro.registros[posicion]
            if linea.guion_tipo[posicion] == TIPO_ACCION:
                self.assertEqual(entrada, (ACCION, linea.guion_nombre[posicion], linea.guion_argumento[posicion],
                                           linea.guion_reloj[posicion], linea.guion_secuencia[posicion]))
            elif linea.guion_tipo[posicion] == TIPO_RETROCESO:
                self.assertEqual(entrada, (RETROCESO, linea.guion_reloj[posicion]))
            else:
                self.assertEqual(entrada, (CARGA, linea.guion_reloj[posicion]))

    def test_fr022_a_registro_es_estable_y_pasa_por_los_bytes(self):
        sesion = self.sesion(pergaminos=1, k=3)
        sesion.jugar(5)
        sesion.retroceder()
        sesion.jugar(2)
        sesion.guardar_y_cargar()
        registro = sesion.linea.a_registro()
        self.assertEqual(registro.to_bytes(), sesion.linea.a_registro().to_bytes())
        self.assertEqual(type(registro).from_bytes(registro.to_bytes()), registro)

    def test_fr022_desde_registro_reconstruye_solo_los_datos(self):
        sesion = self.sesion(pergaminos=2, k=4)
        sesion.jugar(6)
        sesion.retroceder()
        sesion.jugar(3)
        sesion.guardar_y_cargar()
        sesion.jugar(2)
        original = sesion.linea
        copia = LineaTiempo.desde_registro(original.a_registro())
        self.assertEqual(copia.k, original.k)
        for nombre in ("guion_tipo", "guion_nombre", "guion_argumento", "guion_reloj", "guion_secuencia",
                       "vig_guion", "vig_reloj", "vig_sec"):
            with self.subTest(nombre=nombre):
                self.assertEqual(getattr(copia, nombre), getattr(original, nombre))
        self.assertEqual(copia.acciones, original.acciones)
        self.assertEqual(copia.cantidad_puntos, 0)             # los puntos no se guardan: los rehace el controlador
        self.assertEqual(copia.a_registro(), original.a_registro())

    def test_fr031_desde_registro_respeta_el_k_guardado(self):
        sesion = self.sesion(k=7)
        sesion.jugar(3)
        copia = LineaTiempo.desde_registro(sesion.linea.a_registro())
        self.assertEqual(copia.k, 7)

    def test_fr017_cerrar_devuelve_las_copias_privadas_y_no_las_borra(self):
        sesion = self.sesion()
        sesion.jugar(3)
        primera = sesion.guardar_y_cargar()
        sesion.jugar(2)
        segunda = sesion.guardar_y_cargar()
        rutas = sesion.linea.cerrar()
        self.assertEqual(rutas, [primera, segunda])
        self.assertTrue(os.path.exists(primera) and os.path.exists(segunda))   # las borra el controlador
        self.assertEqual(sesion.linea.cerrar(), [])                            # idempotente

    def test_fr017_cerrar_una_linea_sin_cargas_no_pide_borrar_nada(self):
        sesion = self.sesion()
        sesion.jugar(2)
        self.assertEqual(sesion.linea.cerrar(), [])


if __name__ == "__main__":
    unittest.main()
