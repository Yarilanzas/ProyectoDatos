#para hacer el inventario, decidi hacerle con u na lista doblemente enlazada,
#ya que esta especifica que puede recorrerse de delante y poe detras

from Modelo.ordenamiento import elegir_algoritmo
import struct

class NodoInventario:
    #los slots sirven para poder es una optimizacion para las instancias, en este caso, como se llama tanto a cada objeto del inventario
    #crea una instancia de la clase
    #
    __slots__ = ("instancia_id", "tipo_id", "nombre", "peso", "valor", "clase","ataque_bonus","defensa_bonus" ,"anterior", "siguiente")

    def __init__(self, instancia_id, tipo_id,nombre, peso, valor, clase,ataque_bonus = 0, defensa_bonus = 0):
        self.instancia_id = instancia_id
        self.tipo_id = tipo_id
        self.nombre = nombre
        self.peso = peso
        self.valor = valor
        self.clase = clase #catalogo
        self.ataque_bonus = ataque_bonus
        self.defensa_bonus = defensa_bonus
        self.anterior = None
        self.siguiente = None

class Inventario:
    def __init__(self,cap_max):
        self._cabeza = None
        self._cola = None
        self._cursor = None
        self._cantidad = 0
        self._capacidad = cap_max
        self._arma_equipada = None
        self._armadura_equipada = None

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
      if self._cursor is None:
          return None
      return self.suelta_nodo(self._cursor)


    def equipar_actual(self):
        nodo = self._cursor
        if nodo is None:
            return None

        if nodo is not self._cabeza:
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

        if nodo.clase == "arma":
            self._arma_equipada = nodo
        elif nodo.clase == "armadura":
            self._armadura_equipada = nodo

        return nodo

    def arma_equipada(self):
        return self._arma_equipada

    def armadura_equipada(self):
        return self._armadura_equipada

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

    def suelta_nodo (self, nodo):
        anterior, siguiente = nodo.anterior, nodo.siguiente

        if anterior:
            anterior.siguiente = siguiente
        else:
            self._cabeza = siguiente

        if siguiente:
            siguiente.anterior = anterior
        else:
            self._cola = anterior

        if self._cursor is nodo:
            self._cursor = siguiente or anterior

        if self._arma_equipada is nodo:
            self._arma_equipada = None
        if self._armadura_equipada is nodo:
            self._armadura_equipada = None

        nodo.anterior = nodo.siguiente = None
        self._cantidad -= 1
        return nodo

    def _reinsertar(self,nodo, anterior, siguiente):
        vacio = self._cabeza is None # si es vacio devuelve None

        nodo.anterior = anterior
        nodo.siguiente = siguiente
        if anterior:
            anterior.siguiente = nodo
        else:
            self._cabeza = nodo
        if siguiente:
            siguiente.anterior = nodo
        else:
            self._cola = nodo
        self._cantidad += 1
        if vacio:
            self._cursor = nodo #si no habia nada, apunta al unico obj


    def to_bytes(self) -> bytes:
        cuerpo = bytearray()
        cuerpo.extend(struct.pack(">HH", self._capacidad, self._cantidad))
        for nodo in self:
            b_instancia = nodo.instancia_id.encode('utf-8')
            b_tipo = nodo.tipo_id.encode('utf-8')
            b_nombre = nodo.nombre.encode('utf-8')
            b_clase = nodo.clase.encode('utf-8')

            es_arma = 1 if self._arma_equipada is nodo else 0
            es_armadura = 1 if self._armadura_equipada is nodo else 0
            es_cursor = 1 if self._cursor is nodo else 0

            cuerpo.extend(struct.pack(
                ">BBBBhhhhBBB", len(b_instancia), len(b_tipo), len(b_nombre), len(b_clase),
                nodo.peso,nodo.valor,nodo.ataque_bonus, nodo.defensa_bonus,
                es_arma,es_armadura,es_cursor
            ))
            cuerpo.extend(b_instancia + b_tipo + b_nombre+ b_clase)

        return struct.pack(">H", len(cuerpo)) + cuerpo

    @classmethod
    def from_bytes(cls, datos:bytes) -> "Inventario":
        offset = 2
        capacidad, cantidad = struct.unpack_from(">HH", datos, offset)
        offset += 4
        inv =cls(capacidad)
        cursor_nodo = None
        for _ in range(cantidad):
            (len_i, len_t, len_n, len_c, peso, valor, ab, db,
            es_arma, es_armadura, es_cursor) = struct.unpack_from(">BBBBhhhhBBB", datos, offset)

            offset += struct.calcsize(">BBBBhhhhBBB")
            inst = datos[offset:offset + len_i].decode("utf-8"); offset += len_i
            tipo = datos[offset:offset + len_t].decode("utf-8"); offset += len_t
            nom = datos[offset:offset + len_n].decode("utf-8");offset += len_n
            clase = datos[offset:offset + len_c].decode("utf-8");offset += len_c

            nodo = NodoInventario(inst, tipo, nom, peso, valor, clase, ab, db)
            inv.recoge(nodo)

            if es_arma: inv._arma_equipada = nodo
            if es_armadura: inv._armadura_equipada = nodo
            if es_cursor: cursor_nodo = nodo
            if cursor_nodo: inv._cursor = cursor_nodo
        return inv

    @classmethod
    def from_dict(cls, datos:dict) -> "Inventario":
        inv = cls(datos["capacidad"])
        cursor_nodo = None
        for n in datos["nodos"]:
            nodo = NodoInventario(
                n["instancia_id"], n["tipo_id"], n["nombre"],
                n["peso"], n["valor"], n["clase"],
                n["ataque_bonus"], n["defensa_bonus"]
            )

            inv.recoge(nodo)
            if n["es_arma"]: inv._arma_equipada = nodo
            if n["es_armadura"]: inv._armadura_equipada = nodo
            if n["es_cursor"]: cursor_nodo = nodo
        if cursor_nodo: inv._cursor = cursor_nodo
        return inv

      #Para la comparativa JSON vs binario que pide §4.10
    def to_dict(self) -> dict:
        return {
            "capacidad": self._capacidad,
            "nodos": [{
                "instancia_id": n.instancia_id, "tipo_id": n.tipo_id, "nombre": n.nombre,
                "peso": n.peso, "valor": n.valor, "clase": n.clase,
                "ataque_bonus": n.ataque_bonus, "defensa_bonus": n.defensa_bonus,
                "es_arma": self._arma_equipada is n,
                "es_armadura": self._armadura_equipada is n,
                "es_cursor": self._cursor is n,
            } for n in self]
        }

