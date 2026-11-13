# Pruebas de la opción --verificar de main.py (spec 002, T017). Contrato: specs/002-resolubilidad/contracts/
# cli-verificacion.md. Sin red: paquetes offline de tests/generador_criptas.py. Cada prueba cita su FR.

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

import main
from API.Fuentes import FuenteDatosOffline
from Vista.VistaConsola import VistaConsola
from tests.generador_criptas import (INVENTARIO_MAX, JUGADOR, PRESUPUESTO, VERSION, CriptaSintetica,
                                     escribir_paquete, generar_cripta)

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


# --- T028: bloque «No resoluble» completo y sus variantes (US2) -------------------------------------------------

def abierta(destino):
    return {"sala": destino, "cerrada": False, "costo": 1}


def cerrada(destino, llave=None):
    datos = {"sala": destino, "cerrada": True, "costo": 1}
    if llave is not None:
        datos["llave"] = llave
    return datos


def escribir_a_mano(carpeta, id_cripta, total_salas, salidas, llaves_json, sala_salida, llave_salida):
    """Paquete offline de una cripta armada a mano: salas 1..total_salas con las `salidas` dadas por sala.

    `llaves_json` puede tener ubicaciones en salas que no existen: `escribir_paquete` solo recibe las que sí, y luego
    se reescribe `llaves.json` con todas.
    """
    salas_json = [{"id": i, "nombre": f"Sala {i}", "salidas": salidas.get(i, {})} for i in range(1, total_salas + 1)]
    detalles = {"id": id_cripta, "version": VERSION, "salas_total": total_salas, "sala_inicial": 1,
                "sala_salida": sala_salida, "llave_salida": llave_salida, "presupuesto_solicitudes": PRESUPUESTO,
                "inventario_max": INVENTARIO_MAX, "jugador": dict(JUGADOR)}
    existentes = [u for u in llaves_json if 1 <= u["sala"] <= total_salas]
    nombres = []
    for u in llaves_json:
        if u["id"] not in nombres:
            nombres.append(u["id"])
    escribir_paquete(carpeta, CriptaSintetica(id_cripta, 0, detalles, salas_json, existentes, nombres, [], 0))
    with open(os.path.join(carpeta, "criptas", id_cripta, "llaves.json"), "w", encoding="utf-8") as archivo:
        json.dump({"llaves": llaves_json}, archivo)


# Ciclo por cadena (k1 <-> k2), frontera con y sin llave, llave de enemigo y llave sin ubicación: el ejemplo de
# cli-verificacion.md. Región {1..6}; k2 en 7 (tras 3 -E-> 7 con k1) y en 15 (la suelta e-40, tras 14 -> 15 con k1);
# k1 en 8 (tras 7 -> 8 con k2); llave_salida_x sin ubicación; la puerta de salida sale de 11, fuera de la región.
SALIDAS_CRIPTA_X = {
    1: {"E": abierta(2)},
    2: {"E": abierta(3)},
    3: {"S": abierta(4), "E": cerrada(7, "llave_k1")},
    4: {"E": abierta(5)},
    5: {"E": abierta(6), "N": cerrada(9)},
    7: {"E": cerrada(8, "llave_k2")},
    11: {"S": cerrada(12, "llave_salida_x")},
    14: {"S": cerrada(15, "llave_k1")},
}
LLAVES_CRIPTA_X = [{"id": "llave_k1", "sala": 8}, {"id": "llave_k2", "sala": 15, "enemigo": "e-40"},
                   {"id": "llave_k2", "sala": 7}]

ESPERADO_NO_RESOLUBLE = (
    "La cripta cripta-x no es resoluble.\n"
    "Llaves no obtenibles:\n"
    "  - llave_k1\n"
    "  - llave_k2\n"
    "  - llave_salida_x\n"
    "Frontera bloqueada:\n"
    "  - sala 3 (E) -> sala 7: requiere llave_k1\n"
    "  - sala 5 (N) -> sala 9: sin llave\n"
    "Puerta hacia la sala de salida (sala 12, requiere llave_salida_x):\n"
    "  - sala 11 (S) -> sala 12: bloqueada\n"
    "Ubicación de las llaves:\n"
    "  - llave_k1: sala 8\n"
    "  - llave_k2: sala 7; sala 15 (la suelta e-40)\n"
    "  - llave_salida_x: ubicación desconocida\n"
    "Dependencias entre llaves:\n"
    "  - llave_k1 -> llave_k2\n"
    "  - llave_k2 -> llave_k1\n"
    "  - llave_salida_x: sin dependencia\n"
    "Ciclos de llaves:\n"
    "  - llave_k1 -> llave_k2 -> llave_k1\n"
)

