# El costo de las salidas en el paquete --offline y en la caché en disco (spec 003, T032; FR-008, FR-002).
# Sin red: paquete offline (crear_paquete_niebla) y caché en carpetas temporales, borradas con addCleanup.
#
# Cripta de prueba (las salidas son dirigidas; cada sentido declara el suyo):
#   1 -E-> 2 cuesta 250 y 2 -O-> 1 cuesta 120 (costos distintos por sentido)
#   1 -S-> 3 cuesta 1;  3 -N-> 1 cuesta 300
#   2 -E-> 4 no declara costo (vale 100 en el juego, FR-002);  4 -O-> 2 cuesta 7
#
# Lo que conserva cada etapa:
#   - El paquete --offline conserva la ausencia: la salida 2 -E-> 4 no tiene la clave "costo" en el JSON.
#   - Al leerla, Salida.desde_json le da costo 100 (COSTO_POR_DEFECTO) y Salida.a_json lo escribe siempre: en la
#     caché en disco la salida sin costo queda con "costo": 100, no ausente. Es el diseño actual de DTOS/Salida.py
#     (ver test_costo_salida.TestCostoDesdeElPaquete); estas pruebas lo fijan y comprueban que el juego usa 100.

import json
import os
import sys
import tempfile
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from API.Fuentes import FuenteDatosOffline
from AlmacenamientoLocalApi.AlmacenamientoLocalApi import AlmacenamientoLocalApi
from Controlador.ControladorPartida import ControladorPartida
from Gestor.GestorDatos import GestorDatos
from tests.test_integracion import VistaFalsa
from tests.utiles_niebla import CRIPTA_NIEBLA, crear_paquete_niebla, salida

SALAS = [
    {"id": 1, "nombre": "A", "salidas": {"E": salida(2, costo=250), "S": salida(3, costo=1)}},
    {"id": 2, "nombre": "B", "salidas": {"O": salida(1, costo=120), "E": salida(4)}},
    {"id": 3, "nombre": "C", "salidas": {"N": salida(1, costo=300)}},
    {"id": 4, "nombre": "Salida", "salidas": {"O": salida(2, costo=7)}},
]
SIN_COSTO = (2, "E")      # la única salida que no declara costo

# (sala, dirección, destino, costo declarado o None), ordenado por sala y dirección
DECLARADAS = [
    (1, "E", 2, 250), (1, "S", 3, 1),
    (2, "E", 4, None), (2, "O", 1, 120),
    (3, "N", 1, 300),
    (4, "O", 2, 7),
]
# Lo mismo con el valor que usa el juego: 100 para la salida sin costo (FR-002)
EN_EL_JUEGO = [(sala, direccion, destino, 100 if costo is None else costo)
               for sala, direccion, destino, costo in DECLARADAS]
VERSION = "v1"            # la que escribe crear_paquete_niebla en criptas/<id>/version.json


def salidas_de(esqueleto):
    """(sala, dirección, destino, salida.costo) de cada salida de un esqueleto de SalaEsqueleto, ordenado."""
    return sorted((sala.id, direccion, sala.salidas[direccion].sala_destino, sala.salidas[direccion].costo)
                  for sala in esqueleto for direccion in sala.salidas)


def salidas_json(salas_json):
    """(sala, dirección, destino, costo o None si falta la clave) de cada salida de una lista de salas en JSON."""
    return sorted((sala["id"], direccion, datos["sala"], datos.get("costo"))
                  for sala in salas_json for direccion, datos in sala["salidas"].items())


class FuenteSinEsqueleto(FuenteDatosOffline):
    """Falla si se le pide el esqueleto: lo que devuelva el gestor tiene que salir de la caché en disco."""

    def obtener_esqueleto_cripta(self, id_cripta):
        raise AssertionError("el esqueleto debía salir de la caché en disco")


class BaseCostoCache(unittest.TestCase):

    def setUp(self):
        carpeta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(carpeta.cleanup)
        self.carpeta = carpeta.name
        self.paquete = os.path.join(self.carpeta, "paquete")
        self.cache = os.path.join(self.carpeta, "cache")
        crear_paquete_niebla(self.paquete, SALAS)

    def ruta_cache(self):
        return os.path.join(self.cache, f"esqueleto_{CRIPTA_NIEBLA}.json")

    def guardar_en_cache(self):
        """Lee el esqueleto del paquete y lo guarda con AlmacenamientoLocalApi.guardar_esqueleto. Devuelve el JSON
        escrito en disco."""
        esqueleto = FuenteDatosOffline(self.paquete).obtener_esqueleto_cripta(CRIPTA_NIEBLA)
        AlmacenamientoLocalApi(self.cache).guardar_esqueleto(CRIPTA_NIEBLA, VERSION, esqueleto)
        with open(self.ruta_cache(), encoding="utf-8") as archivo:
            return json.load(archivo)

    def leer_desde_cache(self):
        """GestorDatos.obtener_esqueleto con una fuente que no entrega esqueleto: solo puede leer la caché."""
        gestor = GestorDatos(FuenteSinEsqueleto(self.paquete), ruta_base=self.cache, cache_size=25)
        return gestor.obtener_esqueleto(CRIPTA_NIEBLA)


