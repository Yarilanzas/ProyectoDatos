import os
import tempfile
import unittest

from Bitacora.BitacoraPartida import MARCA, VERSION_BITACORA, BitacoraPartida, leer_bitacora
from Bitacora.Reproductor import Reproductor
from Persistencia.FormatoBinario import VersionIncompatible


class MotorFalso:
    """Motor de mentira, solo anota lo que le piden, el de la persona A tendra la logica real."""
    def __init__(self, cripta_id, semilla):
        self.cripta_id = cripta_id
        self.semilla = semilla
        self.acciones = []

    def ejecutar_accion(self, nombre, argumento):
        self.acciones.append((nombre, argumento))
        return True

class MotorQueRechaza(MotorFalso):
    def ejecutar_accion(self, nombre, argumento):
        self.acciones.append((nombre, argumento))
        return False


class PruebasBitacora(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "partida.log")

    def tearDown(self):
        self.carpeta.cleanup()

    def crear(self):
        return BitacoraPartida(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345)

    def test_persistencia(self): # consistencia de los datos
        with self.crear() as bitacora:
            bitacora.registrar("mover", "N")
            bitacora.registrar("esperar")
            bitacora.registrar("atacar", "Rata gigante #1")
            bitacora.registrar("usar_pergamino")
        encabezado, acciones = leer_bitacora(self.ruta)
        self.assertEqual(encabezado.cripta_id, "cripta-01")
        self.assertEqual(encabezado.version_cripta, "a3f91c")
        self.assertEqual(encabezado.version_catalogo, "cat-2026-08-01")
        self.assertEqual(encabezado.semilla, 12345)
        self.assertEqual(acciones, [("mover", "N"), ("esperar", ""),
                                    ("atacar", "Rata gigante #1"), ("usar_pergamino", "")])

    def test_bitacora_vacia(self):
        self.crear().cerrar()
        self.assertEqual(leer_bitacora(self.ruta)[1], [])

    def test_escritura_inmediata(self): # valida que los datos se consoliden en el disco sin esperar al cierre
        bitacora = self.crear()
        bitacora.registrar("mover", "E")
        with open(self.ruta, encoding="utf-8") as archivo:
            self.assertEqual(archivo.read().splitlines()[-1], "mover E")
        bitacora.cerrar()

    def test_solo_agrega_al_final(self):
        with self.crear() as bitacora:
            bitacora.registrar("mover", "N")
            with open(self.ruta, encoding="utf-8") as archivo:
                antes = archivo.read()
            bitacora.registrar("esperar")
        with open(self.ruta, encoding="utf-8") as archivo:
            despues = archivo.read()
        self.assertTrue(despues.startswith(antes))
        self.assertEqual(despues[len(antes):], "esperar\n")

    def test_sobreescritura(self): # bitacora nueva reemplaza a la anterior
        with self.crear() as bitacora:
            bitacora.registrar("mover", "N")
        self.crear().cerrar()
        self.assertEqual(leer_bitacora(self.ruta)[1], [])

    def test_texto_invalido(self):
        with self.crear() as bitacora:
            with self.assertRaises(ValueError):
                bitacora.registrar("")
            with self.assertRaises(ValueError):
                bitacora.registrar("mover norte")
            with self.assertRaises(ValueError):
                bitacora.registrar("atacar", "e-1\nmover N")
        with self.assertRaises(ValueError):
            BitacoraPartida(self.ruta, "cripta\n01", "a", "b", 1)

    def test_archivo_invalido(self):
        with open(self.ruta, "w", encoding="utf-8") as archivo:
            archivo.write('{"no": "soy una bitacora"}\n')
        with self.assertRaises(VersionIncompatible):
            leer_bitacora(self.ruta)

    def test_version_incompatible(self):
        with open(self.ruta, "w", encoding="utf-8") as archivo:
            archivo.write(f"{MARCA} {VERSION_BITACORA + 1}\ncripta_id=c\nversion_cripta=a\nversion_catalogo=b\nsemilla=1\n---\n")
        with self.assertRaises(VersionIncompatible) as contexto:
            leer_bitacora(self.ruta)
        self.assertIn(str(VERSION_BITACORA + 1), str(contexto.exception))

    def test_encabezado_incompleto(self):
        with open(self.ruta, "w", encoding="utf-8") as archivo:
            archivo.write(f"{MARCA} {VERSION_BITACORA}\ncripta_id=c\nversion_cripta=a\n")
        with self.assertRaises(VersionIncompatible):
            leer_bitacora(self.ruta)

    def test_semilla_invalida(self): # semilla no numerica
        with open(self.ruta, "w", encoding="utf-8") as archivo:
            archivo.write(f"{MARCA} {VERSION_BITACORA}\ncripta_id=c\nversion_cripta=a\nversion_catalogo=b\nsemilla=abc\n---\n")
        with self.assertRaises(VersionIncompatible):
            leer_bitacora(self.ruta)


    def test_replay_se_detiene_si_el_motor_rechaza(self): # comprueba que un rechazo explícito no se ignora
        with self.crear() as bitacora:
            bitacora.registrar("mover", "N")

        reproductor = Reproductor(
            lambda cripta_id, semilla: MotorQueRechaza(
                cripta_id, semilla
            ),
            "a3f91c",
            "cat-2026-08-01"
        )

        with self.assertRaisesRegex(ValueError, "motor rechazó la acción"):
            reproductor.reproducir(self.ruta)

    def test_rechaza_nombres_y_argumentos_invalidos(self):
        with self.crear() as bitacora:
            with self.assertRaises(ValueError):
                bitacora.registrar("mover\tN")

            with self.assertRaises(ValueError):
                bitacora.registrar("mover", 123)

            with self.assertRaises(ValueError):
                bitacora.registrar(123, "N")

