from Modelo.Evento import Evento
from Modelo.AgendaEventos import AgendaEventos


class MotorSimulacion:

    def __init__(self):
        self.reloj = 0
        self.secuencia = 0
        self.agenda = AgendaEventos()

    def sig_secu(self):
        secuencia = self.secuencia
        self.secuencia += 1
        return secuencia

    def calcu_inter(self, costo, velocidad):
        return max(1, costo * 100 // velocidad)

    def programar_evento(self, tiempo, tipo, actor=None):

        secuencia = self.sig_secu()
        evento = Evento(tiempo,secuencia,tipo,actor )
        self.agenda.agregar(evento)
        return evento

    def proxima_accion(self, actor, costo=100):

        intervalo = self.calcu_inter(costo,actor.velocidad )
        actor.tiempo_siguiente = self.reloj + intervalo
        return self.programar_evento(actor.tiempo_siguiente,  "ACCION_ACTOR",actor )

    def ejecu_sig_evento(self):

        evento = self.agenda.extraer()
        if evento is None:
            return False

        self.reloj = evento.tiempo
        self.ejecutar_evento(evento)
        return True

    def ejecutar_evento(self, evento):

        actor = evento.actor
        if actor is not None and not actor.esta_vivo():
            return

        print(f"Tiempo {self.reloj}: "f"ejecutando {evento.tipo}" )

        if actor is not None:
            print( f"Actor: {actor.id}" )

    def ejecutar(self):

        while not self.agenda.esta_vacia():
            self.ejecu_sig_evento()