class TestCostoEnElPaquete(BaseCostoCache):

    def test_fr008_t032_paquete_offline_conserva_el_costo_de_cada_salida(self):
        """T032 (FR-008, FR-002): el JSON del paquete --offline trae el costo declarado de cada salida (1, 300, 7 y
        los dos sentidos de 1–2 con 250 y 120) y la salida sin costo sigue sin la clave; leído con
        FuenteDatosOffline, cada salida tiene su costo y la que no lo declara vale 100."""
        with open(os.path.join(self.paquete, "criptas", CRIPTA_NIEBLA, "salas.json"), encoding="utf-8") as archivo:
            en_disco = json.load(archivo)["salas"]
        self.assertEqual(salidas_json(en_disco), DECLARADAS)
        sala_2 = [sala for sala in en_disco if sala["id"] == SIN_COSTO[0]][0]
        self.assertNotIn("costo", sala_2["salidas"][SIN_COSTO[1]])

        esqueleto = FuenteDatosOffline(self.paquete).obtener_esqueleto_cripta(CRIPTA_NIEBLA)
        self.assertEqual(salidas_de(esqueleto), EN_EL_JUEGO)


class TestCostoEnLaCache(BaseCostoCache):

    def test_fr008_t032_guardar_esqueleto_y_obtener_esqueleto_conservan_el_costo(self):
        """T032 (FR-008): AlmacenamientoLocalApi.guardar_esqueleto escribe en disco el costo de cada salida, y
        GestorDatos.obtener_esqueleto (sin poder ir a la fuente) lo devuelve igual, salida por salida y sentido por
        sentido: 1→2 cuesta 250 y 2→1 cuesta 120."""
        en_disco = self.guardar_en_cache()
        self.assertEqual(en_disco["version"], VERSION)
        self.assertEqual(salidas_json(en_disco["esqueleto"]), EN_EL_JUEGO)

        self.assertEqual(salidas_de(self.leer_desde_cache()), EN_EL_JUEGO)

    def test_fr008_t032_el_gestor_llena_la_cache_y_la_segunda_lectura_da_el_mismo_costo(self):
        """T032 (FR-008): el camino real del juego: un gestor sobre el paquete --offline llena la caché con
        obtener_esqueleto (que llama a guardar_esqueleto), y otro gestor que solo puede leer la caché da el mismo
        costo en cada salida."""
        gestor = GestorDatos(FuenteDatosOffline(self.paquete), ruta_base=self.cache, cache_size=25)
        self.assertEqual(salidas_de(gestor.obtener_esqueleto(CRIPTA_NIEBLA)), EN_EL_JUEGO)
        self.assertTrue(os.path.exists(self.ruta_cache()))

        self.assertEqual(salidas_de(self.leer_desde_cache()), EN_EL_JUEGO)

    def test_fr008_t032_un_costo_alterado_en_disco_se_nota_al_leer(self):
        """T032 (FR-008), prueba negativa: si en la caché se borra el costo de 1→2 (250) y se cambia el de 2→1
        (120 → 999), obtener_esqueleto devuelve 100 y 999: la lectura sale de verdad del disco y una caché que no
        conservara el costo no pasaría las pruebas de arriba."""
        en_disco = self.guardar_en_cache()
        for sala in en_disco["esqueleto"]:
            if sala["id"] == 1:
                del sala["salidas"]["E"]["costo"]
            if sala["id"] == 2:
                sala["salidas"]["O"]["costo"] = 999
        with open(self.ruta_cache(), "w", encoding="utf-8") as archivo:
            json.dump(en_disco, archivo)

        leidas = salidas_de(self.leer_desde_cache())
        self.assertNotEqual(leidas, EN_EL_JUEGO)
        self.assertIn((1, "E", 2, 100), leidas)
        self.assertIn((2, "O", 1, 999), leidas)


class TestSinCostoEnElJuego(BaseCostoCache):

    def test_fr002_t032_salida_sin_costo_vale_100_en_el_juego_tras_la_cache(self):
        """T032 (FR-002, FR-008): la salida 2→4, sin costo en el paquete, llega desde la caché con el valor por
        omisión y motor.costo_salida da 100; las demás dan su costo declarado. La partida se arma con
        ControladorPartida.nueva_partida y el esqueleto sale de la caché (la fuente no lo entrega).

        Verifica el valor 100 que usa el juego, no la ausencia del campo: en la caché la salida sin costo queda con
        "costo": 100 explícito (Salida.desde_json pone 100 si falta la clave y a_json siempre lo escribe), y eso no
        incumple FR-002. La ausencia de la clave solo se conserva en el JSON del paquete (ver
        test_fr008_t032_paquete_offline_conserva_el_costo_de_cada_salida)."""
        self.guardar_en_cache()
        gestor = GestorDatos(FuenteSinEsqueleto(self.paquete), ruta_base=self.cache, cache_size=25)
        controlador = ControladorPartida(gestor, VistaFalsa(), os.path.join(self.carpeta, "partida.log"))
        self.addCleanup(controlador._cerrar)
        controlador.nueva_partida(CRIPTA_NIEBLA, 7)
        motor = controlador.motor

        en_el_motor = sorted((sala.id, direccion, sala.salidas[direccion].sala_destino,
                              motor.costo_salida(sala.salidas[direccion]))
                             for sala in motor.salas for direccion in sala.salidas)
        self.assertEqual(en_el_motor, EN_EL_JUEGO)
        sala_2 = [sala for sala in motor.salas if sala.id == SIN_COSTO[0]][0]
        self.assertEqual(motor.costo_salida(sala_2.salidas[SIN_COSTO[1]]), 100)


if __name__ == "__main__":
    unittest.main()