class PruebasReproductor(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "partida.log")
        with BitacoraPartida(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345) as bitacora:
            bitacora.registrar("mover", "N")
            bitacora.registrar("recoger")
            bitacora.registrar("usar_pergamino")

    def tearDown(self):
        self.carpeta.cleanup()

    def test_reproducion_ordenada(self):
        reproductor = Reproductor(MotorFalso, "a3f91c", "cat-2026-08-01")
        motor = reproductor.reproducir(self.ruta)
        self.assertEqual(motor.cripta_id, "cripta-01")
        self.assertEqual(motor.semilla, 12345)
        self.assertEqual(motor.acciones, [("mover", "N"), ("recoger", ""), ("usar_pergamino", "")])

    def test_dos_reproducciones_iguales(self): # si ante las mismas acciones el motor responde igual
        reproductor = Reproductor(MotorFalso, "a3f91c", "cat-2026-08-01")
        self.assertEqual(reproductor.reproducir(self.ruta).acciones,
                         reproductor.reproducir(self.ruta).acciones)

    def test_cripta_incompatible(self):
        creados = []

        def fabrica(cripta_id, semilla):
            creados.append(cripta_id)
            return MotorFalso(cripta_id, semilla)

        reproductor = Reproductor(fabrica, "otra-version", "cat-2026-08-01")
        with self.assertRaises(VersionIncompatible) as contexto:
            reproductor.reproducir(self.ruta)
        self.assertIn("reproduccion fiel", str(contexto.exception))
        self.assertEqual(creados, [])

    def test_catalogo_incompatible(self):
        reproductor = Reproductor(MotorFalso, "a3f91c", "cat-2027-01-01")
        with self.assertRaises(VersionIncompatible) as contexto:
            reproductor.reproducir(self.ruta)
        self.assertIn("catalogo", str(contexto.exception))

ENCABEZADO_V1 = "CRIPTA-LOG 1\ncripta_id=c\nversion_cripta=a\nversion_catalogo=b\nsemilla=1\n---\n"


