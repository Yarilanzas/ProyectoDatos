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