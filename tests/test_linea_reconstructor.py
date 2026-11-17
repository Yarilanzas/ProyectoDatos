# ReconstructorLinea: rehace la línea de una partida guardada reproduciendo su guion (spec 004, T069; FR-022, FR-025, FR-031).
# El guion se reproduce desde la cripta y la semilla del encabezado con `Reproductor.reproducir_acciones` y un
# `ObservadorLinea`; se comparan los sellos `(reloj, secuencia)` de cada acción (la línea reconstruida debe dar el mismo
# registro) y, al final, reloj, sala, vida y acciones contra el bloque del jugador. Una diferencia termina en
# `Versión incompatible: la línea de tiempo no coincide con la partida` (código 2) sin cargar nada. Sin red: los datos salen
# del paquete offline y de la carpeta de datos locales de cada prueba.

import os
import sys
import tempfile
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from API.Fuentes import FuenteDatosOffline
from Controlador.ControladorPartida import guardar_motor
from Controlador.ReconstructorLinea import ReconstructorLinea
from Gestor.GestorDatos import GestorDatos
from Gestor.GestorHistorico import SinDatosParaHistoria
from Gestor.PreparadorPartida import cargar_partida
from Modelo.LineaTiempo import TIPO_CARGA
from Persistencia.ArchivoPartida import LectorPartida
from Persistencia.ConversorPartida import RestauradorPartida
from Persistencia.FormatoBinario import VersionIncompatible
from Persistencia.RegistroLinea import RegistroLinea
from tests.test_linea_consulta import contenido
from tests.utiles_linea import (SesionLinea, archivo_con_linea, copia_sin_datos, crpt_con_version, huella,
                                leer_bloque_linea)

NO_COINCIDE = "la línea de tiempo no coincide con la partida"


def cabecera(ruta):
    """Encabezado y registro del jugador de un CRPT, como los lee el controlador al cargar."""
    restaurador = RestauradorPartida(ruta)
    try:
        return restaurador.encabezado, restaurador.leer_jugador()
    finally:
        restaurador.cerrar()


class BaseReconstructor(unittest.TestCase):

    def sesion(self, **opciones):
        sesion = SesionLinea(**opciones)
        self.addCleanup(sesion.cerrar)
        return sesion

    def guardar(self, sesion, nombre="final.cripta"):
        ruta = os.path.join(sesion.partida.carpeta.name, nombre)
        guardar_motor(sesion.motor, ruta, sesion.partida.gestor)
        return ruta

    def reconstructor(self, sesion, gestor=None):
        gestor = sesion.partida.nuevo_gestor(iniciado=False) if gestor is None else gestor
        reconstructor = ReconstructorLinea(gestor)
        self.addCleanup(reconstructor.cerrar)
        return reconstructor

    def comprobar_decisiones(self, sesion, linea, motor):
        """Cada `#k` de la línea reconstruida da el estado que se vio antes de esa acción en la partida original."""
        self.assertEqual(linea.acciones, len(sesion.decisiones))
        for k in range(1, linea.acciones + 1):
            with self.subTest(k=k):
                self.assertEqual(contenido(linea.consultar_accion(k, motor)), sesion.decisiones[k - 1][1])


