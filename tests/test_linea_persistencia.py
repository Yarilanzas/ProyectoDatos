# Guardar y cargar conservan la línea completa (spec 004, Historia 5; T070 a T077; FR-022, FR-023, FR-024, FR-025, FR-030,
# FR-031, SC-005, SC-008). Cada escenario usa un controlador y un gestor **nuevos sobre la misma carpeta de datos locales**
# (equivale a un proceso nuevo) y una partida jugada con el controlador, con todo lo que cuenta dentro del guion (los pergaminos
# se recogen del suelo con acciones): la reproducción desde cero tiene que llegar al mismo estado. Sin red.
#
#   T070 US5-1   historia <t> para t en 0..800 igual antes y después de guardar y cargar
#   T071 US5-2   cargar, continuar, consultar antes y después del guardado; guardar y cargar otra vez, tres rondas
#   T072 US4-5   `--replay --hasta` de la bitácora de la partida continuada da la misma línea y los mismos resúmenes
#   T073 US5-3   un archivo de la Parte I (formato 1 o 2) se rechaza con Versión incompatible y código 2
#   T074 US5-4   tras cargar, `retroceder` se comporta como en la Parte I (el historial no se guardó)
#   T075 US5-5   versión intermedia o desconocida, línea alterada, bloque truncado, tipo desconocido y K < 1: se rechazan
#   T076 US5-6   el archivo declara el formato 3 y el README lo documenta con la línea (omitida hasta T115)
#   T077 US5-7   `--cargar` con `--checkpoint-cada` falla; sin la opción rige el K del archivo; el comando `cargar` lo adopta

import contextlib
import io
import os
import struct
import sys
import unittest
from unittest import mock

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import main
from Controlador.ConsultaHistoria import ConsultaHistoria
from Controlador.ControladorPartida import ControladorPartida, ruta_bitacora_de
from Modelo.LineaTiempo import TIPO_CARGA, TIPO_RETROCESO
from Persistencia.FormatoBinario import FORMATO_PREFIJO, VERSION_FORMATO, VersionIncompatible
from Persistencia.RegistroLinea import RegistroLinea
from Vista.VistaConsola import VistaConsola
from tests.test_integracion import VistaFalsa
from tests.test_linea_cargar import BaseCargar, COMANDOS, historia, leer
from tests.test_linea_replay_hasta import por_main
from tests.utiles_linea import archivo_con_linea, crpt_con_version, insertar_bloque_linea, leer_bloque_linea
from tests.utiles_niebla import CRIPTA_NIEBLA

CON_PERGAMINO = ["recoger {pergamino}", "esperar", "mover S", "esperar"]   # el pergamino queda en el inventario
LARGA = COMANDOS + ["esperar", "mover E", "esperar", "mover O"] * 4      # el reloj pasa de 800


def sin_entrada(_mensaje):
    raise EOFError


class BasePersistencia(BaseCargar):

    def partida_larga(self, k=None):
        partida = self.partida_jugada(k=k, comandos=LARGA)
        self.assertGreater(partida.motor.reloj, 800)
        return partida

    def correr_main(self, partida, *argumentos, parches=()):
        argv = ["main.py", "--offline", partida.paquete, "--datos-locales", partida.ruta_datos,
                "--puntajes", os.path.join(partida.carpeta.name, "puntajes.txt"), *argumentos]
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


