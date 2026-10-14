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


class ResumenRed:
    def __init__(self, solicitudes, presupuesto, aciertos_cache, fallos_cache):
        self.solicitudes = solicitudes
        self.presupuesto = presupuesto
        self.aciertos_cache = aciertos_cache
        self.fallos_cache = fallos_cache


class GestorDatos:

    def __init__(self, fuente, ruta_base="datos_locales", cache_size=25):
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

        # estado de la cripta en curso
        self._planificador = None
        self._id_cripta_actual = None
        self._salas_cargadas = []
        self._contenido_en_memoria = []
        self._detalles = None
        self._id_detalles = None

    def _version_del_catalogo(self):
        if self._version_catalogo is None: # si no hay una guardada
            self._version_catalogo = self.fuente.obtener_version_catalogo()
        return self._version_catalogo

    def _version_de_cripta(self, id_cripta):
        if self._id_cripta_version != id_cripta:
            self._version_cripta = self.fuente.obtener_version_cripta(id_cripta)
            self._id_cripta_version = id_cripta
        return self._version_cripta

    # sirven para: detectar si la cripta o el catalogo cambiaron desde que se jugo la partida
    def version_cripta(self, id_cripta):
        return self._version_de_cripta(id_cripta)

    def version_catalogo(self):
        return self._version_del_catalogo()

    def listar_criptas(self):
        return self.fuente.list_criptas()

    def solicitudes_realizadas(self):
        return self.fuente.solicitudes_realizadas
    ###


    def obtener_ficha(self, id_ficha):
        # se busca por id: el resultado no siempre viene en el orden pedido
        for ficha in self.resolver_fichas([id_ficha]):
            if ficha.id == id_ficha:
                return ficha
        return None

    def resolver_fichas(self, ids_tipos):
        #ids_tipos= fichas que se quieren buscar
        # guarda los que no estan duplicados: evita buscar la misma ficha más de una vez en memoria o disco.
        unicos = []
        for id_ficha in ids_tipos:
            if id_ficha not in unicos:
                unicos.append(id_ficha)

        resultado = []
        faltantes = []
        for id_ficha in unicos:
            ficha = self.cache_catalogo.obtener(id_ficha)
            if ficha is not None: #ficha si estaba cargada previamente en la cache
                self.aciertos_cache += 1
                resultado.append(ficha)
            else:
                self.fallos_cache += 1 #ficha no estaba en la cache
                faltantes.append(id_ficha) #lo pone en los que faltan para buscarlos depues

        if not faltantes:
            return resultado #si todas las fichas estaban entonces retorna resultado

        # 2. disco (validado contra la version del catalogo)
        version_actual = self._version_del_catalogo()
        #Obtiene la versión actual del catálogo desde la fuente o memoria
        # para asegurarse de no leer datos viejos

        #carga las fichas de ese catalogo
        entidades_disco = self.almacenamiento_disco.cargar_catalogo(version_actual)


        #guarda las fichas en disco si no es un obj vacio, si si es vacio pone una
        #lista vacia nueva
        en_disco = entidades_disco if entidades_disco is not None else []

        por_pedir = []
        for id_ficha in faltantes: #porc cada ficha que faltaba
            encontrada = None
            for ficha in en_disco: #por cada ficha en disco
                if ficha.id == id_ficha: #compara la cada ficha en el disco por cada ficha que le entra
                    encontrada = ficha #si es igual la asigna a encontrada
                    break #sale del ciclo
            if encontrada is not None: #si encontrada existe
                self.cache_catalogo.agregar(encontrada, self) #la agrega al cache
                resultado.append(encontrada)
            else:
                por_pedir.append(id_ficha) #si no se encuentra en disco se agrega a por pedir

        # Pedir  todas las que faltan juntas en lotes de 10
        if por_pedir:
            # la fuente offline devuelve el catalogo completo: solo se toma lo pedido
            nuevas = []
            for ficha in self.fuente.obtener_fichas_catalogo(por_pedir): #por cada ficha en las fichas guardades en la fuente(on u off)
                if ficha is not None and ficha.id in por_pedir: #si la ficha existr y la ficha esta en por pedir
                    nuevas.append(ficha) #la guarda

            for ficha in nuevas: #por cada ficha que se acaba de buscar  se guardan en cache
                self.cache_catalogo.agregar(ficha, self)
                resultado.append(ficha)
            # se guarda lo que ya habia en disco tanto viejas como nuevas
            self.almacenamiento_disco.guardar_catalogo(version_actual, en_disco + nuevas)

        return resultado #retorna las fichas salvadas

    def obtener_detalles(self, id_cripta):
        if self._id_detalles != id_cripta:
            self._detalles = self.fuente.obtener_detalles_cripta(id_cripta)
            self._id_detalles = id_cripta
        return self._detalles

    def resumen_red(self):
        presupuesto = self._detalles.presupuesto_solicitudes if self._detalles is not None else None
        return ResumenRed(self.solicitudes_realizadas(), presupuesto,
                          self.aciertos_cache, self.fallos_cache)

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
        tipos = []
        for sala in contenido:
            self._contenido_en_memoria.append(sala)
            self._salas_cargadas.append(sala.id_sala)
            for enemigo in sala.enemigos:
                tipos.append(enemigo.tipo)
            for trampa in sala.trampas:
                tipos.append(trampa.tipo)
            for objeto in sala.objetos:
                tipos.append(objeto)
        self.resolver_fichas(tipos)   # catalogo de todo lo nuevo, en lotes


    #verifica si el planificador es distinto de none
    def _validar_cripta_iniciada(self):
        if self._planificador is None:
            raise RuntimeError("Llamar a iniciar_cripta()")

    def asegurar_sala(self, id_sala):
        self._validar_cripta_iniciada()
        if id_sala not in self._salas_cargadas:
            lote = self._planificador.planificar(id_sala, self._salas_cargadas)
            self._cargar_lote(lote)
        for sala in self._contenido_en_memoria:
            if sala.id_sala == id_sala:
                return sala
        return None

    def precargar(self, id_sala):
        self._validar_cripta_iniciada()
        lote = self._planificador.planificar(id_sala, self._salas_cargadas)
        if lote:
            self._cargar_lote(lote)