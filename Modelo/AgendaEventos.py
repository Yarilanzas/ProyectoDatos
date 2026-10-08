#Aqui manejamos los eventos pendientes

class AgendaEventos:
    def __init__(self):
        self.heap = []

    def esta_vacia(self):
        return len(self.heap) == 0

    def agregar(self, evento):
        self.heap.append(evento)
        self._subir(len(self.heap) - 1)

    def siguiente(self):
        while not self.esta_vacia():
            evento = self.heap[0]

            if evento.cancelado:
                self._eliminar_raiz()
                continue

            return evento

        return None

    def extraer(self):
        evento = self.siguiente()

        if evento is None:
            return None

        self._eliminar_raiz()
        return evento

    def _subir(self, indice):
        while indice > 0:
            padre = (indice - 1) // 2

            if self.heap[indice] < self.heap[padre]:
                self.heap[indice], self.heap[padre] = (
                    self.heap[padre],
                    self.heap[indice]
                )
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

            self.heap[indice], self.heap[menor] = (
                self.heap[menor],
                self.heap[indice]
            )

            indice = menor

    def _eliminar_raiz(self):
        ultimo = self.heap.pop()

        if not self.esta_vacia():
            self.heap[0] = ultimo
            self._bajar(0)