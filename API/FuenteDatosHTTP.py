import uuid
import requests
import time

from DTOS.ContenidoSala import ContenidoSala
from DTOS.CriptaResumen import CriptaResumen
from DTOS.CriptaDetalles import CriptaDetalles
from DTOS.FichaCatalogo import FichaCatalogo
from DTOS.SalaEsqueleto import SalaEsqueleto



class FuenteDatosHTTP:

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

    def list_criptas(self):
        datos = self._hacer_solicitud(f"{self.base_url}/criptas")
        return [CriptaResumen.desde_json(cripta) for cripta in datos["criptas"]]

    def obtener_detalles_cripta(self, id):
        datos= self._hacer_solicitud(f"{self.base_url}/criptas/{id}")
        return CriptaDetalles.desde_json(datos)

    def obtener_esqueleto_cripta(self, id_cripta):
        numero_de_pagina = 1
        params = {"pagina": numero_de_pagina}
        # llamada a la api
        datos = self._hacer_solicitud(f"{self.base_url}/criptas/{id_cripta}/salas", params)
        # guardar las salas de la pagina 1
        salas_totales = []
        salas_totales.extend(datos['salas']) #extend mete a la lista que existe(extiende el tamaño de la lista ya existente )
        total_pages = datos['total_paginas']

        while numero_de_pagina < total_pages: #paginas totales que devuelve la api
            numero_de_pagina += 1
            params = {"pagina": numero_de_pagina}
            datos_ciclo = self._hacer_solicitud(f"{self.base_url}/criptas/{id_cripta}/salas", params)
            salas_pagina_actual = datos_ciclo['salas']
            salas_totales.extend(salas_pagina_actual)
       #print(salas_totales)
        return [SalaEsqueleto.desde_json(sala) for sala in salas_totales]

    def obtener_contenido_sala(self, id_cripta, ids_salas):
        tamano = 10
        bloques_ids = [ids_salas[i:i + tamano] for i in range(0, len(ids_salas), tamano)]#parte en 10
        contenido_salas = []
        i = 0
        while i < len(bloques_ids):
            bloque_actual = bloques_ids[i] #es una lista de listas, si es mas peuqeño que 10 solo hace una lista
            ids_como_texto = ",".join(str(id_sala) for id_sala in bloque_actual)
            params = {"salas": ids_como_texto}# adentro del cciclo porque pide en bloques de [i]

            datos = self._hacer_solicitud(f"{self.base_url}/criptas/{id_cripta}/contenido", params)
            contenido_salas.extend(datos['contenido']) #guarda el contenido
            i += 1

        return [ContenidoSala.desde_json(sala) for sala in contenido_salas]

    def obtener_fichas_catalogo(self, ids_fichas):
        tamano = 10
        bloques_ids = [ids_fichas[i:i + tamano] for i in range(0, len(ids_fichas), tamano)]  # parte en 10

        catalogo_entidades = []
        i = 0
        while i < len(bloques_ids):
            bloque_actual = bloques_ids[i]
            ids_como_texto = ",".join(str(id_sala) for id_sala in bloque_actual)
            params = {"ids": ids_como_texto}

            datos = self._hacer_solicitud(f"{self.base_url}/catalogo", params)
            catalogo_entidades.extend(datos['entidades'])  # guarda el contenido
            i += 1

        return [FichaCatalogo.desde_json(entidad) for entidad in catalogo_entidades]

    def obtener_version_cripta(self, id_cripta):
        datos = self._hacer_solicitud(f"{self.base_url}/criptas/{id_cripta}/version")
        return datos["version"]

    def obtener_version_catalogo(self):
        datos = self._hacer_solicitud(f"{self.base_url}/catalogo/version")
        return datos["version"]

'''if __name__ == "__main__":
    fuente = FuenteDatosHTTP()

    # 1. Listar criptas disponibles
    print(" 1. Listar criptas disponibles")
    criptas = fuente.list_criptas()
    print(f"Criptas disponibles: {len(criptas)}")
    for cripta in criptas:
        print(f"  - {cripta.id}: {cripta.nombre} ({cripta.salas} salas, dificultad {cripta.dificultad})")

    # 2. Datos generales de una cripta
    print("2. Datos generales de una cripta")
    detalles = fuente.obtener_detalles_cripta("cripta-01")
    print(f"\nDatos generales de {detalles.id}:")
    print(f"  Sala inicial: {detalles.sala_inicial}, sala de salida: {detalles.sala_salida}")
    print(f"  Jugador - vida_max: {detalles.jugador.vida}, ataque: {detalles.jugador.ataque}")

    # 3. Esqueleto completo
    print("3. Esqueleto completo")
    esqueleto = fuente.obtener_esqueleto_cripta("cripta-01")
    print(f"\nEsqueleto: {len(esqueleto)} salas")
    primera_sala = esqueleto[0]
    print(f"  Sala {primera_sala.id} ({primera_sala.nombre}) tiene salidas: {list(primera_sala.salidas.keys())}")

    # 4. Contenido de las primeras salas
    print("4. Contenido de las primeras salas")
    contenido = fuente.obtener_contenido_sala("cripta-01", [1, 2, 3, 4])
    print(f"\nContenido de {len(contenido)} salas:")
    tipos_encontrados = set()
    for sala_contenido in contenido:
        print(f"  Sala {sala_contenido.id_sala}: {len(sala_contenido.enemigos)} enemigos, {len(sala_contenido.objetos)} objetos")
        for enemigo in sala_contenido.enemigos:
            tipos_encontrados.add(enemigo.tipo)

    # 5. Fichas de catálogo de los tipos de enemigo encontrados
    print("5. Fichas de catálogo de los tipos de enemigo encontrados")
    if tipos_encontrados:
        fichas = fuente.obtener_fichas_catalogo(list(tipos_encontrados))
        print(f"\nFichas de catálogo: {len(fichas)}")
        for ficha in fichas:
            print(f"  {ficha.id} ({ficha.clase}): {ficha.nombre}")

    # 6. Versiones
    print("6. Versiones")
    print(f"\nVersión de cripta: {fuente.obtener_version_cripta('cripta-01')}")
    print(f"Versión de catálogo: {fuente.obtener_version_catalogo()}")'''