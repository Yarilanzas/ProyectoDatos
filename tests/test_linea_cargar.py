# Guardar y cargar con la línea de tiempo en el controlador (spec 004, T085; FR-022, FR-024, FR-025, FR-030, FR-031).
# `guardar` escribe el guion de la línea en el archivo; `cargar` lo reproduce (ReconstructorLinea), deja el punto del motor
# cargado, la época y su copia privada, y es **atómico**: si falla cualquier cosa, el motor, la bitácora y la línea que el
# controlador tenía quedan como estaban (hallazgo H1 de la revisión T117). Sin red: carpetas temporales propias.
# Las pruebas de T070 a T078 (otra tanda) recorren el mismo camino con procesos nuevos y archivos alterados.

import os
import sys
import unittest
from unittest import mock

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Controlador.ControladorPartida import ControladorPartida, guardar_motor, ruta_bitacora_de
from Controlador.ReconstructorLinea import ReconstructorLinea
from Gestor.GestorHistorico import SinDatosParaHistoria
from Modelo.LineaTiempo import ErrorReconstruccion, TIPO_CARGA
from Persistencia.FormatoBinario import VersionIncompatible
from Persistencia.RegistroLinea import CARGA, RegistroLinea
from Vista.TextoResumen import lineas_resumen
from tests.test_integracion import VistaFalsa
from tests.utiles_linea import CONTENIDO_LINEA, archivo_con_linea, leer_bloque_linea, partida_linea
from tests.utiles_niebla import CRIPTA_NIEBLA, PERGAMINO, contenido_sala

COMANDOS = ["recoger {pergamino}", "esperar", "mover S", "esperar", "mover E", "retroceder", "esperar", "mover O"]
INSTANTES = (0, 25, 100, 160, 250, 300)


def historia(controlador, t):
    vista = controlador.vista
    vista.lineas.clear()
    controlador.ejecutar(f"historia {t}")
    nombre, argumentos = vista.lineas[-1]
    if nombre != "mostrar_resumen_historico":
        raise AssertionError(f"historia {t} mostró {nombre}: {argumentos}")
    return lineas_resumen(argumentos[0])


def leer(ruta):
    with open(ruta, "rb") as archivo:
        return archivo.read()


class BaseCargar(unittest.TestCase):

    def partida_jugada(self, k=None, comandos=COMANDOS):
        contenido = CONTENIDO_LINEA + [contenido_sala(1, objetos=(PERGAMINO,))]
        partida = partida_linea(contenido=contenido)
        self.addCleanup(partida.cerrar)
        controlador = partida.controlador
        if k is not None:
            controlador.k_linea = k
            controlador.nueva_partida(CRIPTA_NIEBLA, 7)
        pergamino = controlador.motor.obtener_objetos_suelo(controlador.motor.jugador.sala)[0].instancia_id
        for comando in comandos:
            controlador.ejecutar(comando.format(pergamino=pergamino))
        return partida

    def guardada(self, partida, nombre="guardado.cripta"):
        ruta = os.path.join(partida.carpeta.name, nombre)
        self.assertTrue(partida.controlador.guardar(ruta))
        return ruta

    def controlador_nuevo(self, partida, nombre_log="otra.log"):
        """Un controlador de «otro proceso»: gestor nuevo sobre la misma carpeta de datos locales, bitácora propia."""
        controlador = ControladorPartida(partida.nuevo_gestor(iniciado=False), VistaFalsa(),
                                         os.path.join(partida.carpeta.name, nombre_log))
        self.addCleanup(controlador._cerrar)
        return controlador

    def con_una_partida_en_curso(self, partida, semilla=9):
        controlador = self.controlador_nuevo(partida, "en_curso.log")
        controlador.nueva_partida(CRIPTA_NIEBLA, semilla)
        controlador.ejecutar("esperar")
        controlador.ejecutar("esperar")
        return controlador

    def foto(self, controlador):
        return (controlador.motor, controlador.bitacora, controlador.linea, controlador.observador, controlador.k_linea,
                controlador.motor.reloj, controlador.linea.a_registro(), leer(controlador.ruta_bitacora))

    def assertIgual(self, antes, controlador):
        despues = self.foto(controlador)
        for indice in (0, 1, 2, 3):
            self.assertIs(despues[indice], antes[indice], ("motor", "bitacora", "linea", "observador")[indice])
        self.assertEqual(despues[4:], antes[4:])


