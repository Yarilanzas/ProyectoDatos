class Evento:
    def __init__(self, tiempo, secuencia, tipo, actor=None, datos=None):
        self.tiempo = tiempo
        self.secuencia = secuencia
        self.tipo = tipo
        self.actor = actor
        self.datos = datos  # carga útil opcional (p. ej. daño y fin de un veneno)
        self.cancelado = False
        self.indice_heap = -1  # posición en AgendaEventos.heap; -1 si no está en la agenda

    def cancelar(self):
        self.cancelado = True

    def __lt__(self, otro):
        if self.tiempo != otro.tiempo:
            return self.tiempo < otro.tiempo

        return self.secuencia < otro.secuencia

    def __str__(self):
        return f"Evento(tiempo={self.tiempo}, secuencia={self.secuencia}, tipo={self.tipo})"