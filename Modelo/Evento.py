class Evento:
    def __init__(self, tiempo, secuencia, tipo, actor=None):
        self.tiempo = tiempo
        self.secuencia = secuencia
        self.tipo = tipo
        self.actor = actor
        self.cancelado = False

    def cancelar(self):
        self.cancelado = True

    def __lt__(self, otro):
        if self.tiempo != otro.tiempo:
            return self.tiempo < otro.tiempo

        return self.secuencia < otro.secuencia

    def __str__(self):
        return f"Evento(tiempo={self.tiempo}, secuencia={self.secuencia}, tipo={self.tipo})"