class PruebasReconstruir(BaseReconstructor):

    def test_fr022_con_acciones_y_un_retroceso_da_el_mismo_guion_y_los_mismos_sellos(self):
        sesion = self.sesion(pergaminos=2, k=3)
        sesion.jugar(4)
        self.assertTrue(sesion.retroceder())
        sesion.jugar(5)
        ruta = self.guardar(sesion)
        encabezado, jugador = cabecera(ruta)
        registro = sesion.linea.a_registro()

        linea = self.reconstructor(sesion).reconstruir(registro, encabezado, jugador)

        self.assertEqual(linea.a_registro(), registro)        # guion y sello de cada acción
        self.assertEqual(linea.k, 3)
        self.assertEqual(linea.acciones, sesion.linea.acciones)
        self.assertEqual(linea.reloj_actual, sesion.linea.reloj_actual)
        self.assertEqual(linea.cantidad_puntos, sesion.linea.cantidad_puntos)
        self.comprobar_decisiones(sesion, linea, sesion.motor)

    def test_fr022_con_cargas_en_el_guion_reproduce_la_recarga_y_abre_las_epocas(self):
        sesion = self.sesion(pergaminos=2, k=4)
        sesion.jugar(5)
        sesion.guardar_y_cargar()
        sesion.jugar(4)
        self.assertTrue(sesion.retroceder())
        sesion.jugar(3)
        sesion.guardar_y_cargar()
        sesion.jugar(2)
        ruta = self.guardar(sesion)
        encabezado, jugador = cabecera(ruta)
        registro = sesion.linea.a_registro()
        reconstructor = self.reconstructor(sesion)

        linea = reconstructor.reconstruir(registro, encabezado, jugador)

        self.assertEqual(linea.a_registro(), registro)
        self.assertEqual(linea.epocas_accion, sesion.linea.epocas_accion)
        self.assertIsNone(linea.epocas_ruta[0])
        for copia in linea.epocas_ruta[1:]:
            self.assertTrue(os.path.isfile(copia))
            self.assertEqual(os.path.dirname(copia), reconstructor.carpeta)   # en la carpeta propia
        self.comprobar_decisiones(sesion, linea, sesion.motor)

    def test_fr022_una_partida_sin_acciones(self):
        sesion = self.sesion()
        ruta = self.guardar(sesion)
        encabezado, jugador = cabecera(ruta)
        linea = self.reconstructor(sesion).reconstruir(sesion.linea.a_registro(), encabezado, jugador)
        self.assertEqual(linea.acciones, 0)
        self.assertEqual(linea.a_registro(), sesion.linea.a_registro())

    def test_fr031_el_k_es_el_del_bloque_guardado(self):
        sesion = self.sesion(k=7)
        sesion.jugar(4)
        ruta = self.guardar(sesion)
        encabezado, jugador = cabecera(ruta)
        linea = self.reconstructor(sesion).reconstruir(sesion.linea.a_registro(), encabezado, jugador, k=2)
        self.assertEqual(linea.k, 7)

    def test_fr022_el_bloque_leido_del_archivo_reconstruye_la_misma_linea(self):
        sesion = self.sesion(pergaminos=1, k=3)
        sesion.jugar(6)
        sesion.guardar_y_cargar()
        sesion.jugar(3)
        sin_linea = self.guardar(sesion, "sin_linea.cripta")
        con_linea = archivo_con_linea(sin_linea, os.path.join(sesion.partida.carpeta.name, "con_linea.cripta"),
                                      sesion.linea.a_registro())
        registro = RegistroLinea.from_bytes(leer_bloque_linea(con_linea))
        encabezado, jugador = cabecera(con_linea)
        linea = self.reconstructor(sesion).reconstruir(registro, encabezado, jugador)
        self.assertEqual(linea.a_registro(), sesion.linea.a_registro())
        self.comprobar_decisiones(sesion, linea, sesion.motor)


