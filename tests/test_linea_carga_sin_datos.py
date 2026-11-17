# Cargar sin datos locales (spec 004, T078; Quickstart 15; FR-022, FR-025; contracts/comandos-historia.md, «Cargar sin datos
# locales»). Reproducir el guion al cargar usa un gestor que solo lee del disco: si falta un dato local, la carga termina con
# `! Error: No se puede reconstruir sin nuevas solicitudes: faltan datos locales (<qué>)` y código 1, sin cargar nada. El caso
# `--cargar` con la carpeta de datos borrada ya lo prueban `tests/test_linea_cargar_cli.py` (código y mensaje) y las demás
# pruebas de ese archivo; aquí se agrega lo que falta: el comando `cargar` dentro de una partida, el paquete borrado, las
# solicitudes a la fuente y `--replay` con `@cargar`. Sin red.

import contextlib
import io
import os
import shutil
import sys
import unittest
from unittest import mock

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import main
from API.Fuentes import FuenteDatosOffline
from Controlador.ControladorPartida import ControladorPartida
from Controlador.ReconstructorLinea import ReconstructorLinea
from Gestor.GestorDatos import GestorDatos
from Gestor.GestorHistorico import SinDatosParaHistoria
from Gestor.PreparadorPartida import cargar_partida
from Vista.VistaConsola import VistaConsola
from tests.test_integracion import VistaFalsa
from tests.test_linea_cargar_cli import BaseCargarCli, leer
from tests.utiles_linea import SesionLinea, copia_sin_datos, escribir_bitacora
from tests.utiles_niebla import CRIPTA_NIEBLA

FALTAN = "No se puede reconstruir sin nuevas solicitudes: faltan datos locales ("


class FuenteContada(FuenteDatosOffline):
    """Fuente offline que anota cada ruta pedida."""
    rutas = []

    def _obtener(self, ruta, params=None):
        FuenteContada.rutas.append(ruta)
        return super()._obtener(ruta, params)


def rutas_de_cargar_partida(copia, nombre_guardado="guardado.cripta"):
    """Las rutas que pide `cargar_partida` sola (sin reconstruir nada) sobre una copia con la carpeta de datos borrada."""
    FuenteContada.rutas = []
    gestor = GestorDatos(FuenteContada(copia.paquete), ruta_base=copia.ruta_datos, cache_size=25)
    motor = cargar_partida(copia.ruta(nombre_guardado), gestor)
    motor.restaurador.cerrar()
    return list(FuenteContada.rutas)


