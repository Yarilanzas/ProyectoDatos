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

    def __init__(self, ruta_base="datos_locales", cache_size=25, ):
        if self._inicializado:
            return

        self.fuente_http = FuenteDatosHTTP()
        self.almacenamiento_disco = AlmacenamientoLocalApi(ruta_base)
        self.cache_catalogo = CacheCatalogo(cache_size)
        self.estado_juego= None

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
        version_actual = self.fuente_http.obtener_version_cripta(id_cripta)
        datos_disco = self.almacenamiento_disco.cargar_esqueleto(id_cripta, version_actual)

        if datos_disco is not None:
            return datos_disco  # si el esqueleto ya esta guardado en disco lo retorna e lugar de ir a la api de una


        datos_red = self.fuente_http.obtener_esqueleto_cripta(id_cripta) #si no estaba guardada entonces va a la API

        #guarda en disco el esqueleto que no estaba guardado antes
        self.almacenamiento_disco.guardar_esqueleto(id_cripta, version_actual, datos_red)

        # devuelve los datos cargados que se acaba de traer desde la api
        return datos_red

    def obtener_contenido_salas(self, id_cripta, ids_salas):
        version_actual = self.fuente_http.obtener_version_cripta(id_cripta)

        contenido_disco = self.almacenamiento_disco.cargar_contenido(id_cripta, version_actual)

        if contenido_disco is not None:
            ids_en_disco = [] #para guardar los ids de las salas que estaban guardadas en disco
            for sala in contenido_disco:
                ids_en_disco.append(sala.id_sala)  #por cada sala extrae y mete el id

            todas_estan = True
            for id_buscado in ids_salas: #por cada id que entra por solicitud(ids_salas)
                if id_buscado not in ids_en_disco: #con una que no este ya no cumple con todas las que se pide
                    todas_estan = False
                    break

            if todas_estan: #si pasa la condicion retorna todas las salas que se pidio
                salas_encontradas = []
                for sala in contenido_disco:
                    if sala.id_sala in ids_salas:
                        salas_encontradas.append(sala)
                return salas_encontradas

        #si no esta guardado en el disco va a la api y lo pide
        contenido_red = self.fuente_http.obtener_contenido_sala(id_cripta, ids_salas)
        #y lo guarda
        self.almacenamiento_disco.guardar_contenido(id_cripta, version_actual, contenido_red)
        return contenido_red

    def conectar_estado_juego(self, estado):

       #estado= objeto que tiene todo lo que esta vivo, entidades, salas, etc.
        self.estado_juego = estado


''' VERIFICAR ESTO CON MARI!!!!!!!!!!!!!!::
    def esta_en_uso(self, id_ficha):
        if self.estado_juego is None:
            return False # si no hay nada en el juego retorna falso
        # Si el juego define un método específico para consultar fichas activas:

        #hasattr funcion de python que verifica si una clase tiene un atributo especifico
        if hasattr(self.estado_juego, "es_ficha_activa"):

            return self.estado_juego.es_ficha_activa(id_ficha) #verifica que la ficha este activa en la clase juego

        # Alternativa de respaldo por si tu equipo expone una lista 'fichas_activas':
        if hasattr(self.estado_juego, "fichas_activas"):
            return id_ficha in self.estado_juego.fichas_activas

        return False
'''
