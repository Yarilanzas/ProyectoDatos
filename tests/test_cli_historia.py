# Opciones `--hasta` y `--checkpoint-cada` de main.py (spec 004, T059, T060 y T095; FR-011, FR-013, FR-018, FR-024, FR-028, FR-031;
# contracts/comandos-historia.md: «Validación», «Combinaciones con la prioridad de la capacidad 002» y «Códigos de salida»).
# Corre `main.main()` con argv falso y sin red (paquete offline temporal). Los errores de uso salen con código 1 y **antes** de
# abrir la fuente de datos, crear el gestor o leer cualquier archivo; la tabla de prioridad no cambia.

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
from Controlador.ConsultaHistoria import ConsultaHistoria
from Modelo.LineaTiempo import K_POR_OMISION
from Vista.VistaConsola import VistaConsola
from tests.utiles_linea import SesionLinea, escribir_bitacora, partida_linea
from tests.utiles_niebla import CRIPTA_NIEBLA


class VistaQueFalla:
    """Reemplaza a `VistaConsola`: si algún camino sin vista la crea, la prueba falla (Principio II)."""

    def __init__(self, *argumentos, **opciones):
        raise AssertionError("se instanció la vista")


def sin_entrada(_mensaje):
    raise EOFError


class BaseCli(unittest.TestCase):

    def setUp(self):
        self.partida = partida_linea()
        self.addCleanup(self.partida.cerrar)
        for comando in ("esperar", "mover E", "esperar", "mover O"):
            self.partida.controlador.ejecutar(comando)
        self.partida.controlador.bitacora.cerrar()
        self.bitacora = self.partida.ruta_bitacora
        self.puntajes = os.path.join(self.partida.carpeta.name, "puntajes.txt")

    def argv(self, *argumentos, fuente=True):
        base = ["main.py"]
        if fuente:
            base += ["--offline", self.partida.paquete, "--datos-locales", self.partida.ruta_datos]
        return base + ["--puntajes", self.puntajes, *argumentos]

    def correr(self, *argumentos, vista=None, parches=(), fuente=True):
        """Corre main con `argumentos`. `vista` es lo que reemplaza a `VistaConsola` (por omisión, una con entrada vacía).
        Devuelve (código, salida)."""
        salida = io.StringIO()
        with contextlib.ExitStack() as pila:
            pila.enter_context(mock.patch.object(main, "VistaConsola",
                                                 vista if vista is not None else (lambda: VistaConsola(entrada=sin_entrada))))
            pila.enter_context(mock.patch.object(main, "configurar_logging", lambda *a, **k: None))
            pila.enter_context(mock.patch.object(sys, "argv", self.argv(*argumentos, fuente=fuente)))
            pila.enter_context(contextlib.redirect_stdout(salida))
            for parche in parches:
                pila.enter_context(parche)
            codigo = main.main()
        return codigo, salida.getvalue()

    def sin_abrir_nada(self):
        """Parches que hacen fallar a la prueba si main llega a crear el gestor o la fuente de datos."""
        return (mock.patch.object(main, "crear_gestor", side_effect=AssertionError("se creó el gestor")),
                mock.patch.object(main, "FuenteDatosOffline", side_effect=AssertionError("se abrió la fuente")),
                mock.patch.object(main, "FuenteDatosHTTP", side_effect=AssertionError("se abrió la fuente")),
                mock.patch.object(main, "ejecutar_replay", side_effect=AssertionError("se reprodujo")),
                mock.patch.object(main, "leer_bitacora", side_effect=AssertionError("se leyó la bitácora")))


