# El comando `historia` y el enganche de la línea de tiempo en el controlador (spec 004; T023, T024, T035 y T036).
# Atiende: FR-003, FR-004, FR-005, FR-008, FR-009, FR-010, FR-025, PR-08. Sin red: cripta resoluble creada por
# ControladorPartida.nueva_partida con un paquete offline temporal (tests/utiles_linea.py).

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Bitacora.BitacoraPartida import leer_bitacora
from Gestor.GestorHistorico import GestorHistorico
from Modelo.LineaTiempo import TIPO_ACCION, TIPO_RETROCESO
from Vista.TextoResumen import lineas_resumen
from Vista.VistaConsola import AYUDA, VistaConsola
from tests.utiles_linea import dar_pergaminos, partida_linea
from tests.utiles_niebla import CRIPTA_NIEBLA

USO = "Use: historia <t> | historia #<k>"
ACCIONES = ["esperar", "s", "e", "esperar", "o", "n"]   # ciclo por las salas 1, 4 y 5 y de vuelta


def mensajes(vista, tipo):
    return [args[0] for nombre, args in vista.lineas if nombre == tipo]


def foto(partida):
    controlador = partida.controlador
    linea = controlador.linea
    controlador.bitacora._archivo.flush()
    with open(partida.ruta_bitacora, encoding="utf-8") as archivo:
        bitacora = archivo.read()
    return (controlador.motor.reloj, controlador.motor.acciones_jugador, bitacora, list(linea.guion_tipo),
            list(linea.guion_nombre), list(linea.guion_argumento), list(linea.vig_guion), linea.cantidad_puntos)


class BaseComando(unittest.TestCase):

    def setUp(self):
        self.partida = partida_linea(semilla=11)
        self.addCleanup(self.partida.cerrar)
        self.controlador = self.partida.controlador
        self.vista = self.partida.vista
        self.motor = self.controlador.motor

    def jugar(self, comandos=ACCIONES):
        for comando in comandos:
            self.controlador.ejecutar(comando)


