# `main.py --cargar`: códigos de salida 1 y 2 con la línea de tiempo (spec 004, T086; FR-024, FR-031, PR-11;
# contracts/comandos-historia.md: «Cargar sin datos locales» y «Códigos de salida»).
#   código 1: `ErrorReconstruccion`, `SinDatosParaHistoria` (también al cargar: no se carga nada), `ReferenciaInvalida`,
#             `--cargar F --checkpoint-cada K` y `--cargar F --bitacora F.log`, todos como `! Error: ...`;
#   código 2: la línea que no coincide con la partida, un bloque de línea inválido, y los formatos de otras versiones, como
#             `! Error: Versión incompatible: ...`.
# En ningún caso se carga nada: la bitácora de la continuación no se crea y el archivo guardado queda igual. Sin red.

import contextlib
import io
import os
import sys
import unittest
from unittest import mock

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import main
from Controlador.ControladorPartida import ControladorPartida, ruta_bitacora_de
from Controlador.ReconstructorLinea import ReconstructorLinea
from Gestor.GestorHistorico import SinDatosParaHistoria
from Modelo.LineaTiempo import ErrorReconstruccion, ReferenciaInvalida
from Persistencia.RegistroLinea import RegistroLinea
from Vista.VistaConsola import VistaConsola
from tests.utiles_linea import (archivo_con_linea, copia_sin_datos, crpt_con_version, insertar_bloque_linea, leer_bloque_linea,
                                partida_linea)


def sin_entrada(_mensaje):
    raise EOFError


def leer(ruta):
    with open(ruta, "rb") as archivo:
        return archivo.read()


class BaseCargarCli(unittest.TestCase):

    def setUp(self):
        self.partida = partida_linea()
        self.addCleanup(self.partida.cerrar)
        for comando in ("esperar", "mover E", "esperar", "mover O"):
            self.partida.controlador.ejecutar(comando)
        self.base = self.partida.carpeta.name
        self.guardado = os.path.join(self.base, "guardado.cripta")
        self.assertTrue(self.partida.controlador.guardar(self.guardado))
        self.partida.controlador._cerrar()
        self.continuacion = os.path.join(self.base, "continuacion.log")

    def copia_de(self, origen, nombre):
        """Copia de `origen` con su bitácora al lado, para alterarla sin tocar el guardado original."""
        destino = os.path.join(self.base, nombre)
        with open(origen, "rb") as fuente, open(destino, "wb") as archivo:
            archivo.write(fuente.read())
        with open(ruta_bitacora_de(origen), "rb") as fuente, open(ruta_bitacora_de(destino), "wb") as archivo:
            archivo.write(fuente.read())
        return destino

    def correr(self, *argumentos, paquete=None, datos=None, parches=()):
        argv = ["main.py", "--offline", paquete or self.partida.paquete, "--datos-locales", datos or self.partida.ruta_datos,
                "--puntajes", os.path.join(self.base, "puntajes.txt"), *argumentos]
        salida = io.StringIO()
        with contextlib.ExitStack() as pila:
            pila.enter_context(mock.patch.object(main, "VistaConsola", lambda: VistaConsola(entrada=sin_entrada)))
            pila.enter_context(mock.patch.object(main, "configurar_logging", lambda *a, **k: None))
            pila.enter_context(mock.patch.object(sys, "argv", argv))
            pila.enter_context(contextlib.redirect_stdout(salida))
            for parche in parches:
                pila.enter_context(parche)
            codigo = main.main()
        return codigo, salida.getvalue()

    def assertNoSeCargoNada(self, archivo=None):
        self.assertFalse(os.path.exists(self.continuacion), "se creó la bitácora de la continuación")
        self.assertFalse(os.path.exists(os.path.join(self.base, "puntajes.txt")))
        if archivo is not None:
            self.assertTrue(os.path.exists(archivo))