class PruebasValidacionDeHasta(BaseCli):
    """T059: `--hasta` y sus combinaciones. Los casos de K de `--checkpoint-cada` son de T095."""

    def assertErrorDeUso(self, codigo, texto, esperado):
        self.assertEqual(codigo, 1, texto)
        self.assertEqual(texto, f"! Error: {esperado}\n")

    def test_fr013_hasta_no_entero_o_negativo_es_error_de_uso_con_codigo_1(self):
        for valor in ("abc", "-1", "-5", "1.5", "1e3", "", " ", "0x10", "+3", "٣"):
            with self.subTest(valor=valor):
                codigo, texto = self.correr("--replay", self.bitacora, "--hasta", valor, parches=self.sin_abrir_nada())
                self.assertErrorDeUso(codigo, texto,
                                      f"--hasta requiere un entero mayor o igual que 0 (recibido: {valor}).")

    def test_fr013_hasta_cero_y_enteros_validos_no_son_error(self):
        for valor in ("0", "5", "250", "007"):
            with self.subTest(valor=valor):
                codigo, texto = self.correr("--replay", self.bitacora, "--hasta", valor, vista=VistaQueFalla)
                self.assertEqual(codigo, 0, texto)

    def test_fr013_hasta_sin_replay_es_error_de_uso_con_codigo_1(self):
        for argumentos in (("--hasta", "5"), ("--cargar", "g.cripta", "--hasta", "5"),
                           ("--cripta", CRIPTA_NIEBLA, "--hasta", "5"), ("--hasta", "5", "--forzar")):
            with self.subTest(argumentos=argumentos):
                codigo, texto = self.correr(*argumentos, parches=self.sin_abrir_nada())
                self.assertErrorDeUso(codigo, texto, "--hasta solo se puede usar junto con --replay.")

    def test_fr013_el_error_sale_antes_de_abrir_la_fuente_incluso_sin_ella(self):
        codigo, texto = self.correr("--hasta", "xyz", fuente=False, parches=self.sin_abrir_nada())
        self.assertErrorDeUso(codigo, texto, "--hasta requiere un entero mayor o igual que 0 (recibido: xyz).")

    def test_fr013_la_validacion_no_lee_ni_crea_archivos(self):
        antes = os.listdir(self.partida.carpeta.name)
        inexistente = os.path.join(self.partida.carpeta.name, "no_existe.log")
        codigo, texto = self.correr("--replay", inexistente, "--hasta", "-3", parches=self.sin_abrir_nada())
        self.assertErrorDeUso(codigo, texto, "--hasta requiere un entero mayor o igual que 0 (recibido: -3).")
        self.assertEqual(os.listdir(self.partida.carpeta.name), antes)

    def test_fr013_bench_ignora_las_opciones_sin_validarlas(self):
        from tests import bench_cazador, bench_ciclo, bench_niebla, bench_personaD, bench_resolubilidad
        # se reemplazan TODAS las mediciones que main llama: una sin reemplazar correría de verdad y reescribiría su archivo
        with mock.patch.object(bench_personaD, "correr_bench") as uno, mock.patch.object(bench_ciclo, "correr_bench") as dos, \
                mock.patch.object(bench_resolubilidad, "correr_bench") as tres, \
                mock.patch.object(bench_niebla, "correr_bench") as cuatro, \
                mock.patch.object(bench_cazador, "correr_bench") as cinco:
            codigo, texto = self.correr("--bench", "--hasta", "abc", "--checkpoint-cada", "0", "--cargar", "x",
                                        "--replay", self.bitacora, vista=VistaQueFalla, parches=self.sin_abrir_nada())
        self.assertEqual(codigo, 0, texto)
        for medicion in (uno, dos, tres, cuatro, cinco):
            medicion.assert_called_once_with()

    # ───────────── la tabla de combinaciones, fila por fila ─────────────

    def test_fr013_mostrar_puntajes_con_replay_y_hasta_muestra_puntajes_e_ignora_el_resto(self):
        codigo, texto = self.correr("--mostrar-puntajes", "--replay", self.bitacora, "--hasta", "5",
                                    parches=(mock.patch.object(main, "ejecutar_replay",
                                                               side_effect=AssertionError("se reprodujo")),))
        self.assertEqual(codigo, 0, texto)
        self.assertNotIn("Historia", texto)

    def test_fr013_mostrar_puntajes_con_hasta_sin_replay_es_error_de_uso(self):
        codigo, texto = self.correr("--mostrar-puntajes", "--hasta", "5", parches=self.sin_abrir_nada())
        self.assertErrorDeUso(codigo, texto, "--hasta solo se puede usar junto con --replay.")

    def test_fr013_mostrar_puntajes_con_checkpoint_cada_lo_ignora(self):
        codigo, texto = self.correr("--mostrar-puntajes", "--checkpoint-cada", "10")
        self.assertEqual(codigo, 0, texto)

    def test_fr013_verificar_con_replay_y_hasta_verifica_e_ignora_el_resto(self):
        codigo, texto = self.correr("--verificar", CRIPTA_NIEBLA, "--replay", self.bitacora, "--hasta", "5",
                                    parches=(mock.patch.object(main, "ejecutar_replay",
                                                               side_effect=AssertionError("se reprodujo")),))
        self.assertEqual(codigo, 0, texto)
        self.assertNotIn("Historia", texto)
        solo, texto_solo = self.correr("--verificar", CRIPTA_NIEBLA)
        self.assertEqual(texto, texto_solo)

    def test_fr013_verificar_con_hasta_sin_replay_es_error_de_uso(self):
        codigo, texto = self.correr("--verificar", CRIPTA_NIEBLA, "--hasta", "5", parches=self.sin_abrir_nada())
        self.assertErrorDeUso(codigo, texto, "--hasta solo se puede usar junto con --replay.")

    def test_fr013_verificar_con_forzar_y_checkpoint_cada_verifica(self):
        codigo, texto = self.correr("--verificar", CRIPTA_NIEBLA, "--forzar", "--checkpoint-cada", "10")
        self.assertEqual(codigo, 0, texto)
        self.assertEqual(texto, self.correr("--verificar", CRIPTA_NIEBLA)[1])

    def test_fr011_replay_con_hasta_ignora_cargar_cripta_semilla_y_forzar(self):
        codigo, texto = self.correr("--replay", self.bitacora, "--hasta", "100", vista=VistaQueFalla)
        self.assertEqual(codigo, 0, texto)
        otro, texto_otro = self.correr("--replay", self.bitacora, "--hasta", "100", "--cargar", "no_existe.cripta",
                                       "--cripta", CRIPTA_NIEBLA, "--semilla", "99", "--forzar", vista=VistaQueFalla)
        self.assertEqual(otro, 0, texto_otro)
        self.assertEqual(texto_otro, texto)
        self.assertTrue(texto.startswith("Historia — instante 100\n"))

    def test_fr018_replay_con_cargar_y_checkpoint_cada_gana_replay_y_k_es_valido(self):
        codigo, texto = self.correr("--replay", self.bitacora, "--cargar", "no_existe.cripta", "--checkpoint-cada", "5",
                                    vista=VistaQueFalla)
        self.assertEqual(codigo, 0, texto)
        self.assertIn("Reproducción finalizada.", texto)

    def test_fr018_replay_con_checkpoint_cada_sin_hasta_es_un_replay_normal_sin_linea(self):
        with mock.patch.object(main, "ConsultaHistoria", side_effect=AssertionError("se construyó la línea")):
            codigo, texto = self.correr("--replay", self.bitacora, "--checkpoint-cada", "5", vista=VistaQueFalla)
        self.assertEqual(codigo, 0, texto)
        self.assertIn("Reproducción finalizada.", texto)
        self.assertNotIn("Historia", texto)
        self.assertEqual(texto, self.correr("--replay", self.bitacora, vista=VistaQueFalla)[1])

    def test_fr031_cargar_con_checkpoint_cada_es_error_de_uso_y_no_carga_nada(self):
        with mock.patch.object(main.ControladorPartida, "cargar", side_effect=AssertionError("se cargó")):
            codigo, texto = self.correr("--cargar", "g.cripta", "--checkpoint-cada", "10", parches=self.sin_abrir_nada())
        self.assertErrorDeUso(codigo, texto, "--checkpoint-cada no se puede usar al cargar una partida: rige el valor "
                                             "guardado en el archivo.")

    def test_fr031_cargar_con_hasta_sin_replay_es_error_de_uso(self):
        codigo, texto = self.correr("--cargar", "g.cripta", "--hasta", "5", parches=self.sin_abrir_nada())
        self.assertErrorDeUso(codigo, texto, "--hasta solo se puede usar junto con --replay.")

    def test_fr018_cripta_con_checkpoint_cada_arma_la_partida_con_ese_k(self):
        for argumentos in (("--cripta", CRIPTA_NIEBLA, "--checkpoint-cada", "7"),
                           ("--cripta", CRIPTA_NIEBLA, "--forzar", "--checkpoint-cada", "7")):
            with self.subTest(argumentos=argumentos):
                controladores = []
                original = main.ControladorPartida

                def espia(*a, **k):
                    controladores.append(original(*a, **k))
                    return controladores[-1]

                with mock.patch.object(main, "ControladorPartida", espia):
                    codigo, texto = self.correr(*argumentos, "--semilla", "3", "--bitacora",
                                                os.path.join(self.partida.carpeta.name, "nueva.log"))
                self.assertEqual(codigo, 0, texto)
                self.assertEqual(controladores[0].k_linea, 7)

    def test_fr018_sin_checkpoint_cada_rige_el_k_por_omision(self):
        controladores = []
        original = main.ControladorPartida

        def espia(*a, **k):
            controladores.append(original(*a, **k))
            return controladores[-1]

        with mock.patch.object(main, "ControladorPartida", espia):
            codigo, texto = self.correr("--cripta", CRIPTA_NIEBLA, "--semilla", "3", "--bitacora",
                                        os.path.join(self.partida.carpeta.name, "nueva.log"))
        self.assertEqual(codigo, 0, texto)
        self.assertEqual(controladores[0].k_linea, K_POR_OMISION)