class PruebasEnganche(BaseComando):
    """T035: nueva_partida crea la línea; `_accion` la avisa tras la bitácora y solo si el motor aceptó."""

    def test_fr025_nueva_partida_crea_la_linea_con_k_y_el_gestor_historico(self):
        linea = self.controlador.linea
        self.assertEqual(linea.k, 50)
        self.assertEqual((linea.acciones, linea.cantidad_puntos), (0, 1))
        self.assertIsInstance(linea.gestor_historico, GestorHistorico)
        self.controlador.k_linea = 7
        self.controlador.nueva_partida(CRIPTA_NIEBLA, 11)
        self.assertEqual(self.controlador.linea.k, 7)
        self.assertEqual(self.controlador.linea.acciones, 0)

    def test_fr008_una_accion_rechazada_no_registra_nada(self):
        self.jugar(["esperar", "s"])
        antes = foto(self.partida)
        self.controlador.ejecutar("mover X")
        self.controlador.ejecutar("atacar no-existe")
        self.controlador.ejecutar("abrir N")
        self.assertEqual(foto(self.partida), antes)
        self.assertEqual(mensajes(self.vista, "mostrar_aviso").count("No se pudo realizar esa acción"), 3)

    def test_fr025_la_bitacora_y_el_guion_llevan_los_mismos_comandos_en_el_mismo_orden(self):
        self.jugar(ACCIONES + ["mover X", "ir a 5", "esperar"])
        self.controlador.bitacora._archivo.flush()
        _encabezado, acciones = leer_bitacora(self.partida.ruta_bitacora)
        linea = self.controlador.linea
        guion = [(linea.guion_nombre[i], linea.guion_argumento[i]) for i in range(len(linea.guion_tipo))]
        self.assertEqual(guion, acciones)
        self.assertEqual(linea.guion_tipo, [TIPO_ACCION] * len(acciones))
        self.assertGreater(len(acciones), 7)   # incluye los pasos de «ir a»: cada uno es una acción

    def test_fr025_los_retrocesos_tambien_van_a_la_linea_y_a_la_bitacora(self):
        dar_pergaminos(self.motor, 1)
        self.jugar(["esperar", "s", "retroceder"])
        self.controlador.bitacora._archivo.flush()
        _encabezado, acciones = leer_bitacora(self.partida.ruta_bitacora)
        linea = self.controlador.linea
        self.assertEqual([nombre for nombre, _ in acciones], ["esperar", "mover", "retroceder"])
        self.assertEqual(linea.guion_tipo, [TIPO_ACCION, TIPO_ACCION, TIPO_RETROCESO])
        self.assertEqual(linea.acciones, 1)

    def test_fr025_sin_bitacora_la_linea_igual_registra(self):
        self.controlador.bitacora.cerrar()
        self.controlador.bitacora = None
        self.jugar(["esperar", "s", "e"])
        self.assertEqual(self.controlador.linea.acciones, 3)
        self.assertEqual(self.controlador.linea.guion_nombre, ["esperar", "mover", "mover"])

    def test_fr009_una_accion_que_lanza_runtime_error_con_el_motor_ya_avanzado_no_deja_la_linea_desfasada_en_silencio(self):
        """`ejecutar_accion` avanza el motor y luego lanza RuntimeError: `_accion` lo muestra y no anota nada; la línea
        detecta el desfase por el sello y se desactiva avisando, en vez de seguir registrando con un sello equivocado."""
        self.jugar(["esperar", "s"])
        bitacora_antes = foto(self.partida)[2]
        original = self.motor.ejecutar_accion

        def a_medias(nombre, argumento=""):
            original(nombre, argumento)           # el motor avanzó (reloj, secuencia y acciones)
            raise RuntimeError("falló a medias")

        self.motor.ejecutar_accion = a_medias
        self.controlador.ejecutar("esperar")
        del self.motor.ejecutar_accion
        self.assertIn("falló a medias", mensajes(self.vista, "mostrar_error"))
        self.assertTrue(any("desfasada" in aviso for aviso in mensajes(self.vista, "mostrar_aviso")))
        self.assertIsNone(self.controlador.linea, "la línea siguió registrando desfasada")
        self.assertIsNone(self.controlador.observador)
        self.controlador.bitacora._archivo.flush()
        with open(self.partida.ruta_bitacora, encoding="utf-8") as archivo:
            self.assertEqual(archivo.read(), bitacora_antes, "no se anota en la bitácora lo que falló")
        # y `historia` lo dice en vez de mentir
        self.controlador.ejecutar("historia 0")
        self.assertIn("La historia no está disponible en esta partida", mensajes(self.vista, "mostrar_aviso"))
        self.assertEqual(mensajes(self.vista, "mostrar_resumen_historico"), [])

    def test_fr009_un_runtime_error_sin_avanzar_el_motor_deja_la_linea_en_su_sitio(self):
        self.jugar(["esperar"])
        original = self.motor.ejecutar_accion

        def sin_avanzar(nombre, argumento=""):
            raise RuntimeError("falló antes de avanzar")

        self.motor.ejecutar_accion = sin_avanzar
        self.controlador.ejecutar("esperar")
        del self.motor.ejecutar_accion
        self.assertIn("falló antes de avanzar", mensajes(self.vista, "mostrar_error"))
        self.assertIsNotNone(self.controlador.linea)
        self.assertTrue(self.controlador.linea.sincronizada(self.motor))
        self.jugar(["esperar"])
        self.assertEqual(self.controlador.linea.acciones, 2)
        self.assertIs(self.motor.ejecutar_accion.__func__, type(self.motor).ejecutar_accion)
        self.assertEqual(original.__name__, "ejecutar_accion")

    def test_fr025_cerrar_cierra_la_linea_y_una_partida_cargada_no_tiene_historia_hasta_t085(self):
        self.jugar(["esperar", "s"])
        ruta = os.path.join(self.partida.carpeta.name, "guardada.cripta")
        self.assertTrue(self.controlador.guardar(ruta))
        self.controlador.cargar(ruta)
        self.assertIsNone(self.controlador.linea)
        self.controlador.ejecutar("historia 0")
        self.assertIn("La historia no está disponible en esta partida", mensajes(self.vista, "mostrar_aviso"))
        self.controlador._cerrar()
        self.assertIsNone(self.controlador.observador)


class PruebasComandoHistoria(BaseComando):
    """T036: el comando `historia` y su texto."""

    def test_fr003_historia_t_muestra_el_resumen_sin_cambiar_la_partida(self):
        self.jugar()
        antes = foto(self.partida)
        self.controlador.ejecutar("historia 250")
        resumenes = mensajes(self.vista, "mostrar_resumen_historico")
        self.assertEqual(len(resumenes), 1)
        self.assertEqual(resumenes[0].referencia, ("instante", 250))
        self.assertEqual(foto(self.partida), antes)

    def test_fr004_historia_numeral_k_muestra_el_estado_antes_de_esa_accion(self):
        self.jugar()
        self.controlador.ejecutar("historia #3")
        resumen = mensajes(self.vista, "mostrar_resumen_historico")[0]
        self.assertEqual(resumen.referencia, ("accion", 3))
        self.controlador.ejecutar(f"historia #{self.controlador.linea.acciones + 1}")
        self.assertEqual(mensajes(self.vista, "mostrar_resumen_historico")[1].referencia, ("actual", None))

    def test_fr006_la_vista_de_consola_imprime_las_lineas_del_resumen(self):
        salida = []
        self.controlador.vista = VistaConsola(salida=salida.append)
        self.jugar()
        salida.clear()
        self.controlador.ejecutar("historia 250")
        self.assertEqual(salida[0], "Historia — instante 250")
        self.assertIn("Mapa conocido:", salida)
        resumen = self.controlador.linea.consultar_instante(250, self.motor)
        self.assertEqual(salida, lineas_resumen(resumen))

    def test_fr005_un_error_de_reconstruccion_es_un_error_con_la_causa(self):
        self.jugar()
        self.controlador.linea.vig_sec[1] += 1   # el sello de la decisión 2 ya no coincide
        self.controlador.ejecutar("historia #4")
        errores = mensajes(self.vista, "mostrar_error")
        self.assertEqual(len(errores), 1)
        self.assertTrue(errores[0].startswith("No se pudo reconstruir ese momento: "), errores[0])


