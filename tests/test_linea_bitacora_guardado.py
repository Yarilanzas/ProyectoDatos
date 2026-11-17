# `--bitacora` frente al guardado (spec 004, T080; Quickstart 16; FR-025, FR-030; contracts/formato-bitacora.md,
# «Bitácora igual a <guardado>.log»). Prueba lo que 001-T120 y 001-T121 no prueban, con el comportamiento actual de C:
#   - el comando `guardar` con una bitácora que es `<guardado>.log` **o el propio guardado** se rechaza y la partida sigue,
#     sin escribir el archivo ni su bitácora;
#   - `--cargar F --bitacora F` y `--cargar F --bitacora F.log` salen con código 1 sin cargar nada; rutas equivalentes
#     (`sub/../F`, mayúsculas en Windows, un enlace duro) también: la comparación usa `normcase`, `abspath` y `samefile`;
#   - con una bitácora **distinta**, `--replay --hasta` de la continuación da lo mismo que `historia` en la partida cargada
#     (regla 2: el reloj es global y continuo, sin excepciones). Sin red.

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
from Vista.VistaConsola import VistaConsola
from tests.test_integracion import VistaFalsa
from tests.test_linea_cargar import BaseCargar, historia, leer
from tests.test_linea_replay_hasta import por_main
from tests.utiles_niebla import CRIPTA_NIEBLA


def sin_entrada(_mensaje):
    raise EOFError


class BaseBitacoraGuardado(BaseCargar):

    def controlador_con_bitacora(self, partida, ruta_bitacora, comandos=("esperar", "mover E", "esperar")):
        controlador = ControladorPartida(partida.nuevo_gestor(iniciado=False), VistaFalsa(), ruta_bitacora)
        self.addCleanup(controlador._cerrar)
        controlador.nueva_partida(CRIPTA_NIEBLA, 9)
        for comando in comandos:
            controlador.ejecutar(comando)
        return controlador

    def correr_main(self, partida, *argumentos):
        argv = ["main.py", "--offline", partida.paquete, "--datos-locales", partida.ruta_datos,
                "--puntajes", os.path.join(partida.carpeta.name, "puntajes.txt"), *argumentos]
        salida = io.StringIO()
        with mock.patch.object(main, "VistaConsola", lambda: VistaConsola(entrada=sin_entrada)), \
                mock.patch.object(main, "configurar_logging", lambda *a, **k: None), \
                mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(salida):
            codigo = main.main()
        return codigo, salida.getvalue()