FRONTERA_VACIA = "Frontera bloqueada: ninguna (no hay puertas cerradas que salgan de la región alcanzable).\n"


class PruebasReporteNoResolubleCli(unittest.TestCase):

    setUp = PruebasVerificacionCli.setUp
    tearDown = PruebasVerificacionCli.tearDown
    correr = PruebasVerificacionCli.correr

    def verificar_a_mano(self, id_cripta, total_salas, salidas, llaves_json, sala_salida, llave_salida):
        paquete = os.path.join(self.temporal.name, f"paquete_{id_cripta}")
        escribir_a_mano(paquete, id_cripta, total_salas, salidas, llaves_json, sala_salida, llave_salida)
        return self.correr(paquete, "--verificar", id_cripta)

    def test_fr008_fr009_fr010_fr011_fr014_sc009_bloque_no_resoluble_exacto(self):
        """El bloque completo del contrato, carácter por carácter. Con él se señala la puerta (sala 3, E), la llave que
        falta (llave_k1) y dónde está (sala 8) sin consultar los datos (SC-009)."""
        codigo, texto = self.verificar_a_mano("cripta-x", 15, SALIDAS_CRIPTA_X, LLAVES_CRIPTA_X, 12, "llave_salida_x")
        self.assertEqual(codigo, 0)
        self.assertEqual(texto, ESPERADO_NO_RESOLUBLE)

    def test_fr012_bloque_no_resoluble_igual_en_dos_ejecuciones(self):
        _, primera = self.verificar_a_mano("cripta-x", 15, SALIDAS_CRIPTA_X, LLAVES_CRIPTA_X, 12, "llave_salida_x")
        _, segunda = self.verificar_a_mano("cripta-x", 15, SALIDAS_CRIPTA_X, LLAVES_CRIPTA_X, 12, "llave_salida_x")
        self.assertEqual(primera, segunda)

    def test_fr009_frontera_vacia(self):
        codigo, texto = self.verificar_a_mano("v-vacia", 3, {3: {"E": cerrada(2, "ks")}},
                                              [{"id": "ks", "sala": 3}], 2, "ks")
        self.assertEqual(codigo, 0)
        self.assertEqual(texto, (
            "La cripta v-vacia no es resoluble.\n"
            "Llaves no obtenibles:\n"
            "  - ks\n"
            + FRONTERA_VACIA +
            "Puerta hacia la sala de salida (sala 2, requiere ks):\n"
            "  - sala 3 (E) -> sala 2: bloqueada\n"
            "Ubicación de las llaves:\n"
            "  - ks: sala 3\n"
            "Dependencias entre llaves:\n"
            "  - ks: sin dependencia\n"
            "Ciclos de llaves: ninguno.\n"
        ))

    def test_fr009_fr011_destino_inexistente_y_ciclo_directo(self):
        codigo, texto = self.verificar_a_mano("v-destino", 2, {1: {"E": cerrada(99, "ka"), "S": cerrada(2, "ks")}},
                                              [{"id": "ks", "sala": 2}], 2, "ks")
        self.assertEqual(codigo, 0)
        self.assertEqual(texto, (
            "La cripta v-destino no es resoluble.\n"
            "Llaves no obtenibles:\n"
            "  - ka\n"
            "  - ks\n"
            "Frontera bloqueada:\n"
            "  - sala 1 (S) -> sala 2: requiere ks\n"
            "  - sala 1 (E) -> sala 99 (no existe): requiere ka\n"
            "Puerta hacia la sala de salida (sala 2, requiere ks):\n"
            "  - sala 1 (S) -> sala 2: bloqueada\n"
            "Ubicación de las llaves:\n"
            "  - ka: ubicación desconocida\n"
            "  - ks: sala 2\n"
            "Dependencias entre llaves:\n"
            "  - ka: sin dependencia\n"
            "  - ks -> ks\n"
            "Ciclos de llaves:\n"
            "  - ks -> ks (ciclo directo)\n"
        ))

    def test_fr009_fr010_sin_puerta_de_salida_y_ubicacion_en_sala_inexistente(self):
        llaves_json = [{"id": "ks", "sala": 99}, {"id": "ks", "sala": 98, "enemigo": "e-1"}]
        codigo, texto = self.verificar_a_mano("v-sin-puerta", 2, {1: {"E": abierta(2)}}, llaves_json, 2, "ks")
        self.assertEqual(codigo, 0)
        self.assertEqual(texto, (
            "La cripta v-sin-puerta no es resoluble.\n"
            "Llaves no obtenibles:\n"
            "  - ks\n"
            + FRONTERA_VACIA +
            "Puerta hacia la sala de salida: no existe ninguna salida hacia la sala 2 que requiera ks.\n"
            "Ubicación de las llaves:\n"
            "  - ks: sala 98 (no existe) (la suelta e-1); sala 99 (no existe)\n"
            "Dependencias entre llaves:\n"
            "  - ks: sin dependencia\n"
            "Ciclos de llaves: ninguno.\n"
        ))

    def test_fr008_fr010_fr011_secciones_vacias(self):
        """US1.6 con llave_salida obtenible: no hay llaves no obtenibles; cada sección vacía lo dice en una línea."""
        codigo, texto = self.verificar_a_mano("v-nada", 2, {1: {"E": abierta(2)}}, [{"id": "ks", "sala": 1}], 2, "ks")
        self.assertEqual(codigo, 0)
        self.assertEqual(texto, (
            "La cripta v-nada no es resoluble.\n"
            "Llaves no obtenibles: ninguna.\n"
            + FRONTERA_VACIA +
            "Puerta hacia la sala de salida: no existe ninguna salida hacia la sala 2 que requiera ks.\n"
            "Ubicación de las llaves: ninguna.\n"
            "Dependencias entre llaves: ninguna.\n"
            "Ciclos de llaves: ninguno.\n"
        ))