class PruebasRechazos(BaseComando):
    """T023: los rechazos de comandos-historia.md, sin consumir tiempo, sin contar como acción y sin anotarse."""

    def test_us1_6_historia_900_con_el_reloj_en_400_es_un_aviso(self):
        self.jugar(["esperar", "s", "e", "esperar"])
        self.assertEqual(self.motor.reloj, 400)
        antes = foto(self.partida)
        self.controlador.ejecutar("historia 900")
        self.assertEqual(mensajes(self.vista, "mostrar_aviso")[-1], "No hay historia más allá del reloj actual (400).")
        self.assertEqual(mensajes(self.vista, "mostrar_error"), [])
        self.assertEqual(foto(self.partida), antes)

    def test_us1_6_errores_de_uso_frente_a_avisos(self):
        self.jugar(["esperar", "s", "e", "esperar"])
        acciones = self.controlador.linea.acciones
        errores_de_uso = ["historia", "historia -3", "historia abc", "historia #", "historia #1.5", "historia 1.5",
                          "historia # 3", "historia ٣", "historia #-1", "historia 3 4"]
        for comando in errores_de_uso:
            with self.subTest(comando=comando):
                antes = foto(self.partida)
                errores = len(mensajes(self.vista, "mostrar_error"))
                avisos = len(mensajes(self.vista, "mostrar_aviso"))
                self.controlador.ejecutar(comando)
                self.assertEqual(mensajes(self.vista, "mostrar_error")[errores:], [USO])
                self.assertEqual(len(mensajes(self.vista, "mostrar_aviso")), avisos)
                self.assertEqual(foto(self.partida), antes)
        avisos_esperados = [("historia #0", "Las acciones se numeran desde 1."),
                            ("historia #99", f"La acción 99 no existe: la próxima acción es la {acciones + 1}.")]
        for comando, texto in avisos_esperados:
            with self.subTest(comando=comando):
                antes = foto(self.partida)
                errores = len(mensajes(self.vista, "mostrar_error"))
                self.controlador.ejecutar(comando)
                self.assertEqual(mensajes(self.vista, "mostrar_aviso")[-1], texto)
                self.assertEqual(len(mensajes(self.vista, "mostrar_error")), errores)
                self.assertEqual(foto(self.partida), antes)
        self.assertEqual(mensajes(self.vista, "mostrar_resumen_historico"), [])

    def test_us1_6_ningun_rechazo_consume_tiempo_ni_cuenta_como_accion(self):
        self.jugar(["esperar", "s"])
        reloj, acciones = self.motor.reloj, self.motor.acciones_jugador
        for comando in ("historia", "historia 99999", "historia #0", "historia #50", "historia x"):
            self.controlador.ejecutar(comando)
        self.assertEqual((self.motor.reloj, self.motor.acciones_jugador), (reloj, acciones))
        self.assertEqual(self.controlador.linea.acciones, 2)

    def test_fr009_con_la_partida_terminada_apunta_a_replay_hasta(self):
        self.jugar(["esperar"])
        self.motor.jugador.vivo = False
        self.controlador.ejecutar("historia 0")
        self.assertIn("La partida terminó: use --replay --hasta para consultar el pasado",
                      mensajes(self.vista, "mostrar_aviso"))


class PruebasAyuda(BaseComando):
    """T024: la ayuda lista `historia`, `--hasta` y `--checkpoint-cada` (FR-010)."""

    def test_us1_7_la_ayuda_lista_historia_hasta_y_checkpoint_cada(self):
        for texto in ("historia <t>", "historia #<k>", "--hasta", "--checkpoint-cada"):
            with self.subTest(texto=texto):
                self.assertIn(texto, AYUDA)

    def test_us1_7_el_comando_ayuda_muestra_esas_lineas(self):
        salida = []
        vista = VistaConsola(salida=salida.append)
        vista.mostrar_ayuda()
        texto = "\n".join(salida)
        for esperado in ("historia <t>", "historia #<k>", "--hasta T con --replay", "--checkpoint-cada K"):
            self.assertIn(esperado, texto)
        self.controlador.ejecutar("ayuda")
        self.assertIn(("mostrar_ayuda", ()), self.vista.lineas)


if __name__ == "__main__":
    unittest.main()