class PruebasGuardarConLaBitacoraDelDestino(BaseBitacoraGuardado):

    def assertRechazadoSinEscribirNada(self, controlador, destino, texto_esperado):
        antes = leer(controlador.ruta_bitacora)
        reloj = controlador.motor.reloj
        existia = os.path.exists(destino)
        antes_destino = leer(destino) if existia else None
        self.assertTrue(controlador.ejecutar(f"guardar {destino}"))         # el juego sigue
        nombre, argumentos = controlador.vista.lineas[-1]
        self.assertEqual(nombre, "mostrar_error")
        self.assertTrue(argumentos[0].startswith("No se pudo guardar: la bitácora no puede ser "), argumentos[0])
        self.assertIn(texto_esperado, argumentos[0])
        self.assertIn("use otra con --bitacora", argumentos[0])
        self.assertEqual(leer(controlador.ruta_bitacora), antes)              # la bitácora quedó como estaba
        self.assertEqual(controlador.motor.reloj, reloj)
        self.assertEqual(os.path.exists(destino), existia)                   # no se escribió el archivo...
        if existia:
            self.assertEqual(leer(destino), antes_destino)
        controlador.ejecutar("esperar")                                       # y se puede seguir jugando
        self.assertEqual(controlador.motor.reloj, reloj + 100)

    def test_fr025_guardar_con_la_copia_de_bitacora_como_bitacora_se_rechaza_y_la_partida_sigue(self):
        partida = self.partida_jugada()
        destino = os.path.join(partida.carpeta.name, "p.cripta")
        controlador = self.controlador_con_bitacora(partida, destino + ".log")
        self.assertRechazadoSinEscribirNada(controlador, destino, destino + ".log")
        self.assertFalse(os.path.exists(destino))

    def test_fr025_guardar_con_el_propio_guardado_como_bitacora_se_rechaza_y_la_partida_sigue(self):
        partida = self.partida_jugada()
        destino = os.path.join(partida.carpeta.name, "p.cripta")
        controlador = self.controlador_con_bitacora(partida, destino)          # la bitácora ES el guardado (regla de f592da4)
        self.assertRechazadoSinEscribirNada(controlador, destino, destino)

    def test_fr025_rutas_equivalentes_se_rechazan_igual(self):
        partida = self.partida_jugada()
        base = partida.carpeta.name
        os.makedirs(os.path.join(base, "sub"), exist_ok=True)
        destino = os.path.join(base, "p.cripta")
        controlador = self.controlador_con_bitacora(partida, os.path.join(base, "sub", "..", "p.cripta.log"))
        self.assertRechazadoSinEscribirNada(controlador, destino, "p.cripta.log")
        self.assertFalse(os.path.exists(destino))

    @unittest.skipUnless(os.path.normcase("A") == "a", "solo donde las rutas no distinguen mayúsculas")
    def test_fr025_mayusculas_distintas_se_rechazan_igual_en_windows(self):
        partida = self.partida_jugada()
        destino = os.path.join(partida.carpeta.name, "p.cripta")
        controlador = self.controlador_con_bitacora(partida, destino.upper() + ".LOG")
        self.assertRechazadoSinEscribirNada(controlador, destino, "p.cripta.log")   # el mensaje nombra la ruta del guardado

    def test_fr025_un_enlace_duro_al_guardado_como_bitacora_se_rechaza_por_samefile(self):
        partida = self.partida_jugada()
        base = partida.carpeta.name
        destino = os.path.join(base, "p.cripta")
        with open(destino, "wb") as archivo:
            archivo.write(b"un guardado anterior")
        enlace = os.path.join(base, "enlace.bin")
        try:
            os.link(destino, enlace)
        except (OSError, NotImplementedError, AttributeError):
            self.skipTest("este sistema de archivos no permite enlaces duros")
        controlador = ControladorPartida(partida.nuevo_gestor(iniciado=False), VistaFalsa(), os.path.join(base, "otra.log"))
        self.addCleanup(controlador._cerrar)
        controlador.nueva_partida(CRIPTA_NIEBLA, 9)
        controlador.ruta_bitacora = enlace      # la bitácora es otro nombre del mismo archivo que el guardado
        with self.assertRaises(ValueError):
            controlador.guardar(destino)
        self.assertEqual(leer(destino), b"un guardado anterior")


class PruebasCargarConLaBitacoraDelGuardado(BaseBitacoraGuardado):

    def assertRechazado(self, partida, guardado, bitacora):
        antes = leer(guardado)
        codigo, texto = self.correr_main(partida, "--cargar", guardado, "--bitacora", bitacora)
        self.assertEqual(codigo, 1, texto)
        self.assertTrue(texto.startswith("! Error: la bitácora no puede ser "), texto)
        self.assertIn("use otra con --bitacora", texto)
        self.assertEqual(leer(guardado), antes)                               # el guardado no se tocó
        self.assertNotIn("Partida cargada", texto)

    def test_fr025_cargar_con_la_copia_de_bitacora_del_guardado_sale_con_codigo_1(self):
        partida = self.partida_jugada()
        guardado = self.guardada(partida)
        antes_log = leer(ruta_bitacora_de(guardado))
        self.assertRechazado(partida, guardado, ruta_bitacora_de(guardado))
        self.assertEqual(leer(ruta_bitacora_de(guardado)), antes_log)

    def test_fr025_cargar_con_el_propio_guardado_como_bitacora_sale_con_codigo_1_y_no_lo_destruye(self):
        partida = self.partida_jugada()
        guardado = self.guardada(partida)
        self.assertRechazado(partida, guardado, guardado)
        self.assertTrue(leer(guardado).startswith(b"CRPT"))

    def test_fr025_cargar_con_rutas_equivalentes_tambien(self):
        partida = self.partida_jugada()
        guardado = self.guardada(partida)
        os.makedirs(os.path.join(partida.carpeta.name, "sub"), exist_ok=True)
        self.assertRechazado(partida, guardado, os.path.join(partida.carpeta.name, "sub", "..", "guardado.cripta"))
        self.assertRechazado(partida, guardado, os.path.join(partida.carpeta.name, "sub", "..", "guardado.cripta.log"))

    @unittest.skipUnless(os.path.normcase("A") == "a", "solo donde las rutas no distinguen mayúsculas")
    def test_fr025_cargar_con_mayusculas_distintas_tambien_en_windows(self):
        partida = self.partida_jugada()
        guardado = self.guardada(partida)
        self.assertRechazado(partida, guardado, guardado.upper())
        self.assertRechazado(partida, guardado, ruta_bitacora_de(guardado).upper())

    def test_fr025_cargar_con_un_enlace_duro_al_guardado_como_bitacora_sale_con_codigo_1(self):
        partida = self.partida_jugada()
        guardado = self.guardada(partida)
        enlace = os.path.join(partida.carpeta.name, "enlace.cripta")
        try:
            os.link(guardado, enlace)
        except (OSError, NotImplementedError, AttributeError):
            self.skipTest("este sistema de archivos no permite enlaces duros")
        self.assertRechazado(partida, guardado, enlace)

    def test_fr025_el_comando_cargar_con_esa_bitacora_solo_se_rechaza_y_la_partida_sigue(self):
        partida = self.partida_jugada()
        guardado = self.guardada(partida)
        controlador = self.controlador_con_bitacora(partida, ruta_bitacora_de(guardado) + ".otra")
        controlador.ruta_bitacora = ruta_bitacora_de(guardado)
        antes = (controlador.motor, controlador.linea, controlador.bitacora)
        self.assertTrue(controlador.ejecutar(f"cargar {guardado}"))
        nombre, argumentos = controlador.vista.lineas[-1]
        self.assertEqual(nombre, "mostrar_error")
        self.assertIn("la bitácora no puede ser", argumentos[0])
        self.assertEqual((controlador.motor, controlador.linea, controlador.bitacora), antes)


