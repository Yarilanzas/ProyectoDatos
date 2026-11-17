# `--replay --hasta T`: consulta del pasado sin interacción (spec 004, Historia 4; T055 a T058; FR-007, FR-011, FR-012, FR-015,
# FR-030; contracts/comandos-historia.md y formato-bitacora.md). Estas pruebas ejercitan `Controlador/ConsultaHistoria.py`, que es
# lo que `main.py` llamará con `--hasta` (T063a y T063b): reproduce la bitácora **completa** con el `Reproductor`, un
# `ObservadorLinea` y un gestor sin red, y da las líneas de texto que `main` imprimirá. Sin red, sin vista: todo el texto sale de
# `Vista/TextoResumen.py`. Cada escenario se prueba dos veces: contra `ConsultaHistoria` y por `main.py --replay --hasta` (las
# clases `...PorMain`, que repiten las mismas pruebas con `main` y comprueban código de salida 0, la vista que falla al crearse y
# que no hay «Reproducción finalizada.»). Las opciones inválidas y las combinaciones están en tests/test_cli_historia.py.

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
from Bitacora.BitacoraPartida import BitacoraPartida
from Controlador.ConsultaHistoria import ConsultaHistoria
from Controlador.ReconstructorLinea import acciones_del_guion
from Vista.TextoResumen import lineas_resumen
from tests.test_linea_independencia_k import jugar_con_el_controlador
from tests.utiles_linea import CONTENIDO_LINEA, SesionLinea, huella, partida_linea
from tests.utiles_niebla import CRIPTA_NIEBLA, PERGAMINO, contenido_sala

AVISO = "La partida termina antes del instante {t} (la bitácora acaba en el reloj {final}): se muestra el estado final."


def historia(partida, t):
    """Lo que el comando `historia t` muestra en la partida jugada (las líneas del resumen, con título)."""
    vista = partida.vista
    vista.lineas.clear()
    partida.controlador.ejecutar(f"historia {t}")
    nombre, argumentos = vista.lineas[-1]
    if nombre != "mostrar_resumen_historico":
        raise AssertionError(f"historia {t} mostró {nombre}: {argumentos}")
    return lineas_resumen(argumentos[0])


class VistaQueFalla:
    """Reemplaza a `VistaConsola`: `--replay --hasta` no debe instanciar la vista (Principio II)."""

    def __init__(self, *argumentos, **opciones):
        raise AssertionError("--replay --hasta instanció la vista")


VIA = ["consulta"]   # «consulta»: ConsultaHistoria directo; «main»: `main.py --replay --hasta` (lo cambian las clases PorMain)


def por_main(partida, t, k=50, bitacora=None):
    """Lo que imprime `main.py --replay <bitácora> --hasta t --checkpoint-cada k`, como lista de líneas; exige código 0 y
    que no se instancie la vista."""
    argv = ["main.py", "--offline", partida.paquete, "--datos-locales", partida.ruta_datos,
            "--replay", bitacora or partida.ruta_bitacora, "--hasta", str(t), "--checkpoint-cada", str(k)]
    salida = io.StringIO()
    with mock.patch.object(main, "VistaConsola", VistaQueFalla), \
            mock.patch.object(main, "configurar_logging", lambda *a, **k: None), \
            mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(salida):
        codigo = main.main()
    if codigo != 0:
        raise AssertionError(f"main --replay --hasta {t} terminó con código {codigo}: {salida.getvalue()}")
    if "Reproducción finalizada" in salida.getvalue():
        raise AssertionError("main --hasta imprimió «Reproducción finalizada.»")
    return salida.getvalue().splitlines()


def consultar(partida, t, k=50):
    """Lo que `--replay <bitácora> --hasta t` imprimiría, como lista de líneas."""
    partida.controlador.bitacora.cerrar()
    if VIA[0] == "main":
        return por_main(partida, t, k)
    gestor = partida.nuevo_gestor(iniciado=False)
    consulta = ConsultaHistoria(gestor, t, k)
    return consulta.reproducir(partida.ruta_bitacora)