class PruebasComentariosYDirectivas(unittest.TestCase):
    """T082: bitácora v2 con comentarios y directivas (FR-030, PR-11; contracts/formato-bitacora.md)."""

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "partida.log")

    def tearDown(self):
        self.carpeta.cleanup()

    def crear(self):
        return BitacoraPartida(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345)

    def lineas(self):
        with open(self.ruta, encoding="utf-8") as archivo:
            lineas = archivo.read().splitlines()
        return lineas[lineas.index("---") + 1:]

    def escribir(self, cuerpo, encabezado=None):
        if encabezado is None:
            encabezado = f"{MARCA} {VERSION_BITACORA}\ncripta_id=c\nversion_cripta=a\nversion_catalogo=b\nsemilla=1\n---\n"
        with open(self.ruta, "w", encoding="utf-8") as archivo:
            archivo.write(encabezado + cuerpo)

    def test_fr030_comentar_escribe_numeral_y_texto(self):
        with self.crear() as bitacora:
            bitacora.registrar("mover", "E")
            bitacora.comentar("ir a 3")
            bitacora.registrar("mover", "O")
        self.assertEqual(self.lineas(), ["mover E", "# ir a 3", "mover O"])

    def test_fr030_leer_bitacora_omite_los_comentarios(self):
        with self.crear() as bitacora:
            bitacora.comentar("ir a 3")
            bitacora.registrar("mover", "O")
            bitacora.registrar("mover", "S")
        self.assertEqual(leer_bitacora(self.ruta)[1], [("mover", "O"), ("mover", "S")])

    def test_fr030_comentar_valida_como_las_demas_lineas(self):
        with self.crear() as bitacora:
            with self.assertRaises(ValueError):
                bitacora.comentar("ir a 3\nmover N")
            with self.assertRaises(ValueError):
                bitacora.comentar(3)
        self.assertEqual(self.lineas(), [])

    def test_fr030_cripta_log_1_se_rechaza(self):
        # Código de salida 2: main.py convierte VersionIncompatible en 2.
        self.escribir("mover E\n", ENCABEZADO_V1)
        with self.assertRaises(VersionIncompatible):
            leer_bitacora(self.ruta)

    def test_fr030_cripta_log_1_da_codigo_2_en_el_replay(self):
        # ejecutar_replay lee la bitácora antes de usar el gestor: el rechazo llega a main
        # como VersionIncompatible, que devuelve 2.
        from main import ejecutar_replay

        class GestorQueNoSeUsa:
            def __getattr__(self, nombre):
                raise AssertionError(f"el replay usó el gestor ({nombre}) antes de rechazar la bitácora")

        self.escribir("mover E\n", ENCABEZADO_V1)
        with self.assertRaises(VersionIncompatible):
            ejecutar_replay(self.ruta, GestorQueNoSeUsa())

    def test_fr017_marcar_carga_y_leer_devuelve_la_directiva_en_acciones(self):
        with self.crear() as bitacora:
            bitacora.registrar("mover", "E")
            bitacora.marcar_carga()
            bitacora.registrar("esperar")
        self.assertEqual(self.lineas(), ["mover E", "@cargar", "esperar"])
        self.assertEqual(leer_bitacora(self.ruta)[1], [("mover", "E"), ("@cargar", ""), ("esperar", "")])

    def test_fr030_directiva_desconocida_se_rechaza(self):
        for directiva in ("@guardar", "@cargar ahora", "@"):
            with self.subTest(directiva=directiva):
                self.escribir(f"mover E\n{directiva}\n")
                with self.assertRaises(VersionIncompatible):
                    leer_bitacora(self.ruta)

    def test_fr030_registrar_rechaza_nombres_que_empiezan_con_numeral_o_arroba(self):
        with self.crear() as bitacora:
            for nombre in ("#mover", "@cargar", "#", "@"):
                with self.subTest(nombre=nombre):
                    with self.assertRaises(ValueError):
                        bitacora.registrar(nombre)
        self.assertEqual(self.lineas(), [])