class PruebasReplayDeLaContinuacion(BaseBitacoraGuardado):
    """Con una bitácora distinta, el replay de `--hasta` coincide con la línea de la partida cargada: el reloj es global y
    continuo (regla 2 de formato-bitacora.md), sin excepciones por la carga."""

    def test_fr030_replay_hasta_de_la_continuacion_coincide_con_historia(self):
        partida = self.partida_jugada()
        guardado = self.guardada(partida)
        continuacion = os.path.join(partida.carpeta.name, "continuacion.log")
        controlador = ControladorPartida(partida.nuevo_gestor(iniciado=False), VistaFalsa(), continuacion)
        self.addCleanup(controlador._cerrar)
        controlador.cargar(guardado)
        for comando in ("esperar", "mover E", "esperar", "mover O", "esperar"):
            controlador.ejecutar(comando)
        controlador.bitacora.cerrar()
        final = controlador.linea.reloj_actual
        instantes = [t for t in range(0, final + 300, 40)] + [final - 1, final, final + 1]
        self.assertGreater(len(instantes), 10)
        for t in instantes:
            with self.subTest(t=t):
                por_replay = por_main(partida, t, bitacora=continuacion)
                if t < final:
                    self.assertEqual(por_replay, historia(controlador, t))
                elif t == final:
                    self.assertEqual(por_replay[0], f"Historia — estado final (reloj {final})")
                else:
                    self.assertTrue(por_replay[0].startswith(f"La partida termina antes del instante {t}"))

    def test_fr030_la_continuacion_lleva_la_copia_de_la_bitacora_del_guardado_mas_la_carga(self):
        partida = self.partida_jugada()
        guardado = self.guardada(partida)
        copia = leer(ruta_bitacora_de(guardado))
        continuacion = os.path.join(partida.carpeta.name, "continuacion.log")
        controlador = ControladorPartida(partida.nuevo_gestor(iniciado=False), VistaFalsa(), continuacion)
        self.addCleanup(controlador._cerrar)
        controlador.cargar(guardado)
        controlador.ejecutar("esperar")
        controlador.bitacora.cerrar()
        texto = leer(continuacion)
        self.assertTrue(texto.startswith(copia))
        self.assertEqual(texto[len(copia):].replace(b"\r\n", b"\n"), b"@cargar\nesperar\n")   # con fin de línea de Windows o no
        self.assertEqual(leer(ruta_bitacora_de(guardado)), copia)               # la copia del guardado no cambió


if __name__ == "__main__":
    unittest.main()
