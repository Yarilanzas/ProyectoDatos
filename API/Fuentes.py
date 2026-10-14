import json
import os
import uuid
import requests
import time
#solo era para probar si funcionaba bien las llammadas al api, con el main ya no se necesita
#import sys
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from DTOS.ContenidoSala import ContenidoSala
from DTOS.CriptaResumen import CriptaResumen
from DTOS.CriptaDetalles import CriptaDetalles
from DTOS.FichaCatalogo import FichaCatalogo
from DTOS.SalaEsqueleto import SalaEsqueleto


class FuenteDatos:

    def _obtener(self, ruta, params=None):
        raise NotImplementedError

    def list_criptas(self):
        datos = self._obtener("/criptas")
        return [CriptaResumen.desde_json(cripta) for cripta in datos["criptas"]]

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
        while True:
            if (self.presupuesto_solicitudes is not None
                    and self.solicitudes_realizadas >= self.presupuesto_solicitudes):
                raise RuntimeError(
                    f"Se agotó el presupuesto de solicitudes ({self.presupuesto_solicitudes}) "
                    f"al consultar {url}"
                )

            self.solicitudes_realizadas += 1
            try:
                respuesta = requests.get(url, headers=self.headers, params=params, timeout=10)
            except requests.exceptions.Timeout as e:
                raise RuntimeError(f"El servidor tardó demasiado en responder al consultar {url}") from e
            except requests.exceptions.ConnectionError as e:
                raise RuntimeError(f"No hay conexión al consultar {url}") from e

            if respuesta.status_code == 429:
                cuerpo = respuesta.json()
                tiempo_espera = cuerpo["reintentar_en"]
                time.sleep(tiempo_espera)
                continue  # antes era "return self._hacer_solicitud(...)" (recursivo); ahora reintenta
                          # dentro del mismo while, respetando el chequeo de presupuesto de arriba
            if respuesta.status_code != 200:
                raise RuntimeError(f"Error al consultar {url}: código {respuesta.status_code}")
            return respuesta.json()

    def _obtener(self, ruta, params=None):
        return self._hacer_solicitud(self.base_url + ruta, params)


class FuenteDatosOffline(FuenteDatos): #(FuenteDatos) es herencia
    def _init_(self, carpeta_paquete): #para construirse ocupa una ruta
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