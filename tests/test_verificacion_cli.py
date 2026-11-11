# Pruebas de la opción --verificar de main.py (spec 002, T017). Contrato: specs/002-resolubilidad/contracts/
# cli-verificacion.md. Sin red: paquetes offline de tests/generador_criptas.py. Cada prueba cita su FR.

import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

import main
from tests.generador_criptas import escribir_paquete, generar_cripta

CRIPTA_RESOLUBLE = "sint-res"
CRIPTA_NO_RESOLUBLE = "sint-nr"

# bloque «Resoluble» exacto (cli-verificacion.md): k1, k2, k3 en oleadas 1, 2, 3; k3 es la llave de salida
ESPERADO_RESOLUBLE = (
    "La cripta sint-res es resoluble.\n"
    "Orden de obtención de llaves:\n"
    "  1. llave_01 (oleada 1)\n"
    "  2. llave_02 (oleada 2)\n"
    "  3. llave_03 (oleada 3) <- llave de salida\n"
)

ARCHIVOS_DE_PARTIDA = ("partida.cripta", "partida.cripta.log", "partida.log", "puntajes.txt")
INSTANTE_FIJO = 1_600_000_000  # fechas viejas, para notar cualquier escritura


class PruebasVerificacionCli(unittest.TestCase):

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        base = self.temporal.name
        self.paquete_res = os.path.join(base, "paquete_res")
        self.paquete_nr = os.path.join(base, "paquete_nr")
        self.datos = os.path.join(base, "datos")
        self.trabajo = os.path.join(base, "trabajo")
        os.makedirs(self.trabajo)
        escribir_paquete(self.paquete_res, generar_cripta(11, 20, 3, id_cripta=CRIPTA_RESOLUBLE))
        escribir_paquete(self.paquete_nr, generar_cripta(12, 20, 3, resoluble=False, id_cripta=CRIPTA_NO_RESOLUBLE))

        # archivos de partida que ya existían: no se deben crear, tocar ni borrar (FR-015)
        for nombre in ARCHIVOS_DE_PARTIDA:
            ruta = os.path.join(self.trabajo, nombre)
            with open(ruta, "w", encoding="utf-8") as archivo:
                archivo.write("contenido previo\n")
            os.utime(ruta, (INSTANTE_FIJO, INSTANTE_FIJO))

        self.directorio_original = os.getcwd()
        os.chdir(self.trabajo)

    def tearDown(self):
        os.chdir(self.directorio_original)
        self.temporal.cleanup()

    def correr(self, paquete, *argumentos):
        argv = ["main.py", "--offline", paquete, "--datos-locales", self.datos,
                "--bitacora", os.path.join(self.trabajo, "partida.log"),
                "--puntajes", os.path.join(self.trabajo, "puntajes.txt"), *argumentos]
        salida = io.StringIO()
        with mock.patch.object(main, "configurar_logging", lambda *a, **k: None), \
                mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(salida):
            codigo = main.main()
        return codigo, salida.getvalue()

    def foto_de_trabajo(self):
        foto = []
        for carpeta, _, archivos in os.walk(self.trabajo):
            for nombre in archivos:
                ruta = os.path.join(carpeta, nombre)
                estado = os.stat(ruta)
                foto.append((os.path.relpath(ruta, self.trabajo), estado.st_size, estado.st_mtime_ns))
        return sorted(foto)

    def test_fr006_fr016_resoluble_imprime_bloque_exacto_y_devuelve_0(self):
        codigo, texto = self.correr(self.paquete_res, "--verificar", CRIPTA_RESOLUBLE)
        self.assertEqual(codigo, 0)
        self.assertEqual(texto, ESPERADO_RESOLUBLE)

    def test_fr016_no_resoluble_tambien_devuelve_0(self):
        codigo, texto = self.correr(self.paquete_nr, "--verificar", CRIPTA_NO_RESOLUBLE)
        self.assertEqual(codigo, 0)
        self.assertTrue(texto.startswith(f"La cripta {CRIPTA_NO_RESOLUBLE} no es resoluble.\n"), texto)
        self.assertIn("Puerta hacia la sala de salida (sala 20, requiere llave_03):\n", texto)
        self.assertNotIn("! Error", texto)

    def test_fr015_no_crea_ni_modifica_archivos_de_partida(self):
        antes = self.foto_de_trabajo()
        self.correr(self.paquete_res, "--verificar", CRIPTA_RESOLUBLE)
        self.correr(self.paquete_nr, "--verificar", CRIPTA_NO_RESOLUBLE)
        self.assertEqual(self.foto_de_trabajo(), antes)

    def test_fr017_verificar_con_cripta_solo_verifica(self):
        antes = self.foto_de_trabajo()
        codigo, texto = self.correr(self.paquete_res, "--verificar", CRIPTA_RESOLUBLE, "--cripta", "otra-cripta")
        self.assertEqual(codigo, 0)
        self.assertEqual(texto, ESPERADO_RESOLUBLE)
        self.assertEqual(self.foto_de_trabajo(), antes)

    def test_fr025_cripta_inexistente_da_error_y_codigo_1(self):
        codigo, texto = self.correr(self.paquete_res, "--verificar", "no-existe")
        self.assertEqual(codigo, 1)
        self.assertTrue(texto.startswith("! Error: "), texto)
        self.assertNotIn("resoluble", texto)

    def test_fr012_dos_ejecuciones_dan_la_misma_salida(self):
        for paquete, cripta in ((self.paquete_res, CRIPTA_RESOLUBLE), (self.paquete_nr, CRIPTA_NO_RESOLUBLE)):
            with self.subTest(cripta=cripta):
                _, primera = self.correr(paquete, "--verificar", cripta)
                _, segunda = self.correr(paquete, "--verificar", cripta)  # la segunda ya usa la caché
                self.assertEqual(primera, segunda)


if __name__ == "__main__":
    unittest.main()
