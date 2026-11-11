# Verificación de resolubilidad de una cripta (spec 002).
#
# Modelo puro (Principio II, FR-023): sin red, archivos, consola, random ni reloj. Solo importa DTOS,
# Modelo.ordenamiento.merge_sort y Modelo.Estructuras.Queue (lo comprueba tests/test_resolubilidad.py, T016).
#
# Principio I: las estructuras del recorrido son arreglos (list creada con su tamaño y usada por índice), la cola
# propia y el índice de llaves ordenado con búsqueda binaria escrita a mano. Sin dict, set, heapq, deque, bisect,
# collections, sorted() ni .sort(). Recorrer el dict `sala.salidas` del DTO es uso auxiliar permitido.
#
# Notación (data-model.md): S salas, E salidas, K llaves distintas, L ubicaciones, C salidas cerradas con llave,
# M = L + C + 1 menciones de llaves.

from Modelo.ordenamiento import merge_sort


def _identidad(valor):
    return valor


class IndiceLlaves:
    """Índice de llaves (R4): arreglo `ids` ordenado y sin repetidos; la posición de cada id es su número de llave.

    Ese número indexa los arreglos del recorrido (`obtenida`, `en_ronda`, `espera`...). Como `ids` está ordenado,
    el orden por número es el orden por identificador (FR-007, FR-014).

    Invariante: ids[i] < ids[i+1].

    | Operación                                          | Complejidad |
    |----------------------------------------------------|-------------|
    | construir(menciones): merge_sort + quitar repetidos| O(M log M)  |
    | numero(id_llave): búsqueda binaria; −1 si no está  | O(log K)    |
    | id_de(numero)                                      | O(1)        |
    | cantidad()                                         | O(1)        |
    """

    def __init__(self, ids):
        self.ids = ids

    @classmethod
    def construir(cls, menciones):
        """Arma el índice con las menciones de llaves (ids de ubicaciones, llaves de salidas cerradas y
        llave_salida). Las menciones None se ignoran. O(M log M)."""
        validas = []
        for id_llave in menciones:
            if id_llave is not None:
                validas.append(id_llave)
        ordenadas, _ = merge_sort(validas, _identidad)

        # los iguales quedan contiguos: un barrido lineal deja una sola copia de cada uno, O(M)
        ids = []
        for id_llave in ordenadas:
            if len(ids) == 0 or ids[len(ids) - 1] != id_llave:
                ids.append(id_llave)
        return cls(ids)

    def numero(self, id_llave):
        """Número (posición) de `id_llave`, o −1 si no está. Búsqueda binaria escrita a mano, O(log K)."""
        inicio, fin = 0, len(self.ids) - 1
        while inicio <= fin:
            medio = (inicio + fin) // 2
            actual = self.ids[medio]
            if actual == id_llave:
                return medio
            if actual < id_llave:
                inicio = medio + 1
            else:
                fin = medio - 1
        return -1

    def id_de(self, numero):
        """Identificador de la llave número `numero`. O(1)."""
        return self.ids[numero]

    def cantidad(self):
        """K, cantidad de llaves distintas. O(1)."""
        return len(self.ids)