class PruebasGuardarYCargar(BasePersistencia):

    def test_fr022_sc005_us5_1_historia_de_0_a_800_es_identica_tras_guardar_y_cargar(self):
        partida = self.partida_larga()
        antes = [historia(partida.controlador, t) for t in range(0, 801)]
        ruta = self.guardada(partida)
        partida.controlador._cerrar()
        controlador = self.controlador_nuevo(partida)
        controlador.cargar(ruta)
        diferentes = [t for t in range(0, 801) if historia(controlador, t) != antes[t]]
        self.assertEqual(diferentes, [], "instantes que cambiaron tras cargar")
        self.assertEqual(len(antes), 801)

    def test_fr022_us5_1_tambien_los_numerales_y_los_instantes_hasta_el_final(self):
        partida = self.partida_larga()
        controlador = partida.controlador
        final = controlador.linea.reloj_actual
        instantes = list(range(0, final, 7))
        numerales = list(range(1, controlador.linea.acciones + 2))
        antes = [historia(controlador, t) for t in instantes] + [historia(controlador, f"#{k}") for k in numerales]
        ruta = self.guardada(partida)
        nuevo = self.controlador_nuevo(partida)
        nuevo.cargar(ruta)
        despues = [historia(nuevo, t) for t in instantes] + [historia(nuevo, f"#{k}") for k in numerales]
        # `#n+1` es «estado actual» y su título dice lo mismo antes y después: el contenido es el del motor cargado
        self.assertEqual(despues, antes)

    def test_fr025_us5_2_cargar_continuar_consultar_guardar_y_cargar_de_nuevo_tres_rondas(self):
        partida = self.partida_jugada()
        ruta = self.guardada(partida)
        for ronda in range(3):
            controlador = self.controlador_nuevo(partida, f"ronda_{ronda}.log")
            controlador.cargar(ruta)
            guardado = controlador.linea.reloj_actual
            anterior = guardado - 120                      # un instante anterior al guardado
            for comando in ("esperar", "esperar", "esperar"):      # sin moverse: no se llega a la salida
                controlador.ejecutar(comando)
            posterior = guardado + 60                      # y uno posterior (dentro de la primera acción tras continuar)
            self.assertLess(posterior, controlador.linea.reloj_actual)
            esperado_antes = historia(controlador, anterior)
            esperado_despues = historia(controlador, posterior)
            self.assertNotEqual(esperado_antes, esperado_despues)
            ruta = os.path.join(partida.carpeta.name, f"ronda_{ronda}.cripta")
            self.assertTrue(controlador.guardar(ruta))
            controlador._cerrar()
            siguiente = self.controlador_nuevo(partida, f"verifica_{ronda}.log")
            siguiente.cargar(ruta)
            self.assertEqual(historia(siguiente, anterior), esperado_antes, f"ronda {ronda}, antes del guardado")
            self.assertEqual(historia(siguiente, posterior), esperado_despues, f"ronda {ronda}, después del guardado")
            siguiente._cerrar()

    def test_fr025_us5_2_cada_ronda_agrega_una_carga_al_guion(self):
        partida = self.partida_jugada()
        ruta = self.guardada(partida)
        for ronda in range(1, 4):
            controlador = self.controlador_nuevo(partida, f"r{ronda}.log")
            controlador.cargar(ruta)
            self.assertEqual(controlador.linea.guion_tipo.count(TIPO_CARGA), ronda)
            controlador.ejecutar("esperar")
            ruta = os.path.join(partida.carpeta.name, f"r{ronda}.cripta")
            self.assertTrue(controlador.guardar(ruta))
            controlador._cerrar()


class EspiaDeLinea(ConsultaHistoria):
    """Se queda con el guion de la línea que arma `--replay --hasta` antes de que se cierre."""

    registros = []

    def al_terminar(self, motor):
        EspiaDeLinea.registros.append(self.linea.a_registro())
        super().al_terminar(motor)