class PruebasGuardar(BaseCargar):

    def test_fr022_guardar_escribe_el_guion_de_la_linea(self):
        partida = self.partida_jugada()
        ruta = self.guardada(partida)
        bloque = leer_bloque_linea(ruta)
        self.assertGreater(len(bloque), 8)
        self.assertEqual(RegistroLinea.from_bytes(bloque), partida.controlador.linea.a_registro())

    def test_fr022_guardar_sin_linea_escribe_largo_cero(self):
        partida = self.partida_jugada()
        partida.controlador.linea = partida.controlador.observador = None      # línea desfasada: se descartó
        ruta = self.guardada(partida)
        self.assertEqual(leer_bloque_linea(ruta), b"")

    def test_fr022_una_linea_desfasada_no_se_guarda_y_el_archivo_se_puede_cargar(self):
        partida = self.partida_jugada()
        controlador = partida.controlador
        partida.motor.ejecutar_accion("esperar", "")     # el motor avanza sin pasar por el controlador: la línea no se entera
        self.assertFalse(controlador.linea.sincronizada(partida.motor))
        ruta = self.guardada(partida)
        self.assertEqual(leer_bloque_linea(ruta), b"")   # un guion que no lleva a este estado haría el archivo imposible de cargar
        self.assertIsNone(controlador.linea)
        self.assertEqual(controlador.vista.lineas[-2][0], "mostrar_aviso")
        otro = self.controlador_nuevo(partida)
        otro.cargar(ruta)
        self.assertEqual(otro.linea.acciones, 0)

    def test_fr022_guardar_motor_sin_linea_por_omision_escribe_largo_cero(self):
        partida = self.partida_jugada()
        ruta = os.path.join(partida.carpeta.name, "sin_linea.cripta")
        guardar_motor(partida.motor, ruta, partida.gestor)              # como lo llama ejecutar_replay: tres argumentos
        self.assertEqual(leer_bloque_linea(ruta), b"")
        con = os.path.join(partida.carpeta.name, "con_linea.cripta")
        guardar_motor(partida.motor, con, partida.gestor, linea=partida.controlador.linea.a_registro())
        self.assertEqual(RegistroLinea.from_bytes(leer_bloque_linea(con)), partida.controlador.linea.a_registro())


