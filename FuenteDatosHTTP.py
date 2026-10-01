import uuid
import requests


class FuenteDatosHTTP:
    def __init__(self):
        self.base_url = "https://cripta-api.kad06a0zhgs84.us-east-2.cs.amazonlightsail.com/v1"
        self.client_id = str(uuid.uuid4())
        self.headers = {"X-Cripta-Client-Id": self.client_id}
        print("Hola", self.client_id)

    def list_criptas(self):
     respuesta = requests.get(
        f"{self.base_url}/criptas",headers=self.headers,timeout=10)
     #print(respuesta.status_code)
     return respuesta.json()

    def obtener_detalles_cripta(self, id):
        respuesta = requests.get(
            f"{self.base_url}/criptas/{id}", headers=self.headers, timeout=10)
        #print(respuesta.status_code)
        return respuesta.json()

    def obtener_esqueleto_cripta(self, id_cripta):
        numero_de_pagina = 1
        params = {"pagina": numero_de_pagina}
        # llamada a la api
        respuesta = requests.get(
            f"{self.base_url}/criptas/{id_cripta}/salas",
            headers=self.headers,
            params=params,  # parametro que se manda al parametro requerido pagina,
            timeout=10
        )
        # guardar las salas de la pagina 1
        salas_totales = []
        salas_totales.extend(respuesta.json()['salas'])

        total_pages = respuesta.json()['total_paginas']

        while numero_de_pagina < respuesta.json()['total_paginas']: #paginas totales que devuelve la api
            numero_de_pagina += 1
            params = {"pagina": numero_de_pagina}
            respuesta_ciclo = requests.get(
                f"{self.base_url}/criptas/{id_cripta}/salas",
                headers=self.headers,
                params=params,
                timeout=10
            )
            salas_pagina_actual = respuesta_ciclo.json()['salas']
            salas_totales.extend(salas_pagina_actual)
        print(salas_totales)
        return salas_totales

    def obtener_contenido_sala(self, id_cripta, ids_salas):
        tamano = 10
        bloques_ids = [ids_salas[i:i + tamano] for i in range(0, len(ids_salas), tamano)]#parte en 10

        contenido_salas = []
        i = 0
        while i < len(bloques_ids):
            bloque_actual = bloques_ids[i] #es una lista de listas, si es mas peuqeño que 10 solo hace una lista
            ids_como_texto = ",".join(str(id_sala) for id_sala in bloque_actual)
            params = {"salas": ids_como_texto}# adentro del cciclo porque pide en bloques de [i]

            respuesta = requests.get(
                f"{self.base_url}/criptas/{id_cripta}/contenido",
                headers=self.headers,
                params=params,
                timeout=10
            )
            contenido_salas.extend(respuesta.json()['contenido']) #guarda el contenido
            i += 1

        return contenido_salas

    def obtener_fichas_catalogo(self, ids_fichas):
        respuesta = requests.get(
            f"{self.base_url}/GET /catalogo", headers=self.headers, timeout=10)
        print(respuesta.status_code)
        return respuesta.json()


    def obtener_version_cripta(self, id_cripta):
        respuesta = requests.get(
            f"{self.base_url}/GET /criptas/{id}/version", headers=self.headers, timeout=10)
        print(respuesta.status_code)
        return respuesta.json()

    def obtener_version_catalogo(self):
        respuesta = requests.get(
            f"{self.base_url}/GET /catalogo/version", headers=self.headers, timeout=10)
        print(respuesta.status_code)
        return respuesta.json()

if __name__ == "__main__":
    fuente = FuenteDatosHTTP()
    print (fuente.list_criptas())
    print (fuente.obtener_detalles_cripta("cripta-01"))
    print (fuente.obtener_esqueleto_cripta("cripta-01"))
    print( fuente.obtener_contenido_sala("cripta-01", [1,2,3,4]))