class PruebasReplayDeLaPartidaContinuada(BasePersistencia):

    def test_fr025_fr030_us4_5_replay_hasta_da_la_misma_linea_y_los_mismos_resumenes(self):
        partida = self.partida_larga()
        ruta = self.guardada(partida)
        partida.controlador._cerrar()
        continuada = os.path.join(partida.carpeta.name, "continuada.log")
        controlador = ControladorPartida(partida.nuevo_gestor(iniciado=False), VistaFalsa(), continuada)
        self.addCleanup(controlador._cerrar)
        controlador.cargar(ruta)
        for comando in ("esperar", "mover E", "esperar", "retroceder", "esperar", "mover O", "esperar"):
            controlador.ejecutar(comando)
        controlador.bitacora.cerrar()
        final = controlador.linea.reloj_actual

        # la misma línea: el guion que arma el replay es el de la partida continuada
        EspiaDeLinea.registros = []
        gestor = partida.nuevo_gestor(iniciado=False)
        EspiaDeLinea(gestor, 0, controlador.linea.k).reproducir(continuada)
        self.assertEqual(EspiaDeLinea.registros[0], controlador.linea.a_registro())

        # los mismos resúmenes para todo t (por el programa de verdad, `main --replay --hasta`)
        for t in list(range(0, final, 53)) + [final - 1]:
            with self.subTest(t=t):
                self.assertEqual(por_main(partida, t, bitacora=continuada), historia(controlador, t))
        self.assertEqual(por_main(partida, final, bitacora=continuada)[1:], historia(controlador, final)[1:])


class PruebasRechazos(BasePersistencia):
    """T073 y T075: lo que no se puede cargar se rechaza con Versión incompatible, sin cargar nada."""

    def preparar(self):
        partida = self.partida_jugada()
        ruta = self.guardada(partida)
        controlador = self.con_una_partida_en_curso(partida)
        return partida, ruta, controlador, self.foto(controlador)

    def copia_con_bitacora(self, partida, origen, destino):
        with open(ruta_bitacora_de(origen), "rb") as fuente, open(ruta_bitacora_de(destino), "wb") as archivo:
            archivo.write(fuente.read())
        return destino

    def assertRechazada(self, controlador, ruta, antes):
        with self.assertRaises(VersionIncompatible):
            controlador.cargar(ruta)
        self.assertIgual(antes, controlador)

    def test_fr024_sc008_us5_3_un_archivo_de_la_parte_i_se_rechaza_con_codigo_2_sin_cargar_nada(self):
        partida, ruta, controlador, antes = self.preparar()
        for version in (1, 2):
            with self.subTest(version=version):
                otro = crpt_con_version(ruta, os.path.join(partida.carpeta.name, f"parte1_v{version}.cripta"), version)
                self.assertRechazada(controlador, otro, antes)
                codigo, texto = self.correr_main(partida, "--cargar", otro, "--bitacora",
                                                 os.path.join(partida.carpeta.name, "nueva.log"))
                self.assertEqual(codigo, 2, texto)
                self.assertTrue(texto.startswith("! Error: Versión incompatible: "), texto)
                self.assertFalse(os.path.exists(os.path.join(partida.carpeta.name, "nueva.log")))

    def variantes(self, partida, ruta):
        """Todo lo que T075 pide rechazar: (nombre, ruta del archivo alterado)."""
        base = partida.carpeta.name
        registro = RegistroLinea.from_bytes(leer_bloque_linea(ruta))
        resultado = []
        for version in (0, 1, 2, 4, 99):
            resultado.append((f"versión {version}", crpt_con_version(ruta, os.path.join(base, f"v{version}.cripta"), version)))
        for modo in ("sello", "truncado", "tipo"):
            resultado.append((f"línea {modo}", archivo_con_linea(ruta, os.path.join(base, f"{modo}.cripta"), registro, modo)))
        resultado.append(("K < 1", insertar_bloque_linea(ruta, os.path.join(base, "k0.cripta"), struct.pack("<II", 0, 0))))
        return resultado

    def test_fr024_sc008_us5_5_cada_archivo_alterado_se_rechaza_en_el_100_por_ciento_de_los_intentos(self):
        partida, ruta, controlador, antes = self.preparar()
        variantes = self.variantes(partida, ruta)
        self.assertEqual(len(variantes), 9)
        for nombre, otro in variantes:
            if os.path.basename(otro).startswith("v"):
                continue                        # la copia de bitácora de esos no importa: la versión se rechaza antes
            self.copia_con_bitacora(partida, ruta, otro)
        for intento in range(3):                # los tres intentos de cada uno dan siempre lo mismo
            for nombre, otro in variantes:
                with self.subTest(intento=intento, variante=nombre):
                    self.assertRechazada(controlador, otro, antes)

    def test_fr024_sc008_us5_5_por_main_todos_salen_con_codigo_2_y_no_cargan_nada(self):
        partida, ruta, controlador, antes = self.preparar()
        controlador._cerrar()
        for nombre, otro in self.variantes(partida, ruta):
            self.copia_con_bitacora(partida, ruta, otro)
            continuacion = os.path.join(partida.carpeta.name, "continuacion.log")
            with self.subTest(variante=nombre):
                codigo, texto = self.correr_main(partida, "--cargar", otro, "--bitacora", continuacion)
                self.assertEqual(codigo, 2, texto)
                self.assertTrue(texto.startswith("! Error: Versión incompatible: "), texto)
                self.assertFalse(os.path.exists(continuacion))