class PruebasCargarSinDatosLocales(BaseCargarCli):

    def copia(self, borrar):
        copia = copia_sin_datos(self.partida, borrar)
        self.addCleanup(copia.cerrar)
        return copia

    def test_fr025_cargar_sin_datos_locales_no_hace_ninguna_solicitud_mas_que_la_de_cargar_partida(self):
        # La reconstrucción usa un gestor sin red: lo único que se le pide a la fuente es lo que `cargar_partida` necesita para
        # armar el motor (las versiones, los detalles, el esqueleto); el guion no pide salas ni nada más.
        base = self.copia("datos")
        esperadas = rutas_de_cargar_partida(base)
        self.assertGreater(len(esperadas), 0)

        copia = self.copia("datos")
        guardado = copia.ruta("guardado.cripta")
        FuenteContada.rutas = []
        codigo, texto = self.correr("--cargar", guardado, "--bitacora", copia.ruta("continuacion.log"), paquete=copia.paquete,
                                    datos=copia.ruta_datos, parches=(mock.patch.object(main, "FuenteDatosOffline", FuenteContada),))
        self.assertEqual(codigo, 1, texto)
        self.assertTrue(texto.startswith(f"! Error: {FALTAN}"), texto)
        self.assertEqual(FuenteContada.rutas, esperadas)
        self.assertFalse(os.path.exists(copia.ruta("continuacion.log")))

    def test_fr025_el_gestor_historico_no_llama_a_la_fuente(self):
        # `FuenteSinRed` lanza SinDatosParaHistoria en cualquier método y no cuenta solicitudes
        copia = self.copia("datos")
        gestor = GestorDatos(FuenteContada(copia.paquete), ruta_base=copia.ruta_datos, cache_size=25)
        controlador = ControladorPartida(gestor, VistaFalsa(), copia.ruta("continuacion.log"))
        self.addCleanup(controlador._cerrar)
        FuenteContada.rutas = []
        with self.assertRaises(SinDatosParaHistoria) as contexto:
            controlador.cargar(copia.ruta("guardado.cripta"))
        self.assertTrue(str(contexto.exception).startswith(FALTAN))
        self.assertEqual(rutas_de_cargar_partida(self.copia("datos")), FuenteContada.rutas)

    # ───────────── el comando `cargar` dentro de una partida ─────────────

    def partida_en_curso_sin_su_carpeta_de_datos(self):
        """Un controlador con una partida en curso cuya carpeta de datos locales se vació después de empezar."""
        copia = self.copia("datos")
        gestor = GestorDatos(FuenteContada(copia.paquete), ruta_base=copia.ruta_datos, cache_size=25)
        controlador = ControladorPartida(gestor, VistaFalsa(), copia.ruta("en_curso.log"))
        self.addCleanup(controlador._cerrar)
        controlador.nueva_partida(CRIPTA_NIEBLA, 9)
        controlador.ejecutar("esperar")
        controlador.ejecutar("esperar")
        shutil.rmtree(copia.ruta_datos)
        os.makedirs(copia.ruta_datos)
        return copia, controlador

    def test_fr025_el_comando_cargar_sin_datos_deja_intacta_la_partida_en_curso(self):
        copia, controlador = self.partida_en_curso_sin_su_carpeta_de_datos()
        guardado = copia.ruta("guardado.cripta")
        antes = (controlador.motor, controlador.bitacora, controlador.linea, controlador.observador,
                 controlador.motor.reloj, controlador.linea.a_registro(), leer(controlador.ruta_bitacora))
        guardado_antes = leer(guardado)

        self.assertTrue(controlador.ejecutar(f"cargar {guardado}"))

        nombre, argumentos = controlador.vista.lineas[-1]
        self.assertEqual(nombre, "mostrar_error")
        self.assertTrue(argumentos[0].startswith(f"No se pudo cargar: {FALTAN}"), argumentos[0])
        despues = (controlador.motor, controlador.bitacora, controlador.linea, controlador.observador,
                   controlador.motor.reloj, controlador.linea.a_registro(), leer(controlador.ruta_bitacora))
        for uno, otro in zip(antes[:4], despues[:4]):
            self.assertIs(uno, otro)
        self.assertEqual(antes[4:], despues[4:])
        self.assertEqual(leer(guardado), guardado_antes)
        controlador.ejecutar("esperar")                      # la partida sigue y su bitácora recibe lo nuevo
        self.assertEqual(controlador.linea.acciones, 3)
        self.assertEqual(controlador.motor.reloj, 300)
        with open(controlador.ruta_bitacora, encoding="utf-8") as archivo:
            self.assertTrue(archivo.read().endswith("esperar\n"))
        os.remove(guardado)                                  # ningún archivo de la carga quedó abierto

    def test_fr025_el_comando_cargar_sin_datos_no_pide_nada_a_la_red_ni_a_la_fuente_mas_alla_de_cargar_partida(self):
        copia, controlador = self.partida_en_curso_sin_su_carpeta_de_datos()
        esperadas = rutas_de_cargar_partida(self.copia("datos"))
        FuenteContada.rutas = []
        controlador.ejecutar(f"cargar {copia.ruta('guardado.cripta')}")
        # el gestor de la partida en curso ya tiene en memoria las versiones y los detalles: pide menos que uno en frío, pero
        # nada que `cargar_partida` no pida (el contenido de las salas que el guion visitó no se pide: falta y se rechaza)
        self.assertGreater(len(FuenteContada.rutas), 0)
        for ruta in FuenteContada.rutas:
            self.assertIn(ruta, esperadas)
        self.assertLessEqual(len(FuenteContada.rutas), len(esperadas))

    def test_fr025_la_reconstruccion_que_falla_no_deja_carpetas_ni_copias(self):
        copia, controlador = self.partida_en_curso_sin_su_carpeta_de_datos()
        reconstructores = []
        original = ReconstructorLinea.reconstruir

        def espiar(self_, *argumentos, **opciones):
            reconstructores.append(self_)
            return original(self_, *argumentos, **opciones)

        with mock.patch.object(ReconstructorLinea, "reconstruir", espiar):
            controlador.ejecutar(f"cargar {copia.ruta('guardado.cripta')}")
        self.assertEqual(len(reconstructores), 1)
        self.assertIsNone(reconstructores[0].carpeta)

    # ───────────── el paquete borrado ─────────────

    def test_fr025_cargar_con_el_paquete_borrado_da_codigo_1_porque_cargar_partida_pide_la_version_a_la_fuente(self):
        # Sin paquete la fuente offline no tiene ni la versión de la cripta, que `cargar_partida` pide **siempre** (para
        # comprobar que el archivo es de esta versión): el error es el de la fuente, antes de reconstruir nada. Es código 1
        # (un error de datos), no 2 (no es una versión distinta) ni «faltan datos locales» (eso es del gestor sin red).
        copia = self.copia("paquete")
        self.assertFalse(os.path.exists(copia.paquete))
        self.assertTrue(os.path.isdir(copia.ruta_datos))
        guardado = copia.ruta("guardado.cripta")
        antes = leer(guardado)
        with mock.patch.object(ReconstructorLinea, "reconstruir", side_effect=AssertionError("llegó a reconstruir")):
            codigo, texto = self.correr("--cargar", guardado, "--bitacora", copia.ruta("continuacion.log"),
                                        paquete=copia.paquete, datos=copia.ruta_datos)
        self.assertEqual(codigo, 1, texto)
        self.assertTrue(texto.startswith("! Error: Falta el archivo para /criptas/cripta-niebla/version: "), texto)
        self.assertNotIn(FALTAN, texto)
        self.assertEqual(leer(guardado), antes)
        self.assertFalse(os.path.exists(copia.ruta("continuacion.log")))

    def test_fr025_el_comando_cargar_con_el_paquete_borrado_deja_intacta_la_partida_en_curso(self):
        copia, controlador = self.partida_en_curso_sin_su_carpeta_de_datos()
        shutil.rmtree(copia.paquete, ignore_errors=True)
        antes = (controlador.motor, controlador.bitacora, controlador.linea, controlador.motor.reloj)
        controlador.ejecutar(f"cargar {copia.ruta('guardado.cripta')}")
        self.assertEqual(controlador.vista.lineas[-1][0], "mostrar_error")
        self.assertTrue(controlador.vista.lineas[-1][1][0].startswith("No se pudo cargar: "), controlador.vista.lineas[-1])
        despues = (controlador.motor, controlador.bitacora, controlador.linea, controlador.motor.reloj)
        for uno, otro in zip(antes[:3], despues[:3]):
            self.assertIs(uno, otro)
        self.assertEqual(antes[3], despues[3])


