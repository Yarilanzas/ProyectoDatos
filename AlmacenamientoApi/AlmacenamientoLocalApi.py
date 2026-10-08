import json
import os


class AlmacenamientoLocalApi:
    def __init__(self, ruta_base):
        self.ruta_base = ruta_base
        os.makedirs(self.ruta_base, exist_ok=True)
        '''  os.makedirs(self.ruta_base, exist_ok=True) crea una carpeta y si la 
        carpeta ya existe no pasa nada (exist_ok=True) 
        
        '''

    #Guarda en disco
    #with: el archivo se cierra solito
    def guardar_catalogo(self, version, entidades):
        ruta = os.path.join(self.ruta_base, "catalogo.json") #une la ruta
        contenido = {"version": version, "entidades": entidades}
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(contenido, f, indent=4, ensure_ascii=False)
        #.dump lo convierte a json

    def cargar_catalogo(self, version_actual):
        ruta = os.path.join(self.ruta_base, "catalogo.json")
        if not os.path.exists(ruta):
            return None #si no existe retorna none para hacer saber que tiene que llamarlo desde la red
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = json.load(f) #lee el archivo y o convierte
        if contenido["version"] != version_actual:
            return None
        '''Si la versión del archivo no coincide con la versión
         actual entregada por el servidor, la caché 
         ya no funciona porque estaria entregando
         datos guardados de una version que no es la misma 
         por lo que retorna None para forzar la 
         actualización desde la API HTTP.'''
        return contenido["entidades"]
    def guardar_esqueleto(self, id_cripta, version, esqueleto):
        ruta = os.path.join(self.ruta_base, f"esqueleto_{id_cripta}.json")
        contenido = {"version": version, "esqueleto": esqueleto}
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(contenido, f, indent=4, ensure_ascii=False)

    def cargar_esqueleto(self, id_cripta, version_actual):
        ruta = os.path.join(self.ruta_base, f"esqueleto_{id_cripta}.json")
        if not os.path.exists(ruta):
            return None
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = json.load(f)
        if contenido["version"] != version_actual:
            return None
        return contenido["esqueleto"]

    def guardar_contenido(self, id_cripta, version, contenido):
        ruta = os.path.join(self.ruta_base, f"contenido_{id_cripta}.json")
        datos = {"version": version, "contenido": contenido}
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)

    def cargar_contenido(self, id_cripta, version_actual):
        ruta = os.path.join(self.ruta_base, f"contenido_{id_cripta}.json")
        if not os.path.exists(ruta):
            return None
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if datos["version"] != version_actual:
            return None
        return datos["contenido"]
'''if __name__ == "__main__":
    almacen = AlmacenamientoLocalApi("datos_prueba")
    almacen.guardar_catalogo("cat-v1", [{"id": "itm_antorcha", "clase": "antorcha"}])
    print(almacen.cargar_catalogo("cat-v1"))
    print(almacen.cargar_catalogo("cat-v2"))'''