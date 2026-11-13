# Reconstruir sin solicitudes nuevas (spec 004, T027; Quickstart 13; FR-008, FR-025; research R10).
# El gestor histórico lee del mismo disco que el gestor de la partida y no tiene red. Sin red real: la fuente es un
# paquete offline temporal. `solicitudes_realizadas` es el contador de solicitudes (el «presupuesto»).

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Gestor.GestorHistorico import FuenteSinRed, GestorHistorico, SinDatosParaHistoria
from tests.utiles_linea import partida_con_linea
from tests.utiles_niebla import CRIPTA_NIEBLA


class PruebasFuenteSinRed(unittest.TestCase):

    def setUp(self):
        self.fuente = FuenteSinRed(CRIPTA_NIEBLA, "v1", "cat-1", "detalles-capturados")

    def test_fr025_devuelve_las_versiones_y_los_detalles_capturados(self):
        self.assertEqual(self.fuente.obtener_version_cripta(CRIPTA_NIEBLA), "v1")
        self.assertEqual(self.fuente.obtener_version_catalogo(), "cat-1")
        self.assertEqual(self.fuente.obtener_detalles_cripta(CRIPTA_NIEBLA), "detalles-capturados")
        self.assertEqual(self.fuente.solicitudes_realizadas, 0)

    def test_fr025_cualquier_otro_metodo_lanza_sin_datos_para_historia(self):
        llamadas = (lambda: self.fuente.list_criptas(),
                    lambda: self.fuente.obtener_llaves_cripta(CRIPTA_NIEBLA),
                    lambda: self.fuente.obtener_esqueleto_cripta(CRIPTA_NIEBLA),
                    lambda: self.fuente.obtener_contenido_sala(CRIPTA_NIEBLA, [1, 2]),
                    lambda: self.fuente.obtener_fichas_catalogo(["itm_x"]),
                    lambda: self.fuente._obtener("/criptas"),
                    lambda: self.fuente.obtener_version_cripta("otra"),
                    lambda: self.fuente.obtener_detalles_cripta("otra"))
        for llamada in llamadas:
            with self.assertRaises(SinDatosParaHistoria):
                llamada()
        self.assertEqual(self.fuente.solicitudes_realizadas, 0)

    def test_fr025_sin_datos_para_historia_es_un_runtime_error_con_el_mensaje_del_contrato(self):
        self.assertTrue(issubclass(SinDatosParaHistoria, RuntimeError))
        error = SinDatosParaHistoria("contenido de las salas 2")
        self.assertEqual(str(error), "No se puede reconstruir sin nuevas solicitudes: faltan datos locales "
                                     "(contenido de las salas 2)")
        self.assertEqual(error.que, "contenido de las salas 2")


