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

    def get_crypt_details(self, id):
        respuesta = requests.get(
            f"{self.base_url}/criptas/{id}", headers=self.headers, timeout=10)
        #print(respuesta.status_code)
        return respuesta.json()

    def get_cripta_skeleton(self, id):
        numero_de_pagina=1
        params = {"pagina": numero_de_pagina}
        #llamada a la api
        respuesta = requests.get(
            f"{self.base_url}/criptas/{id}/salas",
            headers=self.headers,
            params=params,#parametro que se manda al parametro requerido pagina,
            timeout=10
        )
        #guardar las salas de la pagina 1
        salas_totales = []
        salas_pagina_actual = respuesta.json()['salas']
        salas_totales.extend(salas_pagina_actual)
        total_pages= respuesta.json()['total_paginas']

        while numero_de_pagina < total_pages:
            numero_de_pagina += 1
            params = {"pagina": numero_de_pagina}
            respuestaCiclo = requests.get(
                f"{self.base_url}/criptas/{id}/salas",
                headers=self.headers,
                params=params,
                timeout=10
            )
            salas_pagina_actual = respuestaCiclo.json()['salas']
            salas_totales.extend(salas_pagina_actual)


        print(salas_totales)
        return salas_totales

    def get_room_content(self, crypt_id, room_ids):
        respuesta = requests.get(
            f"{self.base_url}/GET /criptas/{id}/contenido", headers=self.headers, timeout=10)
        print(respuesta.status_code)
        return respuesta.json()

    def get_catalog_entries(self, entry_ids):
        respuesta = requests.get(
            f"{self.base_url}/GET /catalogo", headers=self.headers, timeout=10)
        print(respuesta.status_code)
        return respuesta.json()


    def get_crypt_version(self, crypt_id):
        respuesta = requests.get(
            f"{self.base_url}/GET /criptas/{id}/version", headers=self.headers, timeout=10)
        print(respuesta.status_code)
        return respuesta.json()
    def get_catalog_version(self):
        respuesta = requests.get(
            f"{self.base_url}/GET /catalogo/version", headers=self.headers, timeout=10)
        print(respuesta.status_code)
        return respuesta.json()

if __name__ == "__main__":
    fuente = FuenteDatosHTTP()
    print (fuente.list_criptas())
    print (fuente.get_crypt_details("cripta-01"))
    print (fuente.get_cripta_skeleton("cripta-01"))
