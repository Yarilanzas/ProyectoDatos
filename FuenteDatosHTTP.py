import uuid
import requests


class FuenteDatosHTTP:

    def __init__(self):
        self.base_url = "https://cripta-api.kad06a0zhgs84.us-east-2.cs.amazonlightsail.com/v1"
        self.client_id = str(uuid.uuid4())
        self.headers = {"X-Cripta-Client-Id": self.client_id}

    def list_criptas(self):
     respuesta = requests.get(
        f"{self.base_url}/criptas",headers=self.headers,timeout=10)
     print(respuesta.status_code)
     return respuesta.json()

    def get_crypt_details(self, id):
        respuesta = requests.get(
            f"{self.base_url}/criptas/{id}", headers=self.headers, timeout=10)
        print(respuesta.status_code)
        return respuesta.json()

    def get_cripta_skeleton(self, id):
        respuesta = requests.get(
            f"{self.base_url}criptas/{id}/salas", headers=self.headers, timeout=10)
        print(respuesta.status_code)
        return respuesta.json()

    def get_room_content(self, crypt_id, room_ids):
        respuesta = requests.get(
            f"{self.base_url}GET /criptas/{id}/contenido", headers=self.headers, timeout=10)
        print(respuesta.status_code)
        return respuesta.json()

    def get_catalog_entries(self, entry_ids):
        respuesta = requests.get(
            f"{self.base_url}GET /catalogo", headers=self.headers, timeout=10)
        print(respuesta.status_code)
        return respuesta.json()
    #faltan metodos!!
#if __name__ == "__main__":
   # print (listarCriptas())