class PruebasAbrirLaEpocaDeLaCarga(BaseReconstructor):

    def cargado(self, sesion, ruta):
        motor = cargar_partida(ruta, sesion.partida.nuevo_gestor(iniciado=False))
        self.addCleanup(lambda: motor.restaurador is not None and motor.restaurador.cerrar())
        return motor

    def test_fr025_con_el_motor_cargado_agrega_la_carga_con_su_copia_privada(self):
        sesion = self.sesion(pergaminos=2, k=3)
        sesion.jugar(5)
        sesion.retroceder()
        sesion.jugar(4)
        ruta = self.guardar(sesion)
        encabezado, jugador = cabecera(ruta)
        registro = sesion.linea.a_registro()
        reconstructor = self.reconstructor(sesion)
        motor = self.cargado(sesion, ruta)

        linea = reconstructor.reconstruir(registro, encabezado, jugador, motor_cargado=motor)

        n = sesion.linea.acciones
        self.assertEqual(linea.acciones, n)
        self.assertEqual(linea.guion_tipo[-1], TIPO_CARGA)
        self.assertEqual(linea.guion_reloj[-1], motor.reloj)
        self.assertEqual(linea.epocas_accion[-1], n)
        copia = linea.epocas_ruta[-1]
        self.assertTrue(os.path.isfile(copia))
        self.assertNotEqual(os.path.abspath(copia), os.path.abspath(ruta))   # no es el archivo cargado, sino una copia
        self.assertEqual(os.path.dirname(copia), reconstructor.carpeta)
        # lo anterior sigue consultable, y el motor cargado sigue jugando con la línea
        self.comprobar_decisiones(sesion, linea, motor)
        self.assertEqual(linea.consultar_accion(n + 1, motor).referencia, ("actual", None))
        antes = huella(motor)
        self.assertTrue(motor.ejecutar_accion("esperar", ""))
        linea.registrar_accion(motor, "esperar", "")
        self.assertEqual(contenido(linea.consultar_accion(n + 1, motor)), antes)

    def test_fr025_con_la_copia_borrada_el_archivo_original_ya_no_hace_falta(self):
        sesion = self.sesion(k=3)
        sesion.jugar(6)
        ruta = self.guardar(sesion)
        encabezado, jugador = cabecera(ruta)
        reconstructor = self.reconstructor(sesion)
        motor = self.cargado(sesion, ruta)
        linea = reconstructor.reconstruir(sesion.linea.a_registro(), encabezado, jugador, motor_cargado=motor)
        motor.restaurador.cerrar()
        motor.restaurador = None
        os.remove(ruta)                       # un guardado posterior pudo reemplazarlo
        antes = huella(motor)
        self.assertTrue(motor.ejecutar_accion("esperar", ""))
        linea.registrar_accion(motor, "esperar", "")
        self.assertEqual(contenido(linea.consultar_accion(7, motor)), antes)   # el clon usa la copia privada

    def test_fr022_sin_bloque_de_linea_la_linea_empieza_en_la_carga(self):
        sesion = self.sesion(k=3)
        sesion.jugar(4)
        ruta = self.guardar(sesion)
        encabezado, jugador = cabecera(ruta)
        reconstructor = self.reconstructor(sesion)
        motor = self.cargado(sesion, ruta)

        linea = reconstructor.reconstruir(None, encabezado, jugador, motor_cargado=motor, k=9)

        self.assertEqual(linea.k, 9)                       # largo línea = 0: rige el K de la ejecución
        self.assertEqual(linea.acciones, 0)
        self.assertEqual(linea.cantidad_puntos, 1)
        self.assertEqual(linea.reloj_actual, motor.reloj)
        self.assertTrue(os.path.isfile(linea.epocas_ruta[0]))   # la época 0 es la carga: lleva la copia privada
        self.assertEqual(linea.consultar_accion(1, motor).referencia, ("actual", None))
        antes = huella(motor)
        self.assertTrue(motor.ejecutar_accion("esperar", ""))
        linea.registrar_accion(motor, "esperar", "")
        self.assertEqual(contenido(linea.consultar_accion(1, motor)), antes)

    def test_fr022_sin_bloque_de_linea_y_sin_motor_cargado_no_hay_nada_que_reconstruir(self):
        sesion = self.sesion()
        ruta = self.guardar(sesion)
        encabezado, jugador = cabecera(ruta)
        with self.assertRaises(ValueError):
            self.reconstructor(sesion).reconstruir(None, encabezado, jugador)


