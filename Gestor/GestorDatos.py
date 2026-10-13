import os
import sys

#Provicional para no cambiar la root del proyecto
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
#--------------------

#importaciones normales:
from Gestor.PlanificadorPreCarga import PlanificadorPrecarga
from Cache.CacheCatalogo import CacheCatalogo
from AlmacenamientoLocalApi.AlmacenamientoLocalApi import AlmacenamientoLocalApi
class GestorDatos:
    _instancia = None  # única instancia

    def __new__(cls, *args, **kwargs):
        #crea la instancia si no existe
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
            cls._instancia._inicializado = False
        return cls._instancia

    def __init__(self, fuente, ruta_base="datos_locales", cache_size=25):
        if self._inicializado:
            return

        self.fuente = fuente  # llega ya construida (HTTP o offline), se decide main.py
        self.almacenamiento_disco = AlmacenamientoLocalApi(ruta_base)
        self.cache_catalogo = CacheCatalogo(cache_size)
        self.estado_juego = None

        # versiones se consultan una sola vez y se recuerdan en memoria
        self._version_catalogo = None
        self._id_cripta_version = None
        self._version_cripta = None

        # contadores
        self.aciertos_cache = 0
        self.fallos_cache = 0

        self._inicializado = True

    def _version_del_catalogo(self):
        if self._version_catalogo is None: # si no hay una guardada
            self._version_catalogo = self.fuente.obtener_version_catalogo()
        return self._version_catalogo

    def _version_de_cripta(self, id_cripta):
        if self._id_cripta_version != id_cripta:
            self._version_cripta = self.fuente.obtener_version_cripta(id_cripta)
            self._id_cripta_version = id_cripta
        return self._version_cripta



    def solicitudes_realizadas(self):
        return self.fuente.solicitudes_realizadas

    def obtener_ficha(self, id_ficha):
        #primero se verifica si esta en cache
        if self.cache_catalogo.esta_en_cache(id_ficha):
            self.aciertos_cache += 1
            return self.cache_catalogo.obtener(id_ficha)
        self.fallos_cache += 1

        #si no esta en cache la busca en disco
        version_actual = self._version_del_catalogo()
        entidades_disco = self.almacenamiento_disco.cargar_catalogo(version_actual)

        if entidades_disco is not None:
            for ficha in entidades_disco:
                if ficha.id == id_ficha:
                    self.cache_catalogo.agregar(ficha, self)
                    return ficha


        #si del todo no esta en disco no en cache se manda a llamar a la api o datos offline para buscarla
        fichas_red = self.fuente.obtener_fichas_catalogo([id_ficha])
        if fichas_red:
            ficha = fichas_red[0]
            self.cache_catalogo.agregar(ficha, self)

            # se guarda lo que ya había en disco mas la ficha nueva
            fichas_a_guardar = []
            if entidades_disco is not None:
                fichas_a_guardar.extend(entidades_disco)
            fichas_a_guardar.append(ficha)
            self.almacenamiento_disco.guardar_catalogo(version_actual, fichas_a_guardar)
            return ficha

        return None

    def obtener_esqueleto(self, id_cripta):
        version_actual = self._version_de_cripta(id_cripta)
        datos_disco = self.almacenamiento_disco.cargar_esqueleto(id_cripta, version_actual)

        if datos_disco is not None:
            return datos_disco  # si el esqueleto ya esta guardado en disco lo retorna en lugar de ir a la fuente

        datos_red = self.fuente.obtener_esqueleto_cripta(id_cripta)  # si no estaba guardado va a la fuente

        #guarda en disco el esqueleto que no estaba guardado antes
        self.almacenamiento_disco.guardar_esqueleto(id_cripta, version_actual, datos_red)

        return datos_red

    def obtener_contenido_salas(self, id_cripta, ids_salas):
        version_actual = self._version_de_cripta(id_cripta)

        contenido_disco = self.almacenamiento_disco.cargar_contenido(id_cripta, version_actual)
        ya_guardado = contenido_disco if contenido_disco is not None else []

        ids_en_disco = []  #para guardar los ids de las salas que estaban guardadas en disco
        for sala in ya_guardado:
            ids_en_disco.append(sala.id_sala)

        # solo se pide a la fuente lo que no estaba en disco
        faltantes = []
        for id_buscado in ids_salas:
            if id_buscado not in ids_en_disco:
                faltantes.append(id_buscado)

        todo = ya_guardado
        if faltantes:
            nuevas = self.fuente.obtener_contenido_sala(id_cripta, faltantes)
            todo = ya_guardado + nuevas
            # se guarda lo anterior mas lo nuevo para no perder nada
            self.almacenamiento_disco.guardar_contenido(id_cripta, version_actual, todo)

        salas_encontradas = []
        for sala in todo:
            if sala.id_sala in ids_salas:
                salas_encontradas.append(sala)
        return salas_encontradas

    def conectar_estado_juego(self, estado):
       #estado= objeto que tiene todo lo que esta vivo, entidades, salas,
        self.estado_juego = estado

    def esta_en_uso(self, id_ficha):
        if self.estado_juego is None:
            return False # si no hay nada en el juego retorna falso
        if hasattr(self.estado_juego, "es_ficha_activa"):
            return self.estado_juego.es_ficha_activa(id_ficha)
        if hasattr(self.estado_juego, "fichas_activas"):
            return id_ficha in self.estado_juego.fichas_activas
        return False

    def iniciar_cripta(self, id_cripta):
        esqueleto = self.obtener_esqueleto(id_cripta)
        self._planificador = PlanificadorPrecarga(esqueleto)
        self._id_cripta_actual = id_cripta
        self._salas_cargadas = []
        self._contenido_en_memoria = []
        return esqueleto

    def _cargar_lote(self, ids_salas):
        contenido = self.obtener_contenido_salas(self._id_cripta_actual, ids_salas)
        for sala in contenido:
            self._contenido_en_memoria.append(sala)
            self._salas_cargadas.append(sala.id_sala)

    def asegurar_sala(self, id_sala):
        if id_sala not in self._salas_cargadas:
            lote = self._planificador.planificar(id_sala, self._salas_cargadas)
            self._cargar_lote(lote)
        for sala in self._contenido_en_memoria:
            if sala.id_sala == id_sala:
                return sala
        return None

    def precargar(self, id_sala):
        lote = self._planificador.planificar(id_sala, self._salas_cargadas)
        if lote:
            self._cargar_lote(lote)

from API.Fuentes import FuenteDatosHTTP
from Gestor.GestorDatos import GestorDatos

if __name__ == "__main__":
    fuente = FuenteDatosHTTP()
    gestor = GestorDatos(fuente, ruta_base="datos_prueba", cache_size=25)

    esqueleto = gestor.iniciar_cripta("cripta-01")
    print("Salas en el esqueleto:", len(esqueleto))
  #  print("Solicitudes tras iniciar:", gestor.solicitudes_realizadas())

    sala = gestor.asegurar_sala(1)
    print("Enemigos en la sala 1:", len(sala.enemigos))
    print("Salas cargadas:", gestor._salas_cargadas)
    print("Solicitudes tras asegurar la sala 1:", gestor.solicitudes_realizadas())

    antes = gestor.solicitudes_realizadas()
    gestor.asegurar_sala(2)
    print("Solicitudes nuevas por la sala 2 (esperado 0):", gestor.solicitudes_realizadas() - antes)