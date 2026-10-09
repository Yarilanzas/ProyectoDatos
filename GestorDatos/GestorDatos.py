from enum import nonmember

from API.FuenteDatosHTTP import FuenteDatosHTTP
from AlmacenamientoLocalApi.AlmacenamientoLocalApi import AlmacenamientoLocalApi
from Cache.CacheCatalogo import CacheCatalogo


class GestorDatos:
    _instancia = None  # única instancia

    def __new__(cls, *args, **kwargs):
        #crea la instancia si no existe
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
            cls._instancia._inicializado = False
        return cls._instancia

    def __init__(self, ruta_base="datos_locales", cache_size=25):
        if self._inicializado:
            return

        self.fuente_http = FuenteDatosHTTP()
        self.almacenamiento_disco = AlmacenamientoLocalApi(ruta_base)
        self.cache_catalogo = CacheCatalogo(cache_size)

        self._inicializado = True

    def obtener_ficha(self, id_ficha):
        if self.cache_catalogo.esta_en_cache(id_ficha):
            return self.cache_catalogo.obtener(id_ficha)

        version_actual = self.fuente_http.obtener_version_catalogo()
        entidades_disco = self.almacenamiento_disco.cargar_catalogo(version_actual)

        if entidades_disco is not None:
            for ficha in entidades_disco:
                if ficha.id == id_ficha:
                    self.cache_catalogo.agregar(ficha, self)
                    return ficha

        fichas_red = self.fuente_http.obtener_fichas_catalogo([id_ficha])
        if fichas_red:
            ficha = fichas_red[0]
            self.cache_catalogo.agregar(ficha, self)
            self.almacenamiento_disco.guardar_catalogo(version_actual, ...)
            return ficha

        return None

    def obtener_esqueleto(self, id_cripta):
       id= self.fuente_http.obtener_version_catalogo()
       datos= self.almacenamiento_disco.cargar_catalogo(id)
       if datos is not None:
           return datos