class PruebasEdgesDeReplay(BaseCli):
    """T060."""

    def bitacora_con_carga(self):
        sesion = SesionLinea(k=3, semilla=4, huellas=False)
        self.addCleanup(sesion.cerrar)
        sesion.hacer([("esperar", ""), ("mover", "E")])
        sesion.guardar_y_cargar(entre=[("esperar", "")])
        sesion.hacer([("esperar", ""), ("mover", "O")])
        ruta = escribir_bitacora(sesion, os.path.join(sesion.partida.carpeta.name, "con_carga.log"))
        return sesion, ruta

    def corre_con(self, sesion, *argumentos):
        salida = io.StringIO()
        argv = ["main.py", "--offline", sesion.partida.paquete, "--datos-locales", sesion.partida.ruta_datos, *argumentos]
        with mock.patch.object(main, "VistaConsola", VistaQueFalla), \
                mock.patch.object(main, "configurar_logging", lambda *a, **k: None), \
                mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(salida):
            codigo = main.main()
        return codigo, salida.getvalue()

    def test_fr024_una_bitacora_de_version_incompatible_da_codigo_2_con_y_sin_hasta(self):
        ruta = os.path.join(self.partida.carpeta.name, "vieja.log")
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write(f"CRIPTA-LOG 1\ncripta_id={CRIPTA_NIEBLA}\nversion_cripta=v1\nversion_catalogo=cat-1\nsemilla=7\n---\n")
        sin = self.correr("--replay", ruta, vista=VistaQueFalla)
        con = self.correr("--replay", ruta, "--hasta", "50", vista=VistaQueFalla)
        self.assertEqual(sin[0], 2, sin[1])
        self.assertEqual(con, sin)
        self.assertTrue(con[1].startswith("! Error: Versión incompatible: "), con[1])

    def test_fr024_una_cripta_de_otra_version_da_codigo_2_con_hasta(self):
        ruta = os.path.join(self.partida.carpeta.name, "otra_version.log")
        with open(self.bitacora, encoding="utf-8") as origen:
            texto = origen.read().replace("version_cripta=", "version_cripta=x")
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write(texto)
        codigo, salida = self.correr("--replay", ruta, "--hasta", "50", vista=VistaQueFalla)
        self.assertEqual(codigo, 2, salida)
        self.assertTrue(salida.startswith("! Error: Versión incompatible: "), salida)

    def test_fr011_una_bitacora_que_no_existe_da_codigo_1_con_hasta(self):
        codigo, salida = self.correr("--replay", os.path.join(self.partida.carpeta.name, "nada.log"), "--hasta", "5",
                                     vista=VistaQueFalla)
        self.assertEqual(codigo, 1)
        self.assertTrue(salida.startswith("! Error: "), salida)

    def test_fr028_checkpoint_cada_con_replay_solo_cambia_el_costo(self):
        referencia = None
        for k in ("1", "2", "50", "500"):
            with self.subTest(k=k):
                codigo, texto = self.correr("--replay", self.bitacora, "--hasta", "150", "--checkpoint-cada", k,
                                            vista=VistaQueFalla)
                self.assertEqual(codigo, 0, texto)
                referencia = referencia or texto
                self.assertEqual(texto, referencia)

    def test_fr028_con_cargar_en_la_bitacora_rige_el_k_de_la_ejecucion_y_no_cambia_ningun_resumen(self):
        sesion, ruta = self.bitacora_con_carga()
        final = sesion.linea.reloj_actual
        for t in (0, 100, 150, 200, 250, final, final + 500):
            with self.subTest(t=t):
                resultados = [self.corre_con(sesion, "--replay", ruta, "--hasta", str(t), "--checkpoint-cada", k)
                              for k in ("1", "3", "500")]
                for codigo, texto in resultados:
                    self.assertEqual(codigo, 0, texto)
                self.assertEqual(resultados[0], resultados[1])
                self.assertEqual(resultados[1], resultados[2])

    def test_fr030_con_cargar_el_replay_con_hasta_da_lo_mismo_que_la_linea_viva(self):
        from Vista.TextoResumen import lineas_resumen
        sesion, ruta = self.bitacora_con_carga()
        for t in (0, 100, 150, 200, 250):
            with self.subTest(t=t):
                codigo, texto = self.corre_con(sesion, "--replay", ruta, "--hasta", str(t))
                self.assertEqual(codigo, 0, texto)
                esperado = lineas_resumen(sesion.linea.consultar_instante(t, sesion.motor))
                self.assertEqual(texto.splitlines(), esperado)


