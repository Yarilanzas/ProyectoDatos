import json
import os


class AlmacenamientoLocalApi:
    def __init__(self, ruta_base):
        self.ruta_base = ruta_base
        os.makedirs(self.ruta_base, exist_ok=True)

    def guardar_catalogo(self, version, entidades):
        ruta = os.path.join(self.ruta_base, "catalogo.json")
        contenido = {"version": version, "entidades": entidades}
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(contenido, f, indent=4, ensure_ascii=False)

    def cargar_catalogo(self, version_actual):
        ruta = os.path.join(self.ruta_base, "catalogo.json")
        if not os.path.exists(ruta):
            return None
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = json.load(f)
        if contenido["version"] != version_actual:
            return None
        return contenido["entidades"]

   ''' if __name__ == "__main__":
        almacen = AlmacenamientoLocalApi("datos_prueba")
        almacen.guardar_catalogo("cat-v1", [{"id": "itm_antorcha", "clase": "antorcha"}])
        print(almacen.cargar_catalogo("cat-v1"))  # debe devolver la lista
        print(almacen.cargar_catalogo("cat-v2"))  # debe devolver None'''