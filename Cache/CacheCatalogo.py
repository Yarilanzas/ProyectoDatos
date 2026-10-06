import Estructuras


class CacheCatalogo:

    def __init__(self, tamanio_maximo,fichas,orden_uso):
        self.tamanio_maximo = tamanio_maximo
        self.fichas = []
        self.orden_uso = Estructuras.Queue()

    def esta_en_cache(self, id_ficha):
        encontrado, _ = self._buscar_posicion(id_ficha)
        '''ese _ es que nos va a devolver un valor que no nos importa 
        en esta funcion por lo que lo dejamos afuera '''
        return encontrado

    def agregar(self, ficha):
        encontrado, posicion = self._buscar_posicion(ficha.id)
        if not encontrado:
            self.fichas.insert(posicion, ficha)

    def _buscar_posicion(self, id_buscado):
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