class PruebasCargar(BaseCargar):

    def test_fr022_cargar_reconstruye_la_linea_con_el_guion_y_una_carga(self):
        partida = self.partida_jugada()
        original = partida.controlador.linea.a_registro()
        ruta = self.guardada(partida)
        controlador = self.controlador_nuevo(partida)
        controlador.cargar(ruta)
        registro = controlador.linea.a_registro()
        self.assertEqual(registro.registros[:-1], original.registros)
        self.assertEqual(registro.registros[-1], (CARGA, controlador.motor.reloj))
        # una sola carga: la reconstrucción ya la agregó, `cargar` no llama a `registrar_carga` otra vez
        self.assertEqual(controlador.linea.guion_tipo.count(TIPO_CARGA), 1)
        self.assertEqual(controlador.linea.epocas_accion, [0, controlador.linea.acciones])
        self.assertIsNotNone(controlador.observador)
        self.assertIs(controlador.observador.linea, controlador.linea)

    def test_fr022_tras_cargar_historia_responde_igual_que_antes_de_guardar(self):
        partida = self.partida_jugada()
        antes = [historia(partida.controlador, t) for t in INSTANTES if t < partida.controlador.linea.reloj_actual]
        ruta = self.guardada(partida)
        controlador = self.controlador_nuevo(partida)
        controlador.cargar(ruta)
        despues = [historia(controlador, t) for t in INSTANTES if t < partida.controlador.linea.reloj_actual]
        self.assertEqual(despues, antes)
        self.assertGreater(len(antes), 3)

    def test_fr025_se_puede_seguir_jugando_guardar_y_cargar_otra_vez(self):
        partida = self.partida_jugada()
        ruta = self.guardada(partida)
        controlador = self.controlador_nuevo(partida)
        controlador.cargar(ruta)
        controlador.ejecutar("esperar")
        controlador.ejecutar("esperar")
        vigentes = controlador.linea.acciones
        antes = [historia(controlador, t) for t in (0, 100, 250)]
        segundo = os.path.join(partida.carpeta.name, "segundo.cripta")
        self.assertTrue(controlador.guardar(segundo))
        tercero = self.controlador_nuevo(partida, "tercera.log")
        tercero.cargar(segundo)
        self.assertEqual(tercero.linea.acciones, vigentes)
        self.assertEqual(tercero.linea.guion_tipo.count(TIPO_CARGA), 2)
        self.assertEqual([historia(tercero, t) for t in (0, 100, 250)], antes)

    def test_fr031_el_comando_cargar_adopta_el_k_del_archivo(self):
        partida = self.partida_jugada(k=7)
        self.assertEqual(partida.controlador.linea.k, 7)
        ruta = self.guardada(partida)
        controlador = self.controlador_nuevo(partida)
        self.assertEqual(controlador.k_linea, 50)
        controlador.cargar(ruta)
        self.assertEqual(controlador.linea.k, 7)
        self.assertEqual(controlador.k_linea, 7)

    def test_fr031_un_archivo_sin_bloque_de_linea_empieza_la_linea_en_la_carga_con_el_k_de_la_ejecucion(self):
        partida = self.partida_jugada()
        ruta = os.path.join(partida.carpeta.name, "sin_linea.cripta")
        guardar_motor(partida.motor, ruta, partida.gestor)
        controlador = self.controlador_nuevo(partida)
        controlador.k_linea = 9
        controlador.cargar(ruta)
        self.assertEqual(controlador.linea.k, 9)
        self.assertEqual(controlador.linea.acciones, 0)
        self.assertEqual(historia(controlador, 0)[0], "Historia — instante 0")
        controlador.ejecutar("esperar")
        self.assertEqual(controlador.linea.acciones, 1)
        self.assertEqual(historia(controlador, controlador.motor.reloj - 100)[0].split()[0], "Historia")

    def test_fr025_cargar_sin_bitacora_junto_al_guardado_sigue_con_linea(self):
        partida = self.partida_jugada()
        ruta = self.guardada(partida)
        os.remove(ruta_bitacora_de(ruta))
        controlador = self.controlador_nuevo(partida)
        controlador.cargar(ruta)
        self.assertIsNone(controlador.bitacora)
        self.assertIsNotNone(controlador.linea)
        self.assertEqual(controlador.linea.acciones, partida.controlador.linea.acciones)


