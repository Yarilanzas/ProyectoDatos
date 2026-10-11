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
        bloques_ids = [ids_fichas[i:i + tamano] for i in range(0, len(ids_fichas), tamano)]  # parte en 10

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
    def __init__(self):
        self.base_url = "https://cripta-api.kad06a0zhgs84.us-east-2.cs.amazonlightsail.com/v1"
        self.client_id = str(uuid.uuid4())
        self.headers = {"X-Cripta-Client-Id": self.client_id}

    def _hacer_solicitud(self, url, params=None):
        try:
            respuesta = requests.get(url, headers=self.headers, params=params, timeout=10)
            if respuesta.status_code == 429:
                cuerpo = respuesta.json()
                tiempo_espera = cuerpo["reintentar_en"]
                time.sleep(tiempo_espera)
                return self._hacer_solicitud(url, params)
            if respuesta.status_code != 200:
                raise RuntimeError(f"Error al consultar {url}: código {respuesta.status_code}")
            return respuesta.json()
        except requests.exceptions.Timeout as e:
            raise RuntimeError(f"El servidor tardó demasiado en responder al consultar {url}") from e
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(f"No hay conexión al consultar {url}") from e

    def _obtener(self, ruta, params=None):
        return self._hacer_solicitud(self.base_url + ruta, params)


class FuenteDatosOffline(FuenteDatos): #(FuenteDatos) es herencia
    def __init__(self, carpeta_paquete): #para construirse ocupa una ruta
        self.carpeta_paquete = carpeta_paquete

    def _obtener(self, ruta, params=None):
        #Es una ruta que todavia no existe hay de e
        archivo = os.path.join(self.carpeta_paquete, ruta.strip("/") + ".json")
        if not os.path.exists(archivo):
            raise RuntimeError(f"Falta el archivo para {ruta}: {archivo}")
        with open(archivo, "r", encoding="utf-8") as f:
            return json.load(f)


'''if __name__ == "__main__":
    fuente = FuenteDatosHTTP()

    criptas = fuente.list_criptas()
    print("Criptas:", len(criptas))

    detalles = fuente.obtener_detalles_cripta("cripta-01")
    print("Sala inicial:", detalles.sala_inicial, "| vida jugador:", detalles.jugador.vida)

    esqueleto = fuente.obtener_esqueleto_cripta("cripta-01")
    print("Salas en el esqueleto:", len(esqueleto))

    contenido = fuente.obtener_contenido_sala("cripta-01", [1, 2, 3, 4])
    print("Contenido de", len(contenido), "salas")

    tipos = set()
    for sala in contenido:
        for enemigo in sala.enemigos:
            tipos.add(enemigo.tipo)
    if tipos:
        fichas = fuente.obtener_fichas_catalogo(list(tipos))
        print("Fichas de catálogo:", [f.id for f in fichas])

    print("Versión cripta:", fuente.obtener_version_cripta("cripta-01"))
    print("Versión catálogo:", fuente.obtener_version_catalogo())'''