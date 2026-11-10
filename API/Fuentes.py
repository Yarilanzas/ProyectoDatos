import json
import os
import uuid
import requests
import time
from API import Excepciones


import logging
#solo era para probar si funcionaba bien las llammadas al api, con el main ya no se necesita
#import sys
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from DTOS.ContenidoSala import ContenidoSala
from DTOS.CriptaResumen import CriptaResumen
from DTOS.CriptaDetalles import CriptaDetalles
from DTOS.FichaCatalogo import FichaCatalogo
from DTOS.SalaEsqueleto import SalaEsqueleto
from DTOS.UbicacionLlave import UbicacionLlave

logger = logging.getLogger(__name__)


class FuenteDatos:

    def _obtener(self, ruta, params=None):
        raise NotImplementedError

    def list_criptas(self):
        datos = self._obtener("/criptas")
        return [CriptaResumen.desde_json(cripta) for cripta in datos["criptas"]]


    def obtener_llaves_cripta(self, id_cripta):
        ruta = f"/criptas/{id_cripta}/llaves"
        datos = self._obtener(ruta)
        if "llaves" not in datos:
            raise Excepciones.RespuestaInvalidaError(ruta, "falta la clave 'llaves'")
        # FR-025: una entrada incompleta es una respuesta inválida (antes salía como KeyError).
        # Una sala que no existe en el esqueleto no es error de lectura: la verificación la reporta.
        for llave in datos["llaves"]:
            if not isinstance(llave, dict) or "id" not in llave or "sala" not in llave:
                raise Excepciones.RespuestaInvalidaError(ruta, "entrada de llave sin 'id' o 'sala'")
        return [UbicacionLlave.desde_json(llave) for llave in datos["llaves"]]

    def obtener_detalles_cripta(self, id):
        datos = self._obtener(f"/criptas/{id}")
        return CriptaDetalles.desde_json(datos)

    def obtener_esqueleto_cripta(self, id_cripta):
        numero_de_pagina = 1
        params = {"pagina": numero_de_pagina}
        # llamada a la fuente (api o disco)
        datos = self._obtener(f"/criptas/{id_cripta}/salas", params)
        # guardar las salas de la pagina 1
        salas_totales = []
        salas_totales.extend(
            datos['salas'])  # extend mete a la lista que existe(extiende el tamaño de la lista ya existente )
        total_pages = datos['total_paginas']

        while numero_de_pagina < total_pages:  # paginas totales que devuelve la fuente
            numero_de_pagina += 1
            params = {"pagina": numero_de_pagina}
            datos_ciclo = self._obtener(f"/criptas/{id_cripta}/salas", params)
            salas_pagina_actual = datos_ciclo['salas']
            salas_totales.extend(salas_pagina_actual)
        return [SalaEsqueleto.desde_json(sala) for sala in salas_totales]

    def obtener_contenido_sala(self, id_cripta, ids_salas):
        tamano = 10
        bloques_ids = [ids_salas[i:i + tamano] for i in range(0, len(ids_salas), tamano)]  # parte en 10
        contenido_salas = []
        i = 0
        while i < len(bloques_ids):
            bloque_actual = bloques_ids[i]  # es una lista de listas, si es mas pequeño que 10 solo hace una lista
            ids_como_texto = ",".join(str(id_sala) for id_sala in bloque_actual)
            params = {"salas": ids_como_texto}  # adentro del ciclo porque pide en bloques de [i]

            datos = self._obtener(f"/criptas/{id_cripta}/contenido", params)
            contenido_salas.extend(datos['contenido'])  # guarda el contenido
            i += 1

        return [ContenidoSala.desde_json(sala) for sala in contenido_salas]

    def obtener_fichas_catalogo(self, ids_fichas):
        tamano = 10
        bloques_ids = [ids_fichas[i:i + tamano] for i in range(0, len(ids_fichas), tamano)]

        catalogo_entidades = []
        i = 0
        while i < len(bloques_ids):
            bloque_actual = bloques_ids[i]
            ids_como_texto = ",".join(str(id_ficha) for id_ficha in bloque_actual)
            params = {"ids": ids_como_texto}

            datos = self._obtener("/catalogo", params)
            catalogo_entidades.extend(datos['entidades'])  # guarda el contenido
            i += 1

        return [FichaCatalogo.desde_json(entidad) for entidad in catalogo_entidades]

    def obtener_version_cripta(self, id_cripta):
        datos = self._obtener(f"/criptas/{id_cripta}/version")
        return datos["version"]

    def obtener_version_catalogo(self):
        datos = self._obtener("/catalogo/version")
        return datos["version"]