class PruebasCargarEsAtomico(BaseCargar):
    """H1: un fallo posterior a `cargar_partida` no cambia nada del controlador."""

    def preparar(self):
        partida = self.partida_jugada()
        ruta = self.guardada(partida)
        controlador = self.con_una_partida_en_curso(partida)
        return partida, ruta, controlador, self.foto(controlador)

    def assertSigueJugando(self, controlador, antes):
        controlador.ejecutar("esperar")
        self.assertEqual(controlador.linea.acciones, len(antes[6].registros) + 1)
        self.assertEqual(controlador.motor.reloj, antes[5] + 100)
        with open(controlador.ruta_bitacora, encoding="utf-8") as archivo:
            self.assertTrue(archivo.read().endswith("esperar\n"))     # la bitácora vieja sigue recibiendo acciones
        self.assertEqual(historia(controlador, 0)[0], "Historia — instante 0")

    def test_fr022_h1_una_copia_de_bitacora_danada_no_cambia_nada(self):
        partida, ruta, controlador, antes = self.preparar()
        with open(ruta_bitacora_de(ruta), "w", encoding="utf-8") as archivo:
            archivo.write("esto no es una bitácora\n")
        with self.assertRaises(VersionIncompatible):
            controlador.cargar(ruta)
        self.assertIgual(antes, controlador)
        self.assertEqual(os.path.getsize(controlador.ruta_bitacora), len(antes[7]))
        controlador.ejecutar("esperar")
        self.assertEqual(controlador.linea.acciones, len(antes[6].registros) + 1)
        self.assertEqual(historia(controlador, 0)[0], "Historia — instante 0")
        os.remove(ruta)    # ningún archivo de la carga quedó abierto (en Windows no se podría borrar)

    def test_fr025_h1_sin_datos_para_historia_no_cambia_nada(self):
        partida, ruta, controlador, antes = self.preparar()
        with mock.patch.object(ReconstructorLinea, "reconstruir", side_effect=SinDatosParaHistoria("esqueleto")):
            with self.assertRaises(SinDatosParaHistoria):
                controlador.cargar(ruta)
        self.assertIgual(antes, controlador)
        self.assertSigueJugando(controlador, antes)
        os.remove(ruta)

    def test_fr025_h1_un_error_de_reconstruccion_no_cambia_nada(self):
        partida, ruta, controlador, antes = self.preparar()
        with mock.patch.object(ReconstructorLinea, "reconstruir", side_effect=ErrorReconstruccion("el sello no coincide")):
            with self.assertRaises(ErrorReconstruccion):
                controlador.cargar(ruta)
        self.assertIgual(antes, controlador)
        self.assertSigueJugando(controlador, antes)
        os.remove(ruta)

    def test_fr024_h1_un_guion_que_no_coincide_con_la_partida_no_cambia_nada(self):
        partida, ruta, controlador, antes = self.preparar()
        alterado = archivo_con_linea(ruta, os.path.join(partida.carpeta.name, "alterado.cripta"),
                                     RegistroLinea.from_bytes(leer_bloque_linea(ruta)), "sello")
        with open(ruta_bitacora_de(ruta), "rb") as origen, open(ruta_bitacora_de(alterado), "wb") as destino:
            destino.write(origen.read())
        with self.assertRaises(VersionIncompatible) as contexto:
            controlador.cargar(alterado)
        self.assertEqual(str(contexto.exception), "la línea de tiempo no coincide con la partida")
        self.assertIgual(antes, controlador)
        self.assertSigueJugando(controlador, antes)
        os.remove(alterado)

    def test_fr024_h1_un_bloque_de_linea_danado_no_cambia_nada(self):
        partida, ruta, controlador, antes = self.preparar()
        for modo in ("truncado", "tipo"):
            with self.subTest(modo=modo):
                dañado = archivo_con_linea(ruta, os.path.join(partida.carpeta.name, f"{modo}.cripta"),
                                           RegistroLinea.from_bytes(leer_bloque_linea(ruta)), modo)
                with open(ruta_bitacora_de(ruta), "rb") as origen, open(ruta_bitacora_de(dañado), "wb") as destino:
                    destino.write(origen.read())
                with self.assertRaises(VersionIncompatible):
                    controlador.cargar(dañado)
                self.assertIgual(antes, controlador)
                os.remove(dañado)

    def test_fr022_h1_el_comando_cargar_muestra_el_error_y_la_partida_sigue(self):
        partida, ruta, controlador, antes = self.preparar()
        with open(ruta_bitacora_de(ruta), "w", encoding="utf-8") as archivo:
            archivo.write("basura\n")
        self.assertTrue(controlador.ejecutar(f"cargar {ruta}"))
        nombre, argumentos = controlador.vista.lineas[-1]
        self.assertEqual(nombre, "mostrar_error")
        self.assertIn("No se pudo cargar", argumentos[0])
        self.assertIgual(antes, controlador)

    def test_fr022_h1_un_error_de_reconstruccion_en_el_comando_cargar_no_cierra_el_juego(self):
        partida, ruta, controlador, antes = self.preparar()
        with mock.patch.object(ReconstructorLinea, "reconstruir", side_effect=ErrorReconstruccion("diverge")):
            self.assertTrue(controlador.ejecutar(f"cargar {ruta}"))
        self.assertEqual(controlador.vista.lineas[-1][0], "mostrar_error")
        self.assertIgual(antes, controlador)

    def test_fr025_h1_el_archivo_cargado_se_puede_reemplazar_tras_un_fallo(self):
        partida, ruta, controlador, antes = self.preparar()
        with mock.patch.object(ReconstructorLinea, "reconstruir", side_effect=SinDatosParaHistoria("esqueleto")):
            with self.assertRaises(SinDatosParaHistoria):
                controlador.cargar(ruta)
        self.assertTrue(controlador.guardar(ruta))      # reemplaza el archivo que se intentó cargar