class PruebasGestorHistorico(unittest.TestCase):

    def setUp(self):
        self.pl = partida_con_linea(k=3)
        self.addCleanup(self.pl.cerrar)
        self.partida = self.pl.partida
        self.motor = self.pl.motor
        self.linea = self.pl.linea
        self.pl.jugar(hasta_reloj=600)
        self.gestor_vivo = self.partida.gestor
        self.fuente_viva = self.gestor_vivo.fuente
        self.historico = self.linea.gestor_historico

    def _consultar_todo(self):
        for k in range(1, self.linea.acciones + 2):
            self.linea.consultar_accion(k, self.motor)
        for t in range(0, self.linea.reloj_actual, 53):
            self.linea.consultar_instante(t, self.motor)

    def test_fr008_reconstruir_hace_cero_llamadas_a_la_fuente(self):
        vivas = self.fuente_viva.solicitudes_realizadas
        self.assertIsInstance(self.historico, GestorHistorico)
        self.assertIsInstance(self.historico.fuente, FuenteSinRed)
        self._consultar_todo()
        self.assertEqual(self.fuente_viva.solicitudes_realizadas, vivas, "una consulta pidió datos a la fuente viva")
        self.assertEqual(self.historico.fuente.solicitudes_realizadas, 0)

    def test_fr008_el_gestor_historico_no_toca_los_contadores_del_gestor_vivo(self):
        aciertos, fallos = self.gestor_vivo.aciertos_cache, self.gestor_vivo.fallos_cache
        cache_viva = list(self.gestor_vivo.cache_catalogo.fichas)
        self._consultar_todo()
        self.assertEqual((self.gestor_vivo.aciertos_cache, self.gestor_vivo.fallos_cache), (aciertos, fallos))
        self.assertEqual(list(self.gestor_vivo.cache_catalogo.fichas), cache_viva)
        self.assertIsNot(self.historico.cache_catalogo, self.gestor_vivo.cache_catalogo)
        self.assertIs(self.historico.almacenamiento_disco, self.gestor_vivo.almacenamiento_disco)
        # y tampoco se queda enganchado al último clon
        self.assertIsNone(self.historico.estado_juego)
        self.assertIs(self.gestor_vivo.estado_juego, self.motor)

    def test_fr008_vaciar_la_cache_de_memoria_y_reconstruir_lee_del_disco(self):
        esperado = [self.linea.consultar_accion(k, self.motor).sala for k in range(1, self.linea.acciones + 1)]
        self.historico.cache_catalogo.fichas = []
        self.historico._contenido_en_memoria = []
        self.historico._salas_cargadas = []
        vivas = self.fuente_viva.solicitudes_realizadas
        otra_vez = [self.linea.consultar_accion(k, self.motor).sala for k in range(1, self.linea.acciones + 1)]
        self.assertEqual(otra_vez, esperado)
        self.assertEqual(self.fuente_viva.solicitudes_realizadas, vivas)
        self.assertEqual(self.historico.fuente.solicitudes_realizadas, 0)

    def test_fr025_borrar_un_dato_local_da_sin_datos_para_historia_y_no_gasta_presupuesto(self):
        carpeta = self.partida.ruta_datos
        contenido = os.path.join(carpeta, f"contenido_{CRIPTA_NIEBLA}.json")
        self.assertTrue(os.path.exists(contenido))
        os.remove(contenido)
        self.historico._contenido_en_memoria = []
        self.historico._salas_cargadas = []
        vivas = self.fuente_viva.solicitudes_realizadas
        with self.assertRaises(SinDatosParaHistoria) as contexto:
            self.linea.consultar_accion(2, self.motor)  # desde el punto 0: rehace la acción 1 y necesita el disco
        self.assertTrue(str(contexto.exception).startswith(
            "No se puede reconstruir sin nuevas solicitudes: faltan datos locales ("))
        self.assertIsInstance(contexto.exception, RuntimeError)
        self.assertEqual(self.fuente_viva.solicitudes_realizadas, vivas, "se gastó presupuesto")
        self.assertEqual(self.historico.fuente.solicitudes_realizadas, 0)
        # el presente quedó igual y el gestor no quedó enganchado al clon fallido
        self.assertIs(self.gestor_vivo.estado_juego, self.motor)
        self.assertIsNone(self.historico.estado_juego)

    def test_fr025_borrar_el_catalogo_local_tambien_se_detecta(self):
        os.remove(os.path.join(self.partida.ruta_datos, "catalogo.json"))
        self.historico.cache_catalogo.fichas = []
        self.historico._contenido_en_memoria = []
        self.historico._salas_cargadas = []
        with self.assertRaises(SinDatosParaHistoria):
            self.linea.consultar_accion(2, self.motor)

    def test_fr025_desde_gestor_captura_versiones_y_detalles(self):
        nuevo = GestorHistorico.desde_gestor(self.gestor_vivo, CRIPTA_NIEBLA)
        self.assertEqual(nuevo.version_cripta(CRIPTA_NIEBLA), self.gestor_vivo.version_cripta(CRIPTA_NIEBLA))
        self.assertEqual(nuevo.version_catalogo(), self.gestor_vivo.version_catalogo())
        self.assertIs(nuevo.obtener_detalles(CRIPTA_NIEBLA), self.gestor_vivo.obtener_detalles(CRIPTA_NIEBLA))


if __name__ == "__main__":
    unittest.main()