# --- T034: verificación obligatoria al iniciar una partida nueva (US3) ------------------------------------------

MENSAJE_RECHAZO = ("! Error: La cripta sint-nr no es resoluble. "
                   "Usa --forzar para jugarla de todos modos.\n")


class FuenteOfflineContada(main.FuenteDatosOffline):
    """Fuente offline que anota cada ruta pedida, para contar solicitudes repetidas (FR-026)."""
    rutas = []

    def _obtener(self, ruta, params=None):
        FuenteOfflineContada.rutas.append(ruta)
        return super()._obtener(ruta, params)


class PruebasPartidaNuevaCli(unittest.TestCase):

    setUp = PruebasVerificacionCli.setUp
    tearDown = PruebasVerificacionCli.tearDown
    foto_de_trabajo = PruebasVerificacionCli.foto_de_trabajo

    def correr(self, paquete, entradas, *argumentos):
        """Corre main.main() con una vista cuya entrada devuelve `entradas` en orden y luego fin de entrada."""
        pendientes = list(entradas)

        def entrada(_mensaje):
            if not pendientes:
                raise EOFError
            return pendientes.pop(0)

        argv = ["main.py", "--offline", paquete, "--datos-locales", self.datos,
                "--bitacora", os.path.join(self.trabajo, "partida.log"),
                "--puntajes", os.path.join(self.trabajo, "puntajes.txt"), *argumentos]
        salida = io.StringIO()
        with mock.patch.object(main, "VistaConsola", lambda: VistaConsola(entrada=entrada)), \
                mock.patch.object(main, "configurar_logging", lambda *a, **k: None), \
                mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(salida):
            codigo = main.main()
        return codigo, salida.getvalue()

    def reporte_de(self, paquete, cripta):
        # el reporte que acompaña al rechazo es el mismo bloque que da --verificar
        datos = os.path.join(self.temporal.name, "datos_reporte")
        _, texto = PruebasVerificacionCli.correr(self, paquete, "--verificar", cripta, "--datos-locales", datos)
        return texto

    def test_fr020_sc006_cripta_no_resoluble_rechaza_con_reporte_y_codigo_1(self):
        reporte = self.reporte_de(self.paquete_nr, CRIPTA_NO_RESOLUBLE)
        antes = self.foto_de_trabajo()
        codigo, texto = self.correr(self.paquete_nr, ["salir"], "--cripta", CRIPTA_NO_RESOLUBLE)
        self.assertEqual(codigo, 1)
        self.assertEqual(texto, MENSAJE_RECHAZO + reporte)
        # sin bitácora ni cambios en la tabla de puntajes (SC-006)
        self.assertEqual(self.foto_de_trabajo(), antes)

    def test_fr019_cripta_resoluble_muestra_el_orden_y_la_partida_inicia(self):
        codigo, texto = self.correr(self.paquete_res, ["salir"], "--cripta", CRIPTA_RESOLUBLE, "--semilla", "7")
        self.assertEqual(codigo, 0)
        self.assertTrue(texto.startswith(ESPERADO_RESOLUBLE), texto)
        self.assertIn(f"Partida nueva en {CRIPTA_RESOLUBLE} (semilla 7)\n", texto)
        self.assertLess(texto.index(ESPERADO_RESOLUBLE), texto.index("Partida nueva en"))
        self.assertIn("=== CRIPTA ===", texto)
        self.assertNotIn("! Error", texto)

    def test_fr018_lista_interactiva_con_no_resoluble_igual_que_cripta(self):
        reporte = self.reporte_de(self.paquete_nr, CRIPTA_NO_RESOLUBLE)
        antes = self.foto_de_trabajo()
        codigo, texto = self.correr(self.paquete_nr, [CRIPTA_NO_RESOLUBLE, "salir"])
        self.assertEqual(codigo, 1)
        self.assertTrue(texto.endswith(MENSAJE_RECHAZO + reporte), texto)
        self.assertEqual(self.foto_de_trabajo(), antes)

    def test_fr026_verificar_y_jugar_no_repite_solicitudes(self):
        FuenteOfflineContada.rutas = []
        with mock.patch.object(main, "FuenteDatosOffline", FuenteOfflineContada):
            codigo, _ = self.correr(self.paquete_res, ["salir"], "--cripta", CRIPTA_RESOLUBLE, "--semilla", "7")
        self.assertEqual(codigo, 0)
        rutas = FuenteOfflineContada.rutas
        base = f"/criptas/{CRIPTA_RESOLUBLE}"
        # la verificación tuvo que pedir las llaves: si no, la prueba no comprobaría nada
        self.assertIn(base + "/llaves", rutas)
        for ruta in (base, base + "/version", base + "/salas", base + "/llaves"):
            with self.subTest(ruta=ruta):
                self.assertEqual(rutas.count(ruta), 1, rutas)