def sin_inventario(lineas):
    return [linea for linea in lineas if not linea.startswith("Inventario")]


def jugar(partida, comandos):
    for comando in comandos:
        partida.controlador.ejecutar(comando)


class BasePartida(unittest.TestCase):

    def partida(self, **opciones):
        partida = partida_linea(**opciones)
        self.addCleanup(partida.cerrar)
        return partida


class PruebasIgualQueHistoria(BasePartida):
    """T055 (Escenario US4-1, Quickstart 8): el mismo texto que `historia` en la partida jugada, sin vista."""

    def jugada(self, semilla=1, k=50):
        return jugar_con_el_controlador(self, semilla, k)

    def test_fr007_fr011_hasta_250_imprime_lo_mismo_que_historia_250(self):
        partida = self.jugada()
        esperado = historia(partida, 250)
        self.assertEqual(consultar(partida, 250), esperado)
        self.assertEqual(esperado[0], "Historia — instante 250")

    def test_fr007_fr011_para_muchos_instantes_el_texto_es_el_mismo(self):
        partida = self.jugada(semilla=2)
        reloj = partida.controlador.linea.reloj_actual
        instantes = [0, 1, 99, 100, 101, 250, reloj // 2, reloj - 1]
        esperado = [historia(partida, t) for t in instantes]
        partida.controlador.bitacora.cerrar()
        for t, texto in zip(instantes, esperado):
            with self.subTest(t=t):
                self.assertEqual(ConsultaHistoria(partida.nuevo_gestor(iniciado=False), t).reproducir(
                    partida.ruta_bitacora), texto)

    def test_fr011_solo_el_resumen_sin_las_lineas_de_un_replay_normal(self):
        partida = self.jugada()
        lineas = consultar(partida, 250)
        self.assertTrue(lineas[0].startswith("Historia — "))
        for linea in lineas:
            self.assertNotIn("Reproducción finalizada", linea)
            self.assertFalse(linea.startswith("Resumen:"))

    def test_fr011_no_instancia_la_vista(self):
        partida = self.jugada()
        with mock.patch("Vista.VistaConsola.VistaConsola", side_effect=AssertionError("instanció la vista")):
            self.assertEqual(len(consultar(partida, 250)) > 1, True)

    def test_fr028_k_no_cambia_el_texto(self):
        partida = self.jugada()
        referencia = consultar(partida, 250, k=1)
        self.assertEqual(consultar(partida, 250, k=500), referencia)
        self.assertEqual(consultar(partida, 250, k=50), referencia)

    def test_fr011_no_deja_carpetas_ni_copias_al_terminar(self):
        partida = self.jugada()
        partida.controlador.bitacora.cerrar()
        consulta = ConsultaHistoria(partida.nuevo_gestor(iniciado=False), 250)
        consulta.reproducir(partida.ruta_bitacora)
        self.assertIsNone(consulta.carpeta)


class PruebasPartidaTerminada(BasePartida):
    """T056 (Escenario US4-2 y edge «partida terminada»; FR-012)."""

    def victoria(self):
        partida = self.partida()
        jugar(partida, ["mover S", "mover E", "mover E"])
        self.assertEqual(partida.motor.estado_partida(), "victoria")
        return partida

    def derrota(self):
        # vida 3 y una rata en la sala 2: el jugador entra y espera hasta caer
        partida = self.partida(jugador={"vida_max": 3, "ataque": 1, "defensa": 0, "velocidad": 100})
        jugar(partida, ["mover E"] + ["esperar"] * 8)
        self.assertEqual(partida.motor.estado_partida(), "derrota")
        return partida

    def test_fr012_t_mayor_que_el_final_avisa_y_muestra_el_estado_final(self):
        partida = self.victoria()
        final = partida.motor.reloj
        lineas = consultar(partida, 5000)
        self.assertEqual(lineas[0], AVISO.format(t=5000, final=final))
        self.assertEqual(lineas[1], f"Historia — estado final (reloj {final})")
        self.assertIn("Resultado: victoria", lineas)

    def test_fr012_t_igual_al_reloj_final_no_lleva_aviso(self):
        partida = self.victoria()
        final = partida.motor.reloj
        lineas = consultar(partida, final)
        self.assertEqual(lineas[0], f"Historia — estado final (reloj {final})")
        self.assertEqual(lineas, consultar(partida, final + 1)[1:])        # el mismo estado final, sin el aviso
        self.assertIn("Resultado: victoria", lineas)

    def test_fr012_t_menor_que_el_final_es_un_instante_y_no_trae_resultado(self):
        partida = self.victoria()
        lineas = consultar(partida, 150)
        self.assertEqual(lineas[0], "Historia — instante 150")
        self.assertFalse(any(linea.startswith("Resultado:") for linea in lineas))

    def test_fr012_una_derrota_tambien_trae_el_resultado(self):
        partida = self.derrota()
        final = partida.motor.reloj
        lineas = consultar(partida, final + 1000)
        self.assertEqual(lineas[0], AVISO.format(t=final + 1000, final=final))
        self.assertIn("Resultado: derrota", lineas)
        self.assertEqual(consultar(partida, final)[0], f"Historia — estado final (reloj {final})")

    def test_fr012_con_la_partida_en_curso_el_final_no_tiene_resultado(self):
        partida = self.partida()
        jugar(partida, ["esperar", "esperar"])
        final = partida.motor.reloj
        lineas = consultar(partida, final)
        self.assertEqual(lineas[0], f"Historia — estado final (reloj {final})")
        self.assertFalse(any(linea.startswith("Resultado:") for linea in lineas))

    def test_fr012_el_final_es_el_de_reproducir_la_bitacora_completa(self):
        partida = self.victoria()
        lineas = consultar(partida, 99999)
        self.assertEqual(lineas[2:-1], huella(partida.motor))
        self.assertEqual(lineas[-1], "Resultado: victoria")


class PruebasRetroceso(BasePartida):
    """T057 (Escenario US4-3; FR-011, FR-015): la bitácora con `retroceder` da la historia vigente."""

    def partida_con_pergaminos(self):
        contenido_con = CONTENIDO_LINEA + [contenido_sala(1, objetos=(PERGAMINO,) * 2)]
        partida = self.partida(contenido=contenido_con)
        suelo = partida.motor.obtener_objetos_suelo(partida.motor.jugador.sala)
        jugar(partida, [f"recoger {suelo[0].instancia_id}", "esperar", "mover S", "esperar"])
        return partida

    def test_fr015_el_resumen_no_refleja_la_accion_revertida(self):
        partida = self.partida_con_pergaminos()
        jugar(partida, ["mover E"])                       # esta acción se va a revertir
        reloj_revertido = partida.motor.reloj
        jugar(partida, ["retroceder"])
        self.assertLess(partida.motor.reloj, reloj_revertido)
        final = partida.motor.reloj
        vigente = historia(partida, final)                # el estado actual de la partida
        lineas = consultar(partida, final)
        self.assertEqual(lineas[1:], vigente[1:])
        self.assertEqual(lineas[0], f"Historia — estado final (reloj {final})")
        sala_final = partida.motor.jugador.sala.id
        self.assertEqual(lineas[1], f"Sala {sala_final}: {partida.motor.jugador.sala.nombre}")

    def test_fr015_un_instante_que_solo_existia_en_lo_revertido_no_existe(self):
        partida = self.partida_con_pergaminos()
        jugar(partida, ["mover E"])
        reloj_revertido = partida.motor.reloj
        jugar(partida, ["retroceder"])
        final = partida.motor.reloj
        lineas = consultar(partida, reloj_revertido)
        self.assertEqual(lineas[0], AVISO.format(t=reloj_revertido, final=final))

    def test_fr011_fr015_un_retroceso_posterior_a_t_no_cambia_lo_que_se_veia_en_t(self):
        partida = self.partida_con_pergaminos()
        instantes = [0, 50, 100, 150, 250]
        antes = [historia(partida, t) for t in instantes]   # `historia` antes del retroceso
        jugar(partida, ["mover E", "retroceder", "esperar"])
        partida.controlador.bitacora.cerrar()
        for t, esperado in zip(instantes, antes):
            with self.subTest(t=t):
                por_replay = ConsultaHistoria(partida.nuevo_gestor(iniciado=False), t).reproducir(partida.ruta_bitacora)
                # Se compara sin la línea del inventario: `retroceder` gasta un pergamino y la serie de pergaminos
                # guarda un solo valor por posición, así que dentro de la última acción antes del retroceso (t = 250)
                # el recuento ya es el posterior. Lo mismo hace la partida jugada: `historia` y `--hasta` coinciden.
                self.assertEqual(sin_inventario(por_replay), sin_inventario(esperado))
                self.assertEqual(por_replay, historia(partida, t))

    def test_fr015_despues_del_retroceso_la_accion_nueva_si_se_ve(self):
        partida = self.partida_con_pergaminos()
        jugar(partida, ["mover E", "retroceder", "esperar"])
        final = partida.motor.reloj
        lineas = consultar(partida, final - 50)
        self.assertEqual(lineas, historia(partida, final - 50))


class PruebasCarga(unittest.TestCase):
    """T058 (Escenario US4-6; FR-030): bitácora con `@cargar`, con el reloj global y continuo. Es el ejemplo de
    formato-bitacora.md: `mover E`, `esperar`, se guarda en la decisión 3 (reloj 200), lo jugado después no está, `@cargar`,
    `esperar`."""

    def setUp(self):
        self.sesion = SesionLinea(k=3, semilla=3)
        self.addCleanup(self.sesion.cerrar)
        sesion = self.sesion
        self.assertEqual(sesion.hacer([("mover", "E"), ("esperar", "")]), 2)
        self.reloj_guardado = sesion.motor.reloj
        self.assertEqual(self.reloj_guardado, 200)
        sesion.guardar_y_cargar(entre=[("mover", "O"), ("esperar", "")])    # lo jugado entre el guardado y la carga
        self.assertEqual(sesion.motor.reloj, 200)
        self.assertEqual(sesion.hacer([("esperar", "")]), 1)
        self.final = sesion.motor.reloj
        self.ruta = os.path.join(sesion.partida.carpeta.name, "con_carga.log")
        gestor = sesion.partida.gestor
        bitacora = BitacoraPartida(self.ruta, CRIPTA_NIEBLA, gestor.version_cripta(CRIPTA_NIEBLA),
                                   gestor.version_catalogo(), 3)
        for nombre, argumento in acciones_del_guion(sesion.linea.a_registro()):
            if nombre == "@cargar":
                bitacora.marcar_carga()
            else:
                bitacora.registrar(nombre, argumento)
        bitacora.cerrar()

    def consultar(self, t, k=50):
        gestor = self.sesion.partida.nuevo_gestor(iniciado=False)
        return ConsultaHistoria(gestor, t, k).reproducir(self.ruta)

    def test_fr030_hasta_0_es_la_decision_1(self):
        self.assertEqual(self.consultar(0)[1:], self.sesion.decisiones[0][1])
        self.assertEqual(self.consultar(0)[0], "Historia — instante 0")

    def test_fr030_hasta_150_esta_dentro_de_la_accion_2_antes_del_guardado(self):
        lineas = self.consultar(150)
        self.assertEqual(lineas[0], "Historia — instante 150")
        self.assertEqual(lineas, [linea for linea in lineas_resumen(self.sesion.linea.consultar_instante(
            150, self.sesion.motor))])

    def test_fr030_hasta_200_es_la_decision_del_motor_cargado(self):
        lineas = self.consultar(200)
        self.assertEqual(lineas[1:], self.sesion.decisiones[2][1])
        # lo jugado entre el guardado y la carga (mover O) no existe: el jugador sigue en la sala 2
        self.assertEqual(lineas[1].split(":")[0], "Sala 2")

    def test_fr030_hasta_250_esta_dentro_de_la_accion_posterior_a_la_carga(self):
        lineas = self.consultar(250)
        self.assertEqual(lineas, lineas_resumen(self.sesion.linea.consultar_instante(250, self.sesion.motor)))

    def test_fr030_hasta_el_reloj_final_es_el_estado_final_sin_aviso(self):
        lineas = self.consultar(self.final)
        self.assertEqual(lineas[0], f"Historia — estado final (reloj {self.final})")
        self.assertEqual(lineas[1:], huella(self.sesion.motor))

    def test_fr030_hasta_99999_avisa_y_muestra_el_estado_final(self):
        lineas = self.consultar(99999)
        self.assertEqual(lineas[0], AVISO.format(t=99999, final=self.final))
        self.assertEqual(lineas[1], f"Historia — estado final (reloj {self.final})")
        self.assertEqual(lineas[2:], huella(self.sesion.motor))

    def test_fr030_el_reloj_es_global_y_continuo(self):
        relojes = [self.sesion.linea.guion_reloj[posicion] for posicion in range(len(self.sesion.linea.guion_tipo))]
        self.assertEqual(relojes[:2], [0, 100])                        # las dos primeras acciones, antes de guardar
        self.assertEqual(self.sesion.linea.guion_tipo[2], "CARGA")
        self.assertEqual(relojes[2], 200)                              # el reloj cargado sigue el de antes
        self.assertEqual(self.sesion.linea.guion_reloj[3], 200)        # la acción siguiente parte de ahí

    def test_fr028_fr030_k_no_cambia_nada_con_una_carga(self):
        for t in (0, 150, 200, 250, self.final, 99999):
            with self.subTest(t=t):
                self.assertEqual(self.consultar(t, k=1), self.consultar(t, k=500))


# ───────────────────────── Lo mismo, por main.py --replay --hasta (T055 a T058) ─────────────────────────

class PorMain:
    """Hace que `consultar` pase por `main.py`: las pruebas de la clase base se repiten con el programa entero."""

    def setUp(self):
        super().setUp()
        VIA[0] = "main"
        self.addCleanup(self.volver_a_consulta)

    @staticmethod
    def volver_a_consulta():
        VIA[0] = "consulta"


class PruebasIgualQueHistoriaPorMain(PorMain, PruebasIgualQueHistoria):
    """T055 (Escenario US4-1, Quickstart 8) por `main`: el mismo texto que `historia 250`, código 0, sin vista."""

    def test_fr011_main_no_crea_la_vista_ni_imprime_nada_que_no_sea_el_resumen(self):
        partida = self.jugada()
        lineas = consultar(partida, 250)         # por_main ya exige código 0, sin vista y sin «Reproducción finalizada.»
        self.assertEqual(lineas[0], "Historia — instante 250")
        self.assertEqual(lineas, historia(partida, 250))
        for linea in lineas:
            self.assertFalse(linea.startswith(("Reloj:", "Resumen:", "!")), linea)


class PruebasPartidaTerminadaPorMain(PorMain, PruebasPartidaTerminada):
    """T056 por `main`: el aviso, el estado final y `Resultado:` con código 0."""


class PruebasRetrocesoPorMain(PorMain, PruebasRetroceso):
    """T057 por `main`."""


class PruebasCargaPorMain(PruebasCarga):
    """T058 por `main`: la bitácora con `@cargar` y la tabla del ejemplo, con el reloj global y continuo."""

    def consultar(self, t, k=50):
        partida = self.sesion.partida
        return por_main(partida, t, k, bitacora=self.ruta)


if __name__ == "__main__":
    unittest.main()
