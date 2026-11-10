# Pruebas de la ubicación de las llaves en la fuente de datos y en la caché (spec 002, T011).
# Sin red: la fuente HTTP usa un requests.get simulado. Cada prueba cita el FR que verifica.

import json
import os
import tempfile
import unittest
from unittest import mock

from API import Excepciones
from API.Fuentes import FuenteDatos, FuenteDatosHTTP, FuenteDatosOffline
from AlmacenamientoLocalApi.AlmacenamientoLocalApi import FORMATO_LLAVES, VERSION_FORMATO_LLAVES
from Gestor.GestorDatos import GestorDatos
from tests.generador_criptas import escribir_paquete, generar_cripta
from tests.utiles_niebla import CRIPTA_NIEBLA, crear_paquete_niebla, salida

RUTA_LLAVES = "/criptas/c1/llaves"


class FuenteFija(FuenteDatos):
    # devuelve siempre el mismo cuerpo, como si fuera la respuesta del servicio
    def __init__(self, cuerpo):
        self.cuerpo = cuerpo

    def _obtener(self, ruta, params=None):
        return self.cuerpo


class FuenteOfflineContada(FuenteDatosOffline):
    # anota cada ruta pedida para contar las solicitudes a /llaves
    def __init__(self, carpeta):
        super().__init__(carpeta)
        self.rutas = []

    def _obtener(self, ruta, params=None):
        self.rutas.append(ruta)
        return super()._obtener(ruta, params)

    def pedidas_de_llaves(self):
        return len([ruta for ruta in self.rutas if ruta.endswith("/llaves")])


class RespuestaFalsa:
    def __init__(self, cuerpo, status_code=200):
        self._cuerpo = cuerpo
        self.status_code = status_code

    def json(self):
        return self._cuerpo


def _como_tuplas(ubicaciones):
    return [(u.id_llave, u.sala, u.enemigo) for u in ubicaciones]