class FuenteDatosHTTP(FuenteDatos): #(FuenteDatos) es herencia
    TIMEOUT = 10  # segundos maximos por solicitud
    MAX_INTENTOS = 3  # intentos totales ante timeout, sin conexion o 5xx
    ESPERA_INICIAL = 1  # segundos antes del primer reintento
    MAX_ESPERAS_429 = 5  # veces que se espera por limite de solicitudes
    ESPERA_429_POR_DEFECTO = 1  # si el 429 no trae "reintentar_en"

    def __init__(self, presupuesto_solicitudes=None):
        self.base_url = "https://cripta-api.kad06a0zhgs84.us-east-2.cs.amazonlightsail.com/v1"
        self.client_id = str(uuid.uuid4())
        self.headers = {"X-Cripta-Client-Id": self.client_id}
        self.solicitudes_realizadas = 0
        # el presupuesto se conoce recién después de pedir los datos generales de la cripta (§3.3),
        # por eso puede quedar en None al construir y setearse después con fijar_presupuesto()
        self.presupuesto_solicitudes = presupuesto_solicitudes

    def fijar_presupuesto(self, presupuesto_solicitudes):
        self.presupuesto_solicitudes = presupuesto_solicitudes

    def _hacer_solicitud(self, url, params=None):
        intentos_fallidos = 0
        esperas_429 = 0
        espera = self.ESPERA_INICIAL

        while True:
            #revision de presupuesto
            if (self.presupuesto_solicitudes is not None
                    and self.solicitudes_realizadas >= self.presupuesto_solicitudes):
                logger.error("Presupuesto agotado (%s) antes de consultar %s",
                             self.presupuesto_solicitudes, url)
                raise Excepciones.PresupuestoAgotadoError(self.presupuesto_solicitudes, url)

            self.solicitudes_realizadas += 1
            inicio = time.perf_counter()

            try:
                ms = (time.perf_counter() - inicio) * 1000

                respuesta = requests.get(
                    url, headers=self.headers, params=params, timeout=self.TIMEOUT
                )
            except requests.exceptions.Timeout as e:
                error, causa = Excepciones.TiempoAgotadoError(url, self.TIMEOUT), e
            except requests.exceptions.ConnectionError as e:
                error, causa = Excepciones.SinConexionError(url), e
            except requests.exceptions.RequestException as e:
                raise Excepciones.ErrorCliente(f"Error al consultar {url}: {e}") from e
            else:
                logger.info("GET %s params=%s -> %s (%.0f ms) [solicitud %d/%s]",
                            url, params, respuesta.status_code, ms,
                            self.solicitudes_realizadas, self.presupuesto_solicitudes)
                if respuesta.status_code == 429:
                    esperas_429 += 1
                    if esperas_429 > self.MAX_ESPERAS_429:
                        raise Excepciones.ErrorServicio(
                            url, 429, "Se superó el máximo de esperas por límite de solicitudes"
                        )
                    logger.warning("429 en %s; esperando %s s (espera %d de %d)",
                                   url, espera_429, esperas_429, self.MAX_ESPERAS_429)
                    time.sleep(self._leer_espera_429(respuesta))
                    continue

                if respuesta.status_code == 200:
                    try:
                        return respuesta.json()
                    except ValueError as e:  # JSONDecodeError hereda de ValueError
                        raise Excepciones.RespuestaInvalidaError(
                            url, "el cuerpo no es un JSON válido"
                        ) from e

                error = Excepciones.ErrorServicio(
                    url, respuesta.status_code, self._extraer_mensaje(respuesta)
                )
                causa = None

            intentos_fallidos += 1
            if not error.reintentable or intentos_fallidos >= self.MAX_INTENTOS:
                logger.error("Se abandona la solicitud a %s: %s", url, error)
                raise error from causa
            logger.warning("%s; reintento %d de %d en %s s",
                           error, intentos_fallidos, self.MAX_INTENTOS - 1, espera)
            time.sleep(espera)
            espera *= 2  # espera que se duplica con fallidos

    def _leer_espera_429(self, respuesta):
        try:
            espera = float(
                respuesta.json().get("reintentar_en", self.ESPERA_429_POR_DEFECTO)
            )
        except (ValueError, TypeError, AttributeError):
            espera = self.ESPERA_429_POR_DEFECTO
        return max(0, espera)

    def _obtener(self, ruta, params=None):
        return self._hacer_solicitud(self.base_url + ruta, params)
    @staticmethod
    def _extraer_mensaje(respuesta):
        try:
            return respuesta.json().get("error")
        except (ValueError, AttributeError):
            return None


class FuenteDatosOffline(FuenteDatos): #(FuenteDatos) es herencia
    def __init__(self, carpeta_paquete): #para construirse ocupa una ruta
        self.carpeta_paquete = carpeta_paquete
        # mismo contador que la fuente HTTP, asi GestorDatos.resumen_red() funciona en ambos modos
        self.solicitudes_realizadas = 0

    def _obtener(self, ruta, params=None):
        self.solicitudes_realizadas += 1
        #Es una ruta que todavia no existe hay de e
        archivo = os.path.join(self.carpeta_paquete, ruta.strip("/") + ".json")
        if not os.path.exists(archivo):
            raise RuntimeError(f"Falta el archivo para {ruta}: {archivo}")
        with open(archivo, "r", encoding="utf-8") as f:
            return json.load(f)

