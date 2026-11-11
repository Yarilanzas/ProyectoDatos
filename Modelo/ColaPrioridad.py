# Cola de prioridad de la búsqueda de rutas (spec 003, T005; data-model §3, research R1; Persona A, D-PEND-01).
# Montículo binario mínimo propio en una lista, con inserción perezosa. Principio I: sin heapq, bisect ni collections.


class ColaPrioridad:
    """Montículo binario mínimo de entradas ``(distancia, ordinal)``.

    Sale primero la entrada de menor distancia y, si empatan, la de menor ordinal. La inserción es perezosa: nunca se
    busca ni se actualiza una entrada vieja, así que un mismo ordinal puede estar varias veces y la búsqueda se queda
    con la primera que sale, que es la de menor distancia.

    | Operación        | Complejidad |
    |------------------|-------------|
    | insertar         | O(log t)    |
    | extraer_minimo   | O(log t)    |
    | vacia            | O(1)        |
    | vaciar           | O(1)        |
    | len              | O(1)        |

    t es la cantidad de entradas en la cola. No guarda estado fuera de la instancia (Principio I).
    """

    def __init__(self):
        # entradas[0] es la raíz; los hijos de i están en 2i + 1 y 2i + 2
        self.entradas = []

    def insertar(self, distancia, ordinal):
        """Agrega ``(distancia, ordinal)``. O(log t): sube desde la última hoja como máximo la altura del montículo."""
        entradas = self.entradas
        entradas.append((distancia, ordinal))
        self._subir(len(entradas) - 1)

    def extraer_minimo(self):
        """Quita y devuelve la entrada ``(distancia, ordinal)`` menor, o ``None`` si la cola está vacía (mismo criterio
        que ``AgendaEventos.extraer``). O(log t): la última hoja pasa a la raíz y baja como máximo la altura."""
        entradas = self.entradas
        if not entradas:
            return None
        minimo = entradas[0]
        ultima = entradas.pop()
        if entradas:
            entradas[0] = ultima
            self._bajar(0)
        return minimo

    def vacia(self):
        """``True`` si no quedan entradas. O(1)."""
        return not self.entradas

    def vaciar(self):
        """Deja la cola vacía y lista para otra búsqueda. O(1): reasigna la lista en lugar de borrar entrada por
        entrada (la vieja la libera el recolector)."""
        self.entradas = []

    def __len__(self):
        """Entradas en la cola, incluidas las viejas de la inserción perezosa. O(1)."""
        return len(self.entradas)

    def _subir(self, indice):
        # O(log t). Las entradas son tuplas de enteros: `<` compara distancia y luego ordinal.
        entradas = self.entradas
        entrada = entradas[indice]
        while indice > 0:
            padre = (indice - 1) // 2
            if entrada < entradas[padre]:
                entradas[indice] = entradas[padre]
                indice = padre
            else:
                break
        entradas[indice] = entrada

    def _bajar(self, indice):
        # O(log t): en cada nivel sube el menor de los dos hijos mientras sea menor que la entrada que baja.
        entradas = self.entradas
        cantidad = len(entradas)
        entrada = entradas[indice]
        while True:
            hijo = 2 * indice + 1
            if hijo >= cantidad:
                break
            derecho = hijo + 1
            if derecho < cantidad and entradas[derecho] < entradas[hijo]:
                hijo = derecho
            if entradas[hijo] < entrada:
                entradas[indice] = entradas[hijo]
                indice = hijo
            else:
                break
        entradas[indice] = entrada