def _leer_json(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def _escribir_json(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f)


class PruebasValidacionFuente(unittest.TestCase):

    def _error(self, cuerpo):
        with self.assertRaises(Excepciones.RespuestaInvalidaError) as contexto:
            FuenteFija(cuerpo).obtener_llaves_cripta("c1")
        return contexto.exception

    def test_fr025_entrada_sin_id(self):
        """FR-025: una entrada sin 'id' es RespuestaInvalidaError con la ruta de /llaves."""
        error = self._error({"llaves": [{"id": "k1", "sala": 1}, {"sala": 2}]})
        self.assertEqual(error.url, RUTA_LLAVES)
        self.assertIn("entrada de llave sin 'id' o 'sala'", str(error))

    def test_fr025_entrada_sin_sala(self):
        """FR-025: una entrada sin 'sala' es RespuestaInvalidaError con la ruta de /llaves."""
        error = self._error({"llaves": [{"id": "k1"}]})
        self.assertEqual(error.url, RUTA_LLAVES)
        self.assertIn("entrada de llave sin 'id' o 'sala'", str(error))

    def test_fr025_entrada_que_no_es_objeto(self):
        """FR-025: una entrada que no es un objeto también es RespuestaInvalidaError."""
        error = self._error({"llaves": ["k1"]})
        self.assertEqual(error.url, RUTA_LLAVES)

    def test_fr025_falta_la_clave_llaves(self):
        """FR-025: un cuerpo sin la clave 'llaves' es RespuestaInvalidaError."""
        error = self._error({"otra": []})
        self.assertEqual(error.url, RUTA_LLAVES)

    def test_fr025_sala_inexistente_no_es_error_de_lectura(self):
        """FR-025: una sala que no existe en el esqueleto no es error de lectura."""
        ubicaciones = FuenteFija({"llaves": [{"id": "k1", "sala": 999}]}).obtener_llaves_cripta("c1")
        self.assertEqual(_como_tuplas(ubicaciones), [("k1", 999, None)])


class PruebasOfflineYRed(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.carpeta.cleanup()

    def _por_http(self, id_cripta, cuerpo):
        fuente = FuenteDatosHTTP()
        with mock.patch("API.Fuentes.requests.get", return_value=RespuestaFalsa(cuerpo)) as get:
            ubicaciones = fuente.obtener_llaves_cripta(id_cripta)
        self.assertEqual(get.call_count, 1)
        self.assertTrue(get.call_args[0][0].endswith(f"/criptas/{id_cripta}/llaves"))
        return ubicaciones

    def test_fr028_offline_igual_que_http_con_paquete_sintetico(self):
        """FR-028: con FuenteDatosOffline y un paquete del generador se obtiene lo mismo que por HTTP."""
        cripta = generar_cripta(21, 60, 4, llave_de_enemigo=True)
        paquete = os.path.join(self.carpeta.name, "paquete")
        escribir_paquete(paquete, cripta)

        offline = FuenteDatosOffline(paquete).obtener_llaves_cripta(cripta.id_cripta)
        cuerpo = _leer_json(os.path.join(paquete, "criptas", cripta.id_cripta, "llaves.json"))
        por_red = self._por_http(cripta.id_cripta, cuerpo)

        self.assertEqual(_como_tuplas(offline), _como_tuplas(por_red))
        self.assertEqual(_como_tuplas(offline), _como_tuplas(cripta.ubicaciones()))
        self.assertIsNotNone(offline[0].enemigo)

    def test_fr028_offline_igual_que_http_con_paquete_de_niebla(self):
        """FR-028: lo mismo con un paquete de crear_paquete_niebla (llave_salida en la sala inicial)."""
        paquete = os.path.join(self.carpeta.name, "paquete")
        salas = [{"id": 1, "nombre": "A", "salidas": {"E": salida(2)}},
                 {"id": 2, "nombre": "B", "salidas": {"O": salida(1)}}]
        crear_paquete_niebla(paquete, salas, llave_salida="itm_llave")

        offline = FuenteDatosOffline(paquete).obtener_llaves_cripta(CRIPTA_NIEBLA)
        cuerpo = _leer_json(os.path.join(paquete, "criptas", CRIPTA_NIEBLA, "llaves.json"))
        self.assertEqual(_como_tuplas(offline), [("itm_llave", 1, None)])
        self.assertEqual(_como_tuplas(offline), _como_tuplas(self._por_http(CRIPTA_NIEBLA, cuerpo)))

    def test_fr024_paquete_sin_llaves_json(self):
        """FR-024: si el paquete no trae llaves.json, RuntimeError «Falta el archivo para /criptas/<id>/llaves»."""
        cripta = generar_cripta(22, 20, 2)
        paquete = os.path.join(self.carpeta.name, "paquete")
        escribir_paquete(paquete, cripta, escribir_llaves=False)
        with self.assertRaises(RuntimeError) as contexto:
            FuenteDatosOffline(paquete).obtener_llaves_cripta(cripta.id_cripta)
        self.assertIn(f"Falta el archivo para /criptas/{cripta.id_cripta}/llaves", str(contexto.exception))

    def test_fr024_paquete_de_niebla_sin_llaves_json(self):
        """FR-024: crear_paquete_niebla con escribir_llaves=False deja el paquete sin el archivo."""
        paquete = os.path.join(self.carpeta.name, "paquete")
        salas = [{"id": 1, "nombre": "A", "salidas": {}}]
        crear_paquete_niebla(paquete, salas, escribir_llaves=False)
        with self.assertRaises(RuntimeError) as contexto:
            FuenteDatosOffline(paquete).obtener_llaves_cripta(CRIPTA_NIEBLA)
        self.assertIn(f"Falta el archivo para /criptas/{CRIPTA_NIEBLA}/llaves", str(contexto.exception))


class PruebasCacheLlaves(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.cripta = generar_cripta(23, 80, 4, llave_de_enemigo=True)
        self.paquete = os.path.join(self.carpeta.name, "paquete")
        escribir_paquete(self.paquete, self.cripta)
        self.ruta_cache = os.path.join(self.carpeta.name, "cache")
        self.archivo_cache = os.path.join(self.ruta_cache, f"llaves_{self.cripta.id_cripta}.json")

    def tearDown(self):
        self.carpeta.cleanup()

    def _gestor(self):
        fuente = FuenteOfflineContada(self.paquete)
        return GestorDatos(fuente, ruta_base=self.ruta_cache), fuente

    def _cambiar_version(self, version):
        _escribir_json(os.path.join(self.paquete, "criptas", self.cripta.id_cripta, "version.json"),
                       {"version": version})

    def test_fr026_cache_valida_no_pide_llaves(self):
        """FR-026: con caché válida, obtener_llaves no hace solicitudes a /llaves."""
        gestor, fuente = self._gestor()
        gestor.obtener_llaves(self.cripta.id_cripta)
        self.assertEqual(fuente.pedidas_de_llaves(), 1)
        self.assertTrue(os.path.exists(self.archivo_cache))

        otro, fuente_otra = self._gestor()
        otro.obtener_llaves(self.cripta.id_cripta)
        self.assertEqual(fuente_otra.pedidas_de_llaves(), 0)

    def test_fr026_memoria_del_proceso_no_repite_solicitudes(self):
        """FR-026: en el mismo proceso la segunda llamada no hace ninguna solicitud."""
        gestor, fuente = self._gestor()
        gestor.obtener_llaves(self.cripta.id_cripta)
        antes = len(fuente.rutas)
        gestor.obtener_llaves(self.cripta.id_cripta)
        self.assertEqual(len(fuente.rutas), antes)

    def test_fr013_version_distinta_vuelve_a_pedir_y_reescribe(self):
        """FR-013, FR-026: si la versión de la cripta cambió, se vuelve a pedir y se reescribe la caché."""
        gestor, _ = self._gestor()
        gestor.obtener_llaves(self.cripta.id_cripta)
        self.assertEqual(_leer_json(self.archivo_cache)["version"], "v1")

        self._cambiar_version("v2")
        otro, fuente = self._gestor()
        otro.obtener_llaves(self.cripta.id_cripta)
        self.assertEqual(fuente.pedidas_de_llaves(), 1)
        self.assertEqual(_leer_json(self.archivo_cache)["version"], "v2")

    def _probar_formato_descartado(self, campo, valor):
        gestor, _ = self._gestor()
        gestor.obtener_llaves(self.cripta.id_cripta)
        datos = _leer_json(self.archivo_cache)
        datos[campo] = valor
        _escribir_json(self.archivo_cache, datos)

        otro, fuente = self._gestor()
        ubicaciones = otro.obtener_llaves(self.cripta.id_cripta)
        self.assertEqual(fuente.pedidas_de_llaves(), 1)
        reescrito = _leer_json(self.archivo_cache)
        self.assertEqual(reescrito["formato"], FORMATO_LLAVES)
        self.assertEqual(reescrito["version_formato"], VERSION_FORMATO_LLAVES)
        self.assertEqual(_como_tuplas(ubicaciones), _como_tuplas(self.cripta.ubicaciones()))

    def test_fr026_formato_distinto_se_descarta(self):
        """FR-026 (Principio VI): una caché con otro 'formato' se descarta, se vuelve a pedir y se reescribe."""
        self._probar_formato_descartado("formato", "OTRO-FORMATO")

    def test_fr026_version_formato_distinta_se_descarta(self):
        """FR-026 (Principio VI): una caché con otra 'version_formato' se descarta y se reescribe."""
        self._probar_formato_descartado("version_formato", VERSION_FORMATO_LLAVES + 1)

    def test_fr026_cache_ilegible_se_descarta(self):
        """FR-026: una caché que no se puede leer se descarta y se vuelve a pedir."""
        gestor, _ = self._gestor()
        gestor.obtener_llaves(self.cripta.id_cripta)
        with open(self.archivo_cache, "w", encoding="utf-8") as f:
            f.write("{no es json")
        otro, fuente = self._gestor()
        otro.obtener_llaves(self.cripta.id_cripta)
        self.assertEqual(fuente.pedidas_de_llaves(), 1)
        self.assertEqual(_leer_json(self.archivo_cache)["formato"], FORMATO_LLAVES)

    def test_fr013_mismo_resultado_con_cache_y_sin_ella(self):
        """FR-013: el resultado es el mismo con caché y sin ella."""
        sin_cache, _ = self._gestor()
        primero = _como_tuplas(sin_cache.obtener_llaves(self.cripta.id_cripta))
        con_cache, fuente = self._gestor()
        segundo = _como_tuplas(con_cache.obtener_llaves(self.cripta.id_cripta))
        self.assertEqual(fuente.pedidas_de_llaves(), 0)
        self.assertEqual(primero, segundo)
        self.assertEqual(primero, _como_tuplas(self.cripta.ubicaciones()))


if __name__ == "__main__":
    unittest.main()