class PruebasLoQueNoCoincide(BaseReconstructor):

    def preparar(self, **opciones):
        sesion = self.sesion(pergaminos=2, k=3, **opciones)
        sesion.jugar(5)
        sesion.guardar_y_cargar()
        sesion.jugar(4)
        ruta = self.guardar(sesion)
        encabezado, jugador = cabecera(ruta)
        return sesion, ruta, encabezado, jugador

    def assertNoCoincide(self, reconstructor, registro, encabezado, jugador):
        with self.assertRaises(VersionIncompatible) as contexto:
            reconstructor.reconstruir(registro, encabezado, jugador)
        self.assertEqual(str(contexto.exception), NO_COINCIDE)
        self.assertIsNone(reconstructor.carpeta)          # no queda nada: ni carpeta ni copias

    def test_fr024_un_sello_cambiado_se_rechaza(self):
        sesion, ruta, encabezado, jugador = self.preparar()
        alterado = archivo_con_linea(ruta, os.path.join(sesion.partida.carpeta.name, "sello.cripta"),
                                     sesion.linea.a_registro(), "sello")
        registro = RegistroLinea.from_bytes(leer_bloque_linea(alterado))   # el bloque sigue siendo válido
        self.assertNoCoincide(self.reconstructor(sesion), registro, encabezado, jugador)

    def test_fr024_una_accion_que_el_motor_rechazaria_se_rechaza(self):
        sesion, ruta, encabezado, jugador = self.preparar()
        registros = list(sesion.linea.a_registro().registros)
        registros.append((1, "mover", "X", 99999, 0))        # dirección que no existe
        self.assertNoCoincide(self.reconstructor(sesion), RegistroLinea(sesion.linea.k, registros), encabezado,
                              jugador)

    def test_fr024_un_guion_mas_corto_que_la_partida_guardada_se_rechaza(self):
        sesion, ruta, encabezado, jugador = self.preparar()
        registros = sesion.linea.a_registro().registros
        corto = RegistroLinea(sesion.linea.k, registros[:-2])
        self.assertNoCoincide(self.reconstructor(sesion), corto, encabezado, jugador)

    def test_fr024_el_bloque_del_jugador_distinto_se_rechaza(self):
        sesion, ruta, encabezado, jugador = self.preparar()
        registro = sesion.linea.a_registro()
        for campo, delta in (("reloj", 1), ("vida", 1), ("acciones", 1), ("sala_id", 1)):
            with self.subTest(campo=campo):
                encabezado, jugador = cabecera(ruta)
                if campo == "reloj":
                    encabezado.reloj += delta
                else:
                    setattr(jugador, campo, getattr(jugador, campo) + delta)
                self.assertNoCoincide(self.reconstructor(sesion), registro, encabezado, jugador)

    def test_fr024_una_cripta_o_un_catalogo_de_otra_version_se_rechaza(self):
        sesion, ruta, encabezado, jugador = self.preparar()
        registro = sesion.linea.a_registro()
        encabezado.version_cripta = "otra-version"
        with self.assertRaises(VersionIncompatible):
            self.reconstructor(sesion).reconstruir(registro, encabezado, jugador)

    def test_fr024_los_bloques_truncado_y_con_tipo_desconocido_no_llegan_a_reconstruirse(self):
        sesion, ruta, encabezado, jugador = self.preparar()
        for modo in ("truncado", "tipo"):
            with self.subTest(modo=modo):
                alterado = archivo_con_linea(ruta, os.path.join(sesion.partida.carpeta.name, f"{modo}.cripta"),
                                             sesion.linea.a_registro(), modo)
                with self.assertRaises(VersionIncompatible):
                    RegistroLinea.from_bytes(leer_bloque_linea(alterado))


class PruebasArchivosPropios(BaseReconstructor):
    """La fabricación de archivos de `utiles_linea` (T067) produce archivos que el lector real entiende."""

    def test_fr022_un_bloque_de_linea_no_vacio_no_estorba_a_las_salas_ni_a_la_carga(self):
        sesion = self.sesion(k=3)
        sesion.jugar(6)
        sin_linea = self.guardar(sesion, "sin_linea.cripta")
        con_linea = archivo_con_linea(sin_linea, os.path.join(sesion.partida.carpeta.name, "con_linea.cripta"),
                                      sesion.linea.a_registro())
        bloque = sesion.linea.a_registro().to_bytes()
        self.assertEqual(leer_bloque_linea(con_linea), bloque)
        self.assertEqual(leer_bloque_linea(sin_linea), b"")
        with LectorPartida(sin_linea) as uno, LectorPartida(con_linea) as otro:
            self.assertEqual(otro._inicio_salas, uno._inicio_salas + len(bloque))
            self.assertEqual(otro.encabezado.offset_indice, uno.encabezado.offset_indice + len(bloque))
            salas_uno = uno.leer_todas_salas()
            salas_otro = otro.leer_todas_salas()
            self.assertEqual([sala.to_bytes() for sala in salas_otro], [sala.to_bytes() for sala in salas_uno])
        motor = cargar_partida(con_linea, sesion.partida.nuevo_gestor(iniciado=False))
        self.addCleanup(lambda: motor.restaurador.cerrar())
        self.assertEqual(motor.reloj, sesion.motor.reloj)

    def test_fr024_las_versiones_1_2_y_desconocida_se_rechazan_sin_cargar_nada(self):
        sesion = self.sesion()
        sesion.jugar(2)
        ruta = self.guardar(sesion)
        for version in (1, 2, 99):
            with self.subTest(version=version):
                destino = crpt_con_version(ruta, os.path.join(sesion.partida.carpeta.name, f"v{version}.cripta"),
                                           version)
                with self.assertRaises(VersionIncompatible):
                    cargar_partida(destino, sesion.partida.nuevo_gestor(iniciado=False))

    def test_fr024_modos_alterados_desconocidos_se_rechazan(self):
        sesion = self.sesion()
        sesion.jugar(2)
        with self.assertRaises(ValueError):
            archivo_con_linea(self.guardar(sesion), os.path.join(sesion.partida.carpeta.name, "x.cripta"),
                              sesion.linea.a_registro(), "inventado")