class MotorRecargado(MotorFalso):
    """Motor que devuelve `recargar`: anota sus acciones aparte del original."""


class PruebasReproductorConCarga(unittest.TestCase):
    """T086: `@cargar` en el replay (FR-017, PR-12)."""

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "partida.log")
        with BitacoraPartida(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345) as bitacora:
            bitacora.registrar("mover", "N")
            bitacora.marcar_carga()
            bitacora.registrar("esperar")

    def tearDown(self):
        self.carpeta.cleanup()

    def test_fr017_cargar_llama_a_recargar_y_sigue_con_el_motor_que_devuelve(self):
        llamadas = []

        def recargar(motor):
            llamadas.append(motor)
            return MotorRecargado(motor.cripta_id, motor.semilla)

        reproductor = Reproductor(MotorFalso, "a3f91c", "cat-2026-08-01", recargar=recargar)
        final = reproductor.reproducir(self.ruta)

        self.assertEqual(len(llamadas), 1)
        original = llamadas[0]
        self.assertEqual(original.acciones, [("mover", "N")])  # @cargar no llega al motor
        self.assertIsInstance(final, MotorRecargado)
        self.assertEqual(final.acciones, [("esperar", "")])

    def test_fr017_sin_recargar_y_con_cargar_da_error_y_no_se_ignora(self):
        creados = []

        def fabrica(cripta_id, semilla):
            motor = MotorFalso(cripta_id, semilla)
            creados.append(motor)
            return motor

        reproductor = Reproductor(fabrica, "a3f91c", "cat-2026-08-01")
        with self.assertRaisesRegex(ValueError, "@cargar"):
            reproductor.reproducir(self.ruta)
        self.assertEqual(creados[0].acciones, [("mover", "N")])  # no siguió con «esperar»

    def test_fr017_sin_cargar_recargar_no_se_llama(self):
        with BitacoraPartida(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345) as bitacora:
            bitacora.registrar("mover", "N")

        def recargar(motor):
            raise AssertionError("no debía llamarse")

        motor = Reproductor(MotorFalso, "a3f91c", "cat-2026-08-01", recargar=recargar).reproducir(self.ruta)
        self.assertEqual(motor.acciones, [("mover", "N")])


class ObservadorFalso:
    """Anota cada aviso del Reproductor con el motor que recibe, en el orden en que llegan."""

    def __init__(self):
        self.llamadas = []

    def al_crear_motor(self, motor):
        self.llamadas.append(("al_crear_motor", motor))

    def despues_de_accion(self, motor, nombre, argumento):
        self.llamadas.append(("despues_de_accion", motor, nombre, argumento))

    def despues_de_carga(self, motor):
        self.llamadas.append(("despues_de_carga", motor))

    def eventos(self):
        return [llamada[0] for llamada in self.llamadas]


class MotorQueRechazaLaSegunda(MotorFalso):
    def ejecutar_accion(self, nombre, argumento):
        self.acciones.append((nombre, argumento))
        return len(self.acciones) < 2


