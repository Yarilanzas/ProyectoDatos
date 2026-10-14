
# Aqui manejamos los eventos pendientes.

class AgendaEventos:
    def __init__(self):
        self.heap = []

    def esta_vacia(self):
        return self.siguiente() is None

    def agregar(self, evento):
        if self.contiene(evento):
            return

        indice = len(self.heap)
        self.heap.append(evento)
        evento.indice_heap = indice
        self._subir(indice)

    def siguiente(self):
        self._limpiar_cancelados_raiz()
        return self.heap[0] if self.heap else None

    def extraer(self):
        self._limpiar_cancelados_raiz()
        if not self.heap:
            return None
        return self._eliminar_indice(0)

    def extraer_evento(self, evento):
        if not self.contiene(evento):
            return None
        return self._eliminar_indice(evento.indice_heap)

    def _limpiar_cancelados_raiz(self):
        while self.heap and self.heap[0].cancelado:
            self._eliminar_indice(0)

    def _eliminar_evento(self, evento):
        # Se conserva por compatibilidad con llamadas internas existentes.
        if self.contiene(evento):
            self._eliminar_indice(evento.indice_heap)

    def _eliminar_indice(self, indice):
        ultimo_indice = len(self.heap) - 1
        eliminado = self.heap[indice]
        eliminado.indice_heap = -1

        if indice == ultimo_indice:
            self.heap.pop()
            return eliminado

        ultimo = self.heap.pop()
        self.heap[indice] = ultimo
        ultimo.indice_heap = indice

        if indice > 0:
            padre = (indice - 1) // 2
            if self.heap[indice] < self.heap[padre]:
                self._subir(indice)
            else:
                self._bajar(indice)
        else:
            self._bajar(indice)

        return eliminado

    def _intercambiar(self, i, j):
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]
        self.heap[i].indice_heap = i
        self.heap[j].indice_heap = j

    def _subir(self, indice):
        while indice > 0:
            padre = (indice - 1) // 2
            if self.heap[indice] < self.heap[padre]:
                self._intercambiar(indice, padre)
                indice = padre
            else:
                break

    def _bajar(self, indice):
        while True:
            izquierdo = 2 * indice + 1
            derecho = 2 * indice + 2
            menor = indice

            if izquierdo < len(self.heap):
                if self.heap[izquierdo] < self.heap[menor]:
                    menor = izquierdo

            if derecho < len(self.heap):
                if self.heap[derecho] < self.heap[menor]:
                    menor = derecho

            if menor == indice:
                break

            self._intercambiar(indice, menor)
            indice = menor

    def _eliminar_raiz(self):
        if self.heap:
            self._eliminar_indice(0)

    def contiene(self, evento):
        indice = evento.indice_heap
        return 0 <= indice < len(self.heap) and self.heap[indice] is evento