class PruebasCopiasPrivadas(BaseCargar):

    def cargada(self):
        partida = self.partida_jugada()
        ruta = self.guardada(partida)
        controlador = self.controlador_nuevo(partida)
        controlador.cargar(ruta)
        return partida, ruta, controlador

    def test_fr025_cargar_deja_una_copia_privada_por_epoca_en_una_carpeta_propia(self):
        partida, ruta, controlador = self.cargada()
        copia = controlador.linea.epocas_ruta[-1]
        self.assertTrue(os.path.isfile(copia))
        self.assertNotEqual(os.path.abspath(copia), os.path.abspath(ruta))
        self.assertNotEqual(os.path.abspath(os.path.dirname(copia)), os.path.abspath(partida.carpeta.name))

    def test_fr025_cerrar_borra_las_copias_privadas(self):
        partida, ruta, controlador = self.cargada()
        copia = controlador.linea.epocas_ruta[-1]
        controlador.ejecutar("esperar")
        historia(controlador, 50)                       # un clon abre la copia
        controlador._cerrar()
        self.assertFalse(os.path.exists(copia))
        self.assertFalse(os.path.exists(os.path.dirname(copia)))
        self.assertIsNone(controlador.linea)

    def test_fr025_una_partida_nueva_borra_las_copias_de_la_anterior(self):
        partida, ruta, controlador = self.cargada()
        copia = controlador.linea.epocas_ruta[-1]
        controlador.nueva_partida(CRIPTA_NIEBLA, 5)
        self.assertFalse(os.path.exists(copia))
        self.assertIsNotNone(controlador.linea)
        self.assertEqual(controlador.linea.acciones, 0)

    def test_fr025_cargar_otra_partida_borra_las_copias_de_la_anterior(self):
        partida, ruta, controlador = self.cargada()
        primera = controlador.linea.epocas_ruta[-1]
        segundo = os.path.join(partida.carpeta.name, "segundo.cripta")
        controlador.ejecutar("esperar")
        self.assertTrue(controlador.guardar(segundo))
        controlador.cargar(segundo)
        self.assertFalse(os.path.exists(primera))
        self.assertTrue(os.path.isfile(controlador.linea.epocas_ruta[-1]))

    def test_fr025_el_comando_guardar_y_cargar_desde_la_misma_partida(self):
        partida = self.partida_jugada()
        controlador = partida.controlador
        self.addCleanup(controlador._cerrar)      # suelta el archivo cargado antes de borrar la carpeta
        ruta = os.path.join(partida.carpeta.name, "mismo.cripta")
        self.assertTrue(controlador.ejecutar(f"guardar {ruta}"))
        antes = historia(controlador, 25)
        controlador.cargar(ruta)          # la misma partida recarga su propio guardado con otra bitácora
        self.assertEqual(historia(controlador, 25), antes)


if __name__ == "__main__":
    unittest.main()