class PruebasObservadorDelReproductor(unittest.TestCase):
    """T123: observador del Reproductor y reproducir_acciones (P-D02 de la spec 004, FR-017, PR-12;
    contracts/formato-bitacora.md, «Observador y reproducción en memoria»)."""

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "partida.log")
        self.creados = []
        self.recargados = []

    def tearDown(self):
        self.carpeta.cleanup()

    def escribir(self, lineas, version_catalogo="cat-2026-08-01"):
        # lineas: ("accion", argumento) o "@cargar"
        with BitacoraPartida(self.ruta, "cripta-01", "a3f91c", version_catalogo, 12345) as bitacora:
            for linea in lineas:
                if linea == "@cargar":
                    bitacora.marcar_carga()
                else:
                    bitacora.registrar(*linea)

    def fabrica(self, clase=MotorFalso):
        def crear(cripta_id, semilla):
            motor = clase(cripta_id, semilla)
            self.creados.append(motor)
            return motor
        return crear

    def recargar(self, motor):
        nuevo = MotorRecargado(motor.cripta_id, motor.semilla)
        self.recargados.append(nuevo)
        return nuevo

    def reproductor(self, observador, clase=MotorFalso, recargar="por_defecto", version_catalogo="cat-2026-08-01"):
        if recargar == "por_defecto":
            recargar = self.recargar
        try:
            return Reproductor(self.fabrica(clase), "a3f91c", version_catalogo, recargar=recargar,
                               observador=observador)
        except TypeError as error:
            self.fail(f"Reproductor no acepta observador=: {error}")

    def assertTieneReproducirAcciones(self):
        self.assertTrue(hasattr(Reproductor, "reproducir_acciones"), "falta Reproductor.reproducir_acciones")

    def test_pr12_sin_cargar_avisa_crear_y_cada_accion_en_orden(self):
        self.escribir([("mover", "N"), ("recoger", "llave"), ("retroceder", "")])
        observador = ObservadorFalso()
        final = self.reproductor(observador).reproducir(self.ruta)

        motor = self.creados[0]
        self.assertIs(final, motor)
        self.assertEqual(observador.llamadas, [
            ("al_crear_motor", motor),
            ("despues_de_accion", motor, "mover", "N"),
            ("despues_de_accion", motor, "recoger", "llave"),
            ("despues_de_accion", motor, "retroceder", ""),
        ])

    def test_pr12_con_cargar_avisa_la_carga_con_el_motor_nuevo(self):
        self.escribir([("mover", "N"), "@cargar", ("esperar", ""), "@cargar", ("mover", "S")])
        observador = ObservadorFalso()
        final = self.reproductor(observador).reproducir(self.ruta)

        original = self.creados[0]
        primero, segundo = self.recargados
        self.assertIs(final, segundo)
        self.assertEqual(observador.llamadas, [
            ("al_crear_motor", original),
            ("despues_de_accion", original, "mover", "N"),
            ("despues_de_carga", primero),
            ("despues_de_accion", primero, "esperar", ""),
            ("despues_de_carga", segundo),
            ("despues_de_accion", segundo, "mover", "S"),
        ])

    def test_pr12_accion_rechazada_da_el_error_de_hoy_y_no_se_avisa(self):
        self.escribir([("mover", "N"), ("mover", "E"), ("esperar", "")])
        observador = ObservadorFalso()
        with self.assertRaisesRegex(ValueError, "motor rechazó la acción 'mover' con argumento 'E'"):
            self.reproductor(observador, clase=MotorQueRechazaLaSegunda).reproducir(self.ruta)
        self.assertEqual(observador.eventos(), ["al_crear_motor", "despues_de_accion"])
        self.assertEqual(observador.llamadas[1][2:], ("mover", "N"))

    def test_pr12_cargar_sin_recargar_da_error_sin_avisar_la_carga(self):
        self.escribir([("mover", "N"), "@cargar", ("esperar", "")])
        observador = ObservadorFalso()
        with self.assertRaisesRegex(ValueError, "@cargar"):
            self.reproductor(observador, recargar=None).reproducir(self.ruta)
        self.assertEqual(observador.eventos(), ["al_crear_motor", "despues_de_accion"])

    def test_pr12_recargar_que_devuelve_none_da_error_sin_avisar_la_carga(self):
        self.escribir([("mover", "N"), "@cargar", ("esperar", "")])
        observador = ObservadorFalso()
        with self.assertRaisesRegex(ValueError, "no devolvió un motor"):
            self.reproductor(observador, recargar=lambda motor: None).reproducir(self.ruta)
        self.assertEqual(observador.eventos(), ["al_crear_motor", "despues_de_accion"])

    def test_pr12_version_incompatible_no_crea_motor_ni_avisa(self):
        self.escribir([("mover", "N")], version_catalogo="cat-otra")
        observador = ObservadorFalso()
        with self.assertRaises(VersionIncompatible):
            self.reproductor(observador).reproducir(self.ruta)
        self.assertEqual(self.creados, [])
        self.assertEqual(observador.llamadas, [])

    def test_pr12_motor_de_otra_cripta_no_se_avisa(self):
        self.escribir([("mover", "N")])
        observador = ObservadorFalso()

        class MotorDeOtraCripta(MotorFalso):
            def __init__(self, cripta_id, semilla):
                super().__init__("otra-cripta", semilla)

        with self.assertRaises(VersionIncompatible):
            self.reproductor(observador, clase=MotorDeOtraCripta).reproducir(self.ruta)
        self.assertEqual(observador.llamadas, [])

    def test_pr12_reproducir_acciones_en_memoria_igual_que_desde_el_archivo(self):
        self.assertTieneReproducirAcciones()
        self.escribir([("mover", "N"), "@cargar", ("esperar", "")])
        encabezado, acciones = leer_bitacora(self.ruta)

        desde_archivo, en_memoria = ObservadorFalso(), ObservadorFalso()
        final_archivo = self.reproductor(desde_archivo).reproducir(self.ruta)
        final_memoria = self.reproductor(en_memoria).reproducir_acciones(encabezado, list(acciones))

        self.assertEqual(type(final_memoria), type(final_archivo))
        self.assertEqual(final_memoria.acciones, final_archivo.acciones)
        self.assertEqual(self.creados[1].acciones, self.creados[0].acciones)
        quitar_motor = lambda llamadas: [(ll[0],) + ll[2:] for ll in llamadas]
        self.assertEqual(quitar_motor(en_memoria.llamadas), quitar_motor(desde_archivo.llamadas))

    def test_pr12_reproducir_acciones_comprueba_las_versiones(self):
        self.assertTieneReproducirAcciones()
        self.escribir([("mover", "N")])
        encabezado, acciones = leer_bitacora(self.ruta)
        observador = ObservadorFalso()
        with self.assertRaises(VersionIncompatible):
            self.reproductor(observador, version_catalogo="cat-otra").reproducir_acciones(encabezado, acciones)
        self.assertEqual(self.creados, [])
        self.assertEqual(observador.llamadas, [])

    def test_pr12_reproducir_solo_lee_y_llama_a_reproducir_acciones(self):
        self.assertTieneReproducirAcciones()
        from unittest import mock
        self.escribir([("mover", "N")])
        reproductor = self.reproductor(None)
        with mock.patch.object(reproductor, "reproducir_acciones", return_value="motor") as llamada:
            self.assertEqual(reproductor.reproducir(self.ruta), "motor")
        llamada.assert_called_once()
        (encabezado, acciones), _ = llamada.call_args
        esperado_encabezado, esperado_acciones = leer_bitacora(self.ruta)
        self.assertEqual(encabezado.cripta_id, esperado_encabezado.cripta_id)
        self.assertEqual(list(acciones), list(esperado_acciones))
        self.assertEqual(self.creados, [])  # el bucle está solo en reproducir_acciones

    def test_pr12_sin_observador_igual_que_hoy(self):
        self.assertTieneReproducirAcciones()
        self.escribir([("mover", "N"), "@cargar", ("esperar", "")])
        encabezado, acciones = leer_bitacora(self.ruta)
        con_none = self.reproductor(None).reproducir(self.ruta)
        sin_parametro = Reproductor(self.fabrica(), "a3f91c", "cat-2026-08-01", recargar=self.recargar)
        en_memoria = sin_parametro.reproducir_acciones(encabezado, acciones)
        self.assertEqual(con_none.acciones, [("esperar", "")])
        self.assertEqual(en_memoria.acciones, con_none.acciones)
        self.assertEqual(self.creados[0].acciones, [("mover", "N")])


if __name__ == "__main__":
    unittest.main()