class PruebasReplayConCargarSinDatos(unittest.TestCase):
    """`--replay` de una bitácora con `@cargar`. A diferencia de `--cargar`, el replay usa el gestor normal (con su fuente);
    solo `--hasta` crea además un gestor sin red para los clones, y ese lee lo que el replay acaba de guardar en el disco."""

    def setUp(self):
        self.sesion = SesionLinea(k=3, semilla=4, huellas=False)
        self.addCleanup(self.sesion.cerrar)
        self.sesion.hacer([("esperar", ""), ("mover", "E")])
        self.sesion.guardar_y_cargar(entre=[("esperar", "")])
        self.sesion.hacer([("esperar", ""), ("mover", "O")])
        self.bitacora = escribir_bitacora(self.sesion, os.path.join(self.sesion.partida.carpeta.name, "con_carga.log"))

    def correr(self, copia, *argumentos):
        argv = ["main.py", "--offline", copia.paquete, "--datos-locales", copia.ruta_datos, *argumentos]
        salida = io.StringIO()

        def sin_entrada(_mensaje):
            raise EOFError

        with mock.patch.object(main, "VistaConsola", lambda: VistaConsola(entrada=sin_entrada)), \
                mock.patch.object(main, "configurar_logging", lambda *a, **k: None), \
                mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(salida):
            codigo = main.main()
        return codigo, salida.getvalue()

    def copia(self, borrar):
        copia = copia_sin_datos(self.sesion.partida, borrar)
        self.addCleanup(copia.cerrar)
        return copia

    def test_fr025_replay_con_cargar_sin_la_carpeta_de_datos_pero_con_el_paquete_funciona(self):
        copia = self.copia("datos")
        ruta = copia.ruta("con_carga.log")
        for argumentos in (("--replay", ruta), ("--replay", ruta, "--hasta", "150"), ("--replay", ruta, "--hasta", "99999")):
            with self.subTest(argumentos=argumentos):
                codigo, texto = self.correr(copia, *argumentos)
                self.assertEqual(codigo, 0, texto)

    def test_fr025_replay_con_cargar_sin_el_paquete_da_codigo_1(self):
        copia = self.copia("paquete")
        ruta = copia.ruta("con_carga.log")
        for argumentos in (("--replay", ruta), ("--replay", ruta, "--hasta", "150")):
            with self.subTest(argumentos=argumentos):
                codigo, texto = self.correr(copia, *argumentos)
                self.assertEqual(codigo, 1, texto)
                self.assertTrue(texto.startswith("! Error: "), texto)
                self.assertNotIn("Traceback", texto)


if __name__ == "__main__":
    unittest.main()