class PruebasCargarCorrecto(BaseCargarCli):

    def test_fr022_cargar_con_su_linea_sale_con_codigo_0(self):
        codigo, texto = self.correr("--cargar", self.guardado, "--bitacora", self.continuacion)
        self.assertEqual(codigo, 0, texto)
        self.assertIn(f"Partida cargada desde {self.guardado}", texto)
        self.assertTrue(os.path.exists(self.continuacion))

    def test_fr022_cargar_un_archivo_sin_bloque_de_linea_tambien_sale_con_codigo_0(self):
        sin_linea = insertar_bloque_linea(self.guardado, os.path.join(self.base, "sin_linea.cripta"), b"")
        self.assertEqual(leer_bloque_linea(sin_linea), b"")
        with open(ruta_bitacora_de(self.guardado), "rb") as fuente, open(ruta_bitacora_de(sin_linea), "wb") as archivo:
            archivo.write(fuente.read())
        codigo, texto = self.correr("--cargar", sin_linea, "--bitacora", self.continuacion)
        self.assertEqual(codigo, 0, texto)      # largo línea = 0: la línea empieza en la carga

    def test_fr024_una_linea_vacia_pero_valida_no_coincide_con_una_partida_que_ya_jugo(self):
        vacia = insertar_bloque_linea(self.guardado, os.path.join(self.base, "vacia.cripta"), RegistroLinea(50, []).to_bytes())
        with open(ruta_bitacora_de(self.guardado), "rb") as fuente, open(ruta_bitacora_de(vacia), "wb") as archivo:
            archivo.write(fuente.read())
        codigo, texto = self.correr("--cargar", vacia, "--bitacora", self.continuacion)
        self.assertEqual(codigo, 2, texto)
        self.assertIn("la línea de tiempo no coincide con la partida", texto)


class PruebasCodigoUno(BaseCargarCli):

    def assertError(self, codigo, texto, empieza):
        self.assertEqual(codigo, 1, texto)
        self.assertTrue(texto.startswith("! Error: "), texto)
        self.assertTrue(texto.startswith(f"! Error: {empieza}"), texto)

    def test_fr025_sin_datos_locales_es_error_de_datos_y_no_se_carga_nada(self):
        copia = copia_sin_datos(self.partida, "datos")
        self.addCleanup(copia.cerrar)
        guardado = copia.ruta("guardado.cripta")
        continuacion = copia.ruta("continuacion.log")
        antes = leer(guardado)
        codigo, texto = self.correr("--cargar", guardado, "--bitacora", continuacion, paquete=copia.paquete,
                                    datos=copia.ruta_datos)
        self.assertError(codigo, texto, "No se puede reconstruir sin nuevas solicitudes: faltan datos locales (")
        self.assertFalse(os.path.exists(continuacion))
        self.assertEqual(leer(guardado), antes)

    def test_fr025_sin_el_paquete_pero_con_los_datos_locales_da_codigo_1_porque_la_fuente_no_tiene_la_version(self):
        # `cargar_partida` pide SIEMPRE la versión de la cripta a la fuente (para comprobar que el archivo es de esta versión);
        # sin paquete la fuente offline no la tiene y lanza `Falta el archivo para ...`: un RuntimeError, código 1, antes de
        # reconstruir nada. Detalle y variantes (comando `cargar`, `--replay`) en tests/test_linea_carga_sin_datos.py (T078).
        copia = copia_sin_datos(self.partida, "paquete")
        self.addCleanup(copia.cerrar)
        guardado = copia.ruta("guardado.cripta")
        with mock.patch.object(ReconstructorLinea, "reconstruir", side_effect=AssertionError("llegó a reconstruir")):
            codigo, texto = self.correr("--cargar", guardado, "--bitacora", copia.ruta("continuacion.log"),
                                        paquete=copia.paquete, datos=copia.ruta_datos)
        self.assertError(codigo, texto, "Falta el archivo para /criptas/cripta-niebla/version: ")
        self.assertFalse(os.path.exists(copia.ruta("continuacion.log")))

    def test_fr024_sin_datos_para_historia_error_de_reconstruccion_y_referencia_invalida_dan_codigo_1(self):
        casos = (SinDatosParaHistoria("esqueleto de la cripta x"), ErrorReconstruccion("el sello no coincide"),
                 ReferenciaInvalida("La acción 9 no existe"))
        for error in casos:
            with self.subTest(error=type(error).__name__):
                with mock.patch.object(ControladorPartida, "cargar", side_effect=error):
                    codigo, texto = self.correr("--cargar", self.guardado, "--bitacora", self.continuacion)
                self.assertError(codigo, texto, str(error))
                self.assertNoSeCargoNada(self.guardado)

    def test_fr025_un_error_de_reconstruccion_dentro_de_la_carga_da_codigo_1_y_no_carga_nada(self):
        for error in (SinDatosParaHistoria("contenido de las salas 1"), ErrorReconstruccion("diverge")):
            with self.subTest(error=type(error).__name__):
                with mock.patch.object(ReconstructorLinea, "reconstruir", side_effect=error):
                    codigo, texto = self.correr("--cargar", self.guardado, "--bitacora", self.continuacion)
                self.assertError(codigo, texto, str(error))
                self.assertNoSeCargoNada(self.guardado)

    def test_fr031_cargar_con_checkpoint_cada_es_error_de_uso_y_no_carga_nada(self):
        codigo, texto = self.correr("--cargar", self.guardado, "--checkpoint-cada", "10", "--bitacora", self.continuacion)
        self.assertError(codigo, texto, "--checkpoint-cada no se puede usar al cargar una partida: rige el valor guardado "
                                        "en el archivo.")
        self.assertNoSeCargoNada(self.guardado)

    def test_fr017_cargar_con_la_bitacora_del_guardado_es_error_de_uso(self):
        codigo, texto = self.correr("--cargar", self.guardado, "--bitacora", ruta_bitacora_de(self.guardado))
        self.assertError(codigo, texto, "la bitácora no puede ser ")
        codigo, texto = self.correr("--cargar", self.guardado, "--bitacora", self.guardado)
        self.assertError(codigo, texto, "la bitácora no puede ser ")

    def test_fr025_un_archivo_que_no_existe_da_codigo_1(self):
        codigo, texto = self.correr("--cargar", os.path.join(self.base, "no_existe.cripta"), "--bitacora", self.continuacion)
        self.assertEqual(codigo, 1, texto)
        self.assertTrue(texto.startswith("! Error: "), texto)
        self.assertNoSeCargoNada()