class PruebasSinDatosLocales(BaseReconstructor):

    def test_fr022_sin_la_carpeta_de_datos_locales_lanza_sin_datos_y_no_deja_nada(self):
        sesion = self.sesion(k=3)
        sesion.jugar(5)
        ruta = self.guardar(sesion)
        encabezado, jugador = cabecera(ruta)
        registro = sesion.linea.a_registro()
        copia = copia_sin_datos(sesion.partida, "datos")
        self.addCleanup(copia.cerrar)
        gestor = GestorDatos(FuenteDatosOffline(copia.paquete), ruta_base=copia.ruta_datos, cache_size=25)
        reconstructor = ReconstructorLinea(gestor)
        self.addCleanup(reconstructor.cerrar)

        with self.assertRaises(SinDatosParaHistoria):
            reconstructor.reconstruir(registro, encabezado, jugador)
        self.assertIsNone(reconstructor.carpeta)


class PruebasCarpetaPropia(BaseReconstructor):

    def test_fr025_la_carpeta_es_propia_y_cerrar_la_borra_despues_de_cerrar_los_manejadores(self):
        sesion = self.sesion(k=3)
        sesion.jugar(4)
        sesion.guardar_y_cargar()
        sesion.jugar(3)
        ruta = self.guardar(sesion)
        encabezado, jugador = cabecera(ruta)
        reconstructor = ReconstructorLinea(sesion.partida.nuevo_gestor(iniciado=False))
        self.addCleanup(reconstructor.cerrar)
        self.assertIsNone(reconstructor.carpeta)            # no crea nada hasta que reconstruye
        linea = reconstructor.reconstruir(sesion.linea.a_registro(), encabezado, jugador)

        carpeta = reconstructor.carpeta
        self.assertTrue(os.path.isdir(carpeta))
        self.assertNotEqual(os.path.abspath(carpeta), os.path.abspath(sesion.partida.carpeta.name))
        self.assertTrue(os.path.abspath(carpeta).startswith(os.path.abspath(tempfile.gettempdir())))
        # consultar una época abre un clon sobre la copia privada (un manejador abierto en Windows)
        linea.consultar_accion(linea.acciones, sesion.motor)
        copias = [copia for copia in linea.epocas_ruta if copia is not None]
        self.assertTrue(len(copias) >= 1)

        reconstructor.cerrar()
        for copia in copias:
            self.assertFalse(os.path.exists(copia))
        self.assertFalse(os.path.exists(carpeta))
        self.assertIsNone(reconstructor.carpeta)
        reconstructor.cerrar()                              # idempotente

    def test_fr025_la_carpeta_de_recargas_no_sobrevive_a_la_reconstruccion(self):
        sesion = self.sesion(k=3)
        sesion.jugar(3)
        sesion.guardar_y_cargar()
        sesion.jugar(2)
        ruta = self.guardar(sesion)
        encabezado, jugador = cabecera(ruta)
        reconstructor = self.reconstructor(sesion)
        reconstructor.reconstruir(sesion.linea.a_registro(), encabezado, jugador)
        contenidos = os.listdir(reconstructor.carpeta)
        self.assertTrue(all(nombre.endswith(".cripta") for nombre in contenidos), contenidos)


if __name__ == "__main__":
    unittest.main()