class PruebasRetrocederTrasCargar(BasePersistencia):

    def test_fr022_fr014_us5_4_tras_cargar_retroceder_es_como_en_la_parte_i(self):
        partida = self.partida_jugada(comandos=CON_PERGAMINO)
        ruta = self.guardada(partida)
        controlador = self.controlador_nuevo(partida)
        controlador.cargar(ruta)
        linea = controlador.linea
        guion = len(linea.guion_tipo)
        acciones = linea.acciones
        reloj = controlador.motor.reloj

        # el historial de retroceso no se guardó: no hay nada que revertir
        controlador.ejecutar("retroceder")
        self.assertEqual(controlador.vista.lineas[-1], ("mostrar_aviso", ("No se pudo realizar esa acción",)))
        self.assertEqual((len(linea.guion_tipo), linea.acciones, controlador.motor.reloj), (guion, acciones, reloj))

        # lo que ocurra después sí se puede revertir, y la línea refleja solo eso
        controlador.ejecutar("esperar")
        self.assertEqual(linea.acciones, acciones + 1)
        controlador.ejecutar("retroceder")
        self.assertEqual(linea.guion_tipo[-1], TIPO_RETROCESO)
        self.assertEqual(linea.acciones, acciones)
        self.assertEqual(controlador.motor.reloj, reloj)
        controlador.ejecutar("retroceder")      # y otra vez: ya no hay pergamino ni nada que revertir
        self.assertEqual(controlador.vista.lineas[-1], ("mostrar_aviso", ("No se pudo realizar esa acción",)))
        self.assertEqual(linea.guion_tipo[-1], TIPO_RETROCESO)
        self.assertEqual(linea.acciones, acciones)
        self.assertEqual(len(linea.guion_tipo), guion + 2)

    def test_fr022_us5_4_el_pasado_anterior_a_la_carga_sigue_consultable_tras_un_retroceso(self):
        partida = self.partida_jugada(comandos=CON_PERGAMINO)
        # (no se usa un instante dentro de la última acción antes del retroceso: ahí la serie de pergaminos ya da el recuento
        # posterior, una limitación conocida de la serie, que guarda un valor por posición)
        antes = [historia(partida.controlador, t) for t in (0, 100, 200)]
        ruta = self.guardada(partida)
        controlador = self.controlador_nuevo(partida)
        controlador.cargar(ruta)
        controlador.ejecutar("esperar")
        controlador.ejecutar("retroceder")
        self.assertEqual(controlador.linea.guion_tipo[-1], TIPO_RETROCESO)
        self.assertEqual([historia(controlador, t) for t in (0, 100, 200)], antes)


def texto_del_readme():
    with open(os.path.join(RAIZ, "README.md"), "rb") as archivo:
        return archivo.read().decode("utf-16")


def readme_documenta_la_linea():
    """True cuando el README (UTF-16) ya documenta el bloque de la línea con su fórmula (el párrafo de T085/T115)."""
    try:
        texto = texto_del_readme()
    except (OSError, UnicodeError):
        return False
    return "largo línea" in texto and "_inicio_salas" in texto