# --- T035: la verificación no cambia la partida (SC-007, FR-023) ------------------------------------------------

SEMILLA_SC007 = 7
# acciones fijas sobre sint-res (sala 1 -E-> 2 -E-> 3 -E-> 4 -S-> 7, donde está llave_01); las rechazadas no van
# a la bitácora en ninguno de los dos caminos
ACCIONES_SC007 = ("e", "e", "esperar", "e", "s", "recoger llave_01", "mapa", "n", "o", "e", "s", "esperar")


def _como_datos(valor):
    # vuelve comparables los DTO sin __eq__ (MapaConocido, SalaConocida, ...)
    if isinstance(valor, (list, tuple)):
        return [_como_datos(v) for v in valor]
    if isinstance(valor, dict):
        return {k: _como_datos(v) for k, v in valor.items()}
    if hasattr(valor, "__dict__"):
        return {k: _como_datos(v) for k, v in vars(valor).items()}
    return valor


class VistaEspia(VistaConsola):
    """Vista muda que anota cuántas veces se mostró una verificación."""

    def __init__(self):
        super().__init__(entrada=lambda _m: "salir", salida=lambda *_a, **_k: None)
        self.verificaciones = 0

    def mostrar_verificacion(self, resultado):
        self.verificaciones += 1


class PruebasVerificacionNoCambiaPartida(unittest.TestCase):

    def setUp(self):
        from Gestor.GestorDatos import GestorDatos
        self.temporal = tempfile.TemporaryDirectory()
        base = self.temporal.name
        self.paquete = os.path.join(base, "paquete")
        escribir_paquete(self.paquete, generar_cripta(11, 20, 3, id_cripta=CRIPTA_RESOLUBLE))

        def gestor(nombre):
            return GestorDatos(main.FuenteDatosOffline(self.paquete), ruta_base=os.path.join(base, nombre))

        self.crear_gestor = gestor

    def tearDown(self):
        self.temporal.cleanup()

    def _partida_con_verificacion(self):
        from Controlador.ControladorPartida import ControladorPartida
        vista = VistaEspia()
        ruta = os.path.join(self.temporal.name, "con.log")
        controlador = ControladorPartida(self.crear_gestor("datos_con"), vista, ruta)
        controlador.nueva_partida(CRIPTA_RESOLUBLE, SEMILLA_SC007)
        return controlador, vista, ruta

    def _partida_sin_verificacion(self):
        # mismo arranque que nueva_partida, pero llamando directamente a preparar_partida
        from Bitacora.BitacoraPartida import BitacoraPartida
        from Controlador.ControladorPartida import ControladorPartida
        from Gestor.PreparadorPartida import preparar_partida
        gestor = self.crear_gestor("datos_sin")
        ruta = os.path.join(self.temporal.name, "sin.log")
        controlador = ControladorPartida(gestor, VistaEspia(), ruta)
        controlador.motor = preparar_partida(CRIPTA_RESOLUBLE, SEMILLA_SC007, gestor)
        controlador.bitacora = BitacoraPartida(ruta, CRIPTA_RESOLUBLE, gestor.version_cripta(CRIPTA_RESOLUBLE),
                                               gestor.version_catalogo(), SEMILLA_SC007)
        return controlador, ruta

    @staticmethod
    def _jugar_y_leer(controlador, ruta):
        for linea in ACCIONES_SC007:
            controlador.ejecutar(linea)
        motor = controlador.motor
        estado = {
            "reloj": motor.reloj,
            "sala": motor.jugador.sala.id,
            "vida": motor.jugador.vida,
            "resumen": motor.resumen_puntaje(),
            "azar": motor.azar.getstate(),
            "mapa": _como_datos(motor.mapa_conocido()),
        }
        controlador._cerrar()
        with open(ruta, encoding="utf-8") as archivo:
            return archivo.read(), estado

    def test_sc007_fr023_la_verificacion_se_ejecuta_al_iniciar(self):
        # sin esto, las comparaciones de abajo pasarían sin verificar nada
        controlador, vista, _ = self._partida_con_verificacion()
        controlador._cerrar()
        self.assertEqual(vista.verificaciones, 1)

    def test_sc007_fr023_misma_bitacora_y_mismo_estado_final(self):
        con, vista, ruta_con = self._partida_con_verificacion()
        self.assertEqual(vista.verificaciones, 1)
        sin, ruta_sin = self._partida_sin_verificacion()
        bitacora_con, estado_con = self._jugar_y_leer(con, ruta_con)
        bitacora_sin, estado_sin = self._jugar_y_leer(sin, ruta_sin)
        self.assertGreaterEqual(len(bitacora_sin.splitlines()), 6 + 4, bitacora_sin)  # encabezado + acciones
        self.assertEqual(bitacora_con, bitacora_sin)
        self.assertEqual(estado_con, estado_sin)

    def test_sc007_fr023_azar_y_conocimiento_iguales_al_iniciar(self):
        con, vista, _ = self._partida_con_verificacion()
        sin, _ = self._partida_sin_verificacion()
        self.assertEqual(vista.verificaciones, 1)
        self.assertEqual(con.motor.azar.getstate(), sin.motor.azar.getstate())
        self.assertEqual(_como_datos(con.motor.mapa_conocido()), _como_datos(sin.motor.mapa_conocido()))
        con._cerrar()
        sin._cerrar()

    def test_sc007_fr023_verificar_no_toca_el_azar_global(self):
        import random
        from Gestor.PreparadorPartida import verificar_cripta
        antes = random.getstate()
        verificar_cripta(CRIPTA_RESOLUBLE, self.crear_gestor("datos_global"))
        self.assertEqual(random.getstate(), antes)

    def test_sc007_fr023_la_verificacion_no_aparece_en_la_bitacora(self):
        con, vista, ruta = self._partida_con_verificacion()
        self.assertEqual(vista.verificaciones, 1)
        texto, _ = self._jugar_y_leer(con, ruta)
        for palabra in ("resoluble", "verific", "oleada", "llaves:"):
            with self.subTest(palabra=palabra):
                self.assertNotIn(palabra, texto.lower())


if __name__ == "__main__":
    unittest.main()