class EspiaDeConsulta(ConsultaHistoria):
    """Anota la línea que arma `--hasta` justo antes de consultarla (después se cierra y se borra)."""

    vistas = []

    def al_terminar(self, motor):
        EspiaDeConsulta.vistas.append((self.linea.k, self.linea.cantidad_puntos, self.linea.acciones))
        super().al_terminar(motor)


class PruebasValidacionDeCheckpointCada(BaseCli):
    """T095: los casos de K viven solo aquí."""

    def test_fr018_k_invalido_es_error_de_uso_con_codigo_1(self):
        for valor in ("0", "-5", "abc", "1.5", "", " 3", "1e1", "٣"):
            with self.subTest(valor=valor):
                codigo, texto = self.correr("--replay", self.bitacora, "--hasta", "5", "--checkpoint-cada", valor,
                                            parches=self.sin_abrir_nada())
                self.assertEqual(codigo, 1, texto)
                self.assertEqual(texto, "! Error: --checkpoint-cada requiere un entero mayor o igual que 1 "
                                        f"(recibido: {valor}).\n")

    def test_fr018_k_invalido_se_rechaza_con_cualquier_modo(self):
        for argumentos in (("--cripta", CRIPTA_NIEBLA), ("--cargar", "g.cripta"), ("--replay", self.bitacora)):
            with self.subTest(argumentos=argumentos):
                codigo, texto = self.correr(*argumentos, "--checkpoint-cada", "0", parches=self.sin_abrir_nada())
                self.assertEqual(codigo, 1, texto)
                self.assertIn("--checkpoint-cada requiere un entero mayor o igual que 1 (recibido: 0).", texto)

    def test_fr018_k_igual_a_1_es_valido_y_arma_una_linea_con_un_punto_por_accion(self):
        EspiaDeConsulta.vistas = []
        with mock.patch.object(main, "ConsultaHistoria", EspiaDeConsulta):
            codigo, texto = self.correr("--replay", self.bitacora, "--hasta", "100", "--checkpoint-cada", "1",
                                        vista=VistaQueFalla)
        self.assertEqual(codigo, 0, texto)
        k, puntos, acciones = EspiaDeConsulta.vistas[0]
        self.assertEqual(k, 1)
        self.assertEqual(puntos, acciones + 1)          # el punto inicial y uno por acción
        self.assertEqual(acciones, 4)

    def test_fr018_otros_valores_validos_llegan_a_la_linea(self):
        for valor, esperado in (("2", 2), ("50", 50), ("500", 500), ("0007", 7)):
            with self.subTest(valor=valor):
                EspiaDeConsulta.vistas = []
                with mock.patch.object(main, "ConsultaHistoria", EspiaDeConsulta):
                    codigo, texto = self.correr("--replay", self.bitacora, "--hasta", "100", "--checkpoint-cada", valor,
                                                vista=VistaQueFalla)
                self.assertEqual(codigo, 0, texto)
                self.assertEqual(EspiaDeConsulta.vistas[0][0], esperado)

    def test_fr018_sin_checkpoint_cada_rige_el_k_por_omision_en_el_replay(self):
        EspiaDeConsulta.vistas = []
        with mock.patch.object(main, "ConsultaHistoria", EspiaDeConsulta):
            codigo, texto = self.correr("--replay", self.bitacora, "--hasta", "100", vista=VistaQueFalla)
        self.assertEqual(codigo, 0, texto)
        self.assertEqual(EspiaDeConsulta.vistas[0][0], K_POR_OMISION)
        self.assertEqual(K_POR_OMISION, 50)


if __name__ == "__main__":
    unittest.main()
