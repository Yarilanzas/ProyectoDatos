#para hacer el inventario, decidi hacerle con u na lista doblemente enlazada,
#ya que esta especifica que puede recorrerse de delante y poe detras

from Modelo.ordenamiento import elegir_algoritmo

class NodoInventario:
    #los slots sirven para poder es una optimizacion para las instancias, en este caso, como se llama tanto a cada objeto del inventario
    #crea una instancia de la clase
    #
    __slots__ = ("instancia_id", "tipo_id", "nombre", "peso", "valor", "clase", "anterior", "siguiente")

    def __init__(self, instancia_id, tipo_id,nombre, peso, valor, clase):
        self.instancia_id = instancia_id
        self.tipo_id = tipo_id
        self.nombre = nombre
        self.peso = peso
        self.valor = valor
        self.clase = clase #catalogo
        self.anterior = None
        self.siguiente = None

class Inventario:
    def __init__(self,cap_max):
        self._cabeza = None
        self._cola = None
        self._cursor = None
        self._cantidad = 0
        self._capacidad = cap_max

    def lleno(self):
        return self._cantidad >= self._capacidad

    # agrega al final, si esta lleno no deja meter
    def recoge(self, nodo):
        if self.lleno():
            return False
        if self._cabeza is None:
            self._cabeza = nodo
            self._cursor = nodo
        else:
            nodo.anterior = self._cola
            self._cola.siguiente = nodo
        self._cola = nodo
        self._cantidad += 1
        return True


    # mueve el cursor a la posicion de adelante
    def avanza(self):
        if self._cursor and self._cursor.siguiente:
            self._cursor = self._cursor.siguiente
        return self._cursor

    # mueve el cursor a la posicion de atras
    def retrocede(self):
        if self._cursor and self._cursor.anterior:
            self._cursor = self._cursor.anterior
        return self._cursor

    def actual(self):
        return self._cursor

    def suelta_actual(self):
        nodo = self._cursor
        if nodo is None:
            return None

        anterior, siguiente = nodo.anterior, nodo.siguiente

        if anterior:
            anterior.siguiente = siguiente
        else:
            self._cabeza = siguiente

        if siguiente:
            siguiente.anterior = anterior
        else:
            self._cola = anterior

        #pasa al cursor a la cripta vecina
        self._cursor = siguiente or anterior
        nodo.anterior = nodo.siguiente = None
        self._cantidad -= 1
        return nodo


    def equipar_actual(self):
        nodo = self._cursor
        if nodo is None or nodo is self._cabeza:
            return nodo

        anterior, siguiente = nodo.anterior, nodo.siguiente
        if anterior:
            anterior.siguiente = siguiente
        if siguiente:
            siguiente.anterior = anterior
        else:
            self._cola = anterior


        nodo.anterior = None
        nodo.siguiente = self._cabeza
        self._cabeza.anterior = nodo
        self._cabeza = nodo
        return nodo

    def __iter__(self):
        nodo = self._cabeza
        while nodo:
            yield nodo
            nodo = nodo.siguiente


def vista_ordenada(inventario,criterio):
    #no modifica orden actual, arma lista aparte a partir del iter
    claves = {"peso" : lambda nodo:nodo.peso,
              "valor" : lambda nodo:nodo.valor,
              "nombre" : lambda nodo:nodo.nombre}
    key = claves[criterio]
    comparacion_costosa = (criterio == "nombre")
    items = list(inventario) #recorrido de lectura
    algoritmo = elegir_algoritmo(len(items), comparacion_costosa)
    return algoritmo(items,key)