class PruebasCodigoDos(BaseCargarCli):

    def assertVersionIncompatible(self, codigo, texto, detalle=None):
        self.assertEqual(codigo, 2, texto)
        self.assertTrue(texto.startswith("! Error: Versión incompatible: "), texto)
        if detalle is not None:
            self.assertEqual(texto, f"! Error: Versión incompatible: {detalle}\n")

    def test_fr024_la_linea_que_no_coincide_con_la_partida_da_codigo_2(self):
        alterado = archivo_con_linea(self.guardado, os.path.join(self.base, "sello.cripta"),
                                     RegistroLinea.from_bytes(leer_bloque_linea(self.guardado)), "sello")
        with open(ruta_bitacora_de(self.guardado), "rb") as fuente, open(ruta_bitacora_de(alterado), "wb") as archivo:
            archivo.write(fuente.read())
        codigo, texto = self.correr("--cargar", alterado, "--bitacora", self.continuacion)
        self.assertVersionIncompatible(codigo, texto, "la línea de tiempo no coincide con la partida")
        self.assertNoSeCargoNada(alterado)

    def test_fr024_un_bloque_de_linea_invalido_da_codigo_2(self):
        for modo in ("truncado", "tipo"):
            with self.subTest(modo=modo):
                alterado = archivo_con_linea(self.guardado, os.path.join(self.base, f"{modo}.cripta"),
                                             RegistroLinea.from_bytes(leer_bloque_linea(self.guardado)), modo)
                with open(ruta_bitacora_de(self.guardado), "rb") as fuente, \
                        open(ruta_bitacora_de(alterado), "wb") as archivo:
                    archivo.write(fuente.read())
                codigo, texto = self.correr("--cargar", alterado, "--bitacora", self.continuacion)
                self.assertVersionIncompatible(codigo, texto)
                self.assertNoSeCargoNada(alterado)

    def test_fr024_los_formatos_de_otras_versiones_dan_codigo_2(self):
        for version in (1, 2, 4, 99):
            with self.subTest(version=version):
                otro = crpt_con_version(self.guardado, os.path.join(self.base, f"v{version}.cripta"), version)
                codigo, texto = self.correr("--cargar", otro, "--bitacora", self.continuacion)
                self.assertVersionIncompatible(codigo, texto)
                self.assertNoSeCargoNada(otro)

    def test_fr024_una_cripta_de_otra_version_da_codigo_2(self):
        otro = os.path.join(self.base, "otra_cripta.cripta")
        with open(self.guardado, "rb") as fuente:
            datos = bytearray(fuente.read())
        marca = datos.find(b"v1")                       # la versión de la cripta del encabezado
        self.assertGreater(marca, 0)
        datos[marca:marca + 2] = b"vx"
        with open(otro, "wb") as archivo:
            archivo.write(bytes(datos))
        codigo, texto = self.correr("--cargar", otro, "--bitacora", self.continuacion)
        self.assertVersionIncompatible(codigo, texto)
        self.assertNoSeCargoNada(otro)


if __name__ == "__main__":
    unittest.main()
