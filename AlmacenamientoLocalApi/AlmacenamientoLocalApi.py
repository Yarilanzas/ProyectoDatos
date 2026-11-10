import sys
import os
import json

# Provicional para probar
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

#  importaciones
from DTOS.ContenidoSala import ContenidoSala
from DTOS.FichaCatalogo import FichaCatalogo
from DTOS.SalaEsqueleto import SalaEsqueleto
from DTOS.UbicacionLlave import UbicacionLlave

# Formato de la caché de llaves (Principio VI). Son constantes del formato, no datos de cripta.
FORMATO_LLAVES = "CRIPTA-LLAVES"
VERSION_FORMATO_LLAVES = 1



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
        contenido = {"version": version, "entidades": [e.a_json() for e in entidades]}

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
        return [FichaCatalogo.desde_json(e) for e in contenido["entidades"]]

    def guardar_esqueleto(self, id_cripta, version, esqueleto):
        ruta = os.path.join(self.ruta_base, f"esqueleto_{id_cripta}.json")

        # Convierte la lista de objetos sala esqueleto a diccionarios de Python

        contenido = {"version": version, "esqueleto": [s.a_json() for s in esqueleto]}


        os.makedirs(self.ruta_base, exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(contenido, f, indent=4, ensure_ascii=False)

    def cargar_esqueleto(self, id_cripta, version_esperada):
        ruta = os.path.join(self.ruta_base, f"esqueleto_{id_cripta}.json")
        if not os.path.exists(ruta):
            return None

        with open(ruta, "r", encoding="utf-8") as f:
            contenido = json.load(f)

        if contenido.get("version") != version_esperada:
            return None  # si lla a version cambió se descarta el cache en local

        # Reconstruye los objetos de sala esqueleto originales usando desde_json
        return [SalaEsqueleto.desde_json(s) for s in contenido["esqueleto"]]

    def guardar_contenido(self, id_cripta, version, contenido):
        ruta = os.path.join(self.ruta_base, f"contenido_{id_cripta}.json")
        datos = {"version": version, "contenido": [c.a_json() for c in contenido]}
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
        return [ContenidoSala.desde_json(c) for c in datos["contenido"]]

    # Ubicación de las llaves (spec 002, FR-013, FR-026). A diferencia de las demás cachés, lleva
    # identificador y versión de formato (Principio VI): si no coinciden, se descarta y se vuelve a pedir.
    def _ruta_llaves(self, id_cripta):
        return os.path.join(self.ruta_base, f"llaves_{id_cripta}.json")

    def guardar_llaves(self, id_cripta, version, ubicaciones):
        contenido = {
            "formato": FORMATO_LLAVES,
            "version_formato": VERSION_FORMATO_LLAVES,
            "version": version,
            # UbicacionLlave no tiene a_json (el DTO no se modifica): mismo esquema que /criptas/<id>/llaves
            "llaves": [{"id": u.id_llave, "sala": u.sala, "enemigo": u.enemigo} for u in ubicaciones],
        }
        os.makedirs(self.ruta_base, exist_ok=True)
        with open(self._ruta_llaves(id_cripta), "w", encoding="utf-8") as f:
            json.dump(contenido, f, indent=4, ensure_ascii=False)

    def cargar_llaves(self, id_cripta, version_esperada):
        # None = no hay caché válida: falta, no se puede leer, otro formato u otra versión de la cripta
        ruta = self._ruta_llaves(id_cripta)
        if not os.path.exists(ruta):
            return None
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = json.load(f)
            if (contenido.get("formato") != FORMATO_LLAVES
                    or contenido.get("version_formato") != VERSION_FORMATO_LLAVES
                    or contenido.get("version") != version_esperada):
                return None
            return [UbicacionLlave.desde_json(llave) for llave in contenido["llaves"]]
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None


'''if __name__ == "__main__":
    almacen = AlmacenamientoLocalApi("datos_prueba")
    almacen.guardar_catalogo("cat-v1", [{"id": "itm_antorcha", "clase": "antorcha"}])
    print(almacen.cargar_catalogo("cat-v1"))
    print(almacen.cargar_catalogo("cat-v2"))'''