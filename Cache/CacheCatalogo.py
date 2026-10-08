import Estructuras


class CacheCatalogo:

    def __init__(self, tamanio_maximo):
        self.tamanio_maximo = tamanio_maximo
        self.fichas = []
        self.orden_uso = Estructuras.Queue()
        '''se decide trabajar con una cola para guardar el orden el que se van usando 
        las fichas ya que el principio fifo se adapta perfectamente a los requerimientos de 
        liberar el espacio si ya esta lleno. Se toma la decision de hacer modificaciones al
        momento de agregar un objeto a la lista de uso para evitar consumir memoria y tener 
        fichas duplicadas'''

    def obtener(self, id_ficha):
        encontrado, posicion = self._buscar_posicion(id_ficha)
        if encontrado:
            self.actualizar_orden(id_ficha)
            return self.fichas[posicion]
        return None
    def esta_en_cache(self, id_ficha):
        return self.obtener(id_ficha) is not None #devuelve true si ell metodo devuelve algo que no es none


    def agregar(self, ficha, gestor_datos=None):
        encontrado, posicion = self._buscar_posicion(ficha.id)

        if not encontrado:
            if len(self.fichas) >= self.tamanio_maximo:
                self.desalojar(gestor_datos)

            self.fichas.insert(posicion, ficha)

            self.actualizar_orden(ficha.id)
        print("agrgada")

    def  _buscar_posicion(self, id_buscado):
        #busqueda binaria
        inicio = 0
        fin = len(self.fichas) - 1

        while inicio <= fin:
            medio = (inicio + fin) // 2
            id_actual = self.fichas[medio].id

            if id_actual == id_buscado:
                return (True, medio)
            elif id_actual < id_buscado:
                inicio = medio + 1
            else:
                fin = medio - 1

        return (False, inicio)

    def actualizar_orden(self, id_ficha):
        tamanio = self.orden_uso.size()
        encontrado = False

        for _ in range(tamanio):
            id_actual = self.orden_uso.dequeue()
            if id_actual == id_ficha:
                encontrado = True  #si es igual al que buscamos no lo inserta solo cambia el encontrado
            else:
                self.orden_uso.enqueue(id_actual)  #si no es el que buscamos lo vuelve a insertar


        self.orden_uso.enqueue(id_ficha) #al

    def desalojar(self, gestor_datos=None):
        while len(self.fichas) >= self.tamanio_maximo and not self.orden_uso.is_empty():
            id_candidato = self.orden_uso.dequeue()
            en_uso = gestor_datos.esta_en_uso(id_candidato) if gestor_datos else False

            if en_uso:
                self.orden_uso.enqueue(id_candidato)
            else:
                encontrado, pos = self._buscar_posicion(id_candidato)
                if encontrado:
                    self.fichas.pop(pos)
                break



'''pruebas:
if __name__ == "__main__":

    cache = CacheCatalogo(tamanio_maximo=3)  # chiquito a propósito, para forzar desalojo rápido

    # Simula una ficha mínima (ajusta según tu clase real)
    class FichaFalsa:
        def __init__(self, id):
            self.id = id




    f1 = FichaFalsa("ent_rata_gigante")
    f2 = FichaFalsa("itm_daga_oxidada")
    f3 = FichaFalsa("trp_dardos")
    f4 = FichaFalsa("itm_antorcha")

    # 1. Agregar hasta el tope
    cache.agregar(f1)
    cache.agregar(f2)
    cache.agregar(f3)
    print("¿f1 en cache?", cache.esta_en_cache("ent_rata_gigante"))  # True
    print("¿f4 en cache?", cache.esta_en_cache("itm_antorcha"))      # False, aún no se agregó

    # 2. Usar f1 de nuevo (para que quede como 'reciente', no debería ser desalojada)
    cache.obtener("ent_rata_gigante")

    # 3. Agregar una cuarta — debería desalojar la MENOS reciente (f2, porque f1 se volvió a usar)
    cache.agregar(f4)

    print("¿f1 sigue en cache?", cache.esta_en_cache("ent_rata_gigante"))  # esperado: True
    print("¿f2 sigue en cache?", cache.esta_en_cache("itm_daga_oxidada"))  # esperado: False (desalojada)
    # esperado: True
    print("¿f4 ya está?", cache.esta_en_cache("itm_antorcha"))


    class GestorFalso:
        def esta_en_uso(self, id_ficha):
            return id_ficha == "itm_daga_oxidada"  # simula que esta SIEMPRE está en uso


    cache2 = CacheCatalogo(tamanio_maximo=2)
    cache2.agregar(FichaFalsa("a"))
    cache2.agregar(FichaFalsa("b"))
    cache2.agregar(FichaFalsa("itm_daga_oxidada"), gestor_datos=GestorFalso())
    # "itm_daga_oxidada" nunca debería ser elegida para desalojo, aunque sea la más vieja'''