class PruebasFormatoYReadme(BasePersistencia):
    """T076: omitida hasta que el README documente el `CRPT` 3 con la línea (T115); T121 comprueba que ya no lo esté."""

    def test_fr023_el_archivo_guardado_declara_el_formato_3_distinto_del_de_la_parte_i(self):
        partida = self.partida_jugada()
        ruta = self.guardada(partida)
        with open(ruta, "rb") as archivo:
            magia, version = struct.unpack(FORMATO_PREFIJO, archivo.read(struct.calcsize(FORMATO_PREFIJO)))
        self.assertEqual((magia, version), (b"CRPT", VERSION_FORMATO))
        self.assertEqual(VERSION_FORMATO, 3)
        self.assertNotIn(version, (1, 2))

    @unittest.skipUnless(readme_documenta_la_linea(), "espera T115 (README)")
    def test_fr023_us5_6_el_readme_documenta_el_crpt_3_con_el_bloque_de_la_linea(self):
        texto = texto_del_readme()
        self.assertIn("largo línea", texto)
        self.assertIn("_inicio_salas", texto)


class PruebasCheckpointCadaAlCargar(BasePersistencia):
    """T077 (Escenario US5-7)."""

    def test_fr031_us5_7_cargar_con_checkpoint_cada_falla_y_sin_la_opcion_rige_el_k_del_archivo(self):
        partida = self.partida_jugada(k=10)
        ruta = self.guardada(partida)
        antes = leer(ruta)
        continuacion = os.path.join(partida.carpeta.name, "continuacion.log")
        with mock.patch.object(ControladorPartida, "cargar", side_effect=AssertionError("se cargó")):
            codigo, texto = self.correr_main(partida, "--cargar", ruta, "--checkpoint-cada", "5", "--bitacora", continuacion)
        self.assertEqual(codigo, 1, texto)
        self.assertEqual(texto, "! Error: --checkpoint-cada no se puede usar al cargar una partida: rige el valor "
                                "guardado en el archivo.\n")
        self.assertFalse(os.path.exists(continuacion))
        self.assertEqual(leer(ruta), antes)

        # sin la opción: carga, y la línea usa el K del archivo (10), no el de la ejecución (50)
        controladores = []
        original = main.ControladorPartida

        def espia(*argumentos, **opciones):
            controladores.append(original(*argumentos, **opciones))
            return controladores[-1]

        with mock.patch.object(main, "ControladorPartida", espia):
            codigo, texto = self.correr_main(partida, "--cargar", ruta, "--bitacora", continuacion)
        self.assertEqual(codigo, 0, texto)
        self.assertEqual(controladores[0].k_linea, 10)

    def test_fr031_us5_7_el_comando_cargar_adopta_el_k_del_archivo_sin_error(self):
        partida = self.partida_jugada(k=10)
        ruta = self.guardada(partida)
        controlador = self.controlador_nuevo(partida)
        controlador.k_linea = 25
        controlador.nueva_partida(CRIPTA_NIEBLA, 3)
        controlador.ejecutar("esperar")
        self.assertEqual(controlador.linea.k, 25)
        self.assertTrue(controlador.ejecutar(f"cargar {ruta}"))
        self.assertNotEqual(controlador.vista.lineas[-1][0], "mostrar_error")
        self.assertEqual(controlador.linea.k, 10)
        self.assertEqual(controlador.k_linea, 10)

    def test_fr031_un_archivo_sin_k_guardado_usa_el_de_la_ejecucion(self):
        partida = self.partida_jugada(k=10)
        ruta = insertar_bloque_linea(self.guardada(partida), os.path.join(partida.carpeta.name, "sin_linea.cripta"), b"")
        controlador = self.controlador_nuevo(partida)
        controlador.k_linea = 25
        controlador.cargar(ruta)
        self.assertEqual(controlador.linea.k, 25)


if __name__ == "__main__":
    unittest.main()
