import random
from Modelo.Evento import Evento
from Modelo.AgendaEventos import AgendaEventos
from Modelo.Enemigo import Enemigo

class MotorSimulacion:

    def __init__(self,semilla=None):
        self.reloj = 0
        self.secuencia = 0
        self.agenda = AgendaEventos()
        self.azar = random.Random(semilla)
        self.salas = []
        self.jugador = None

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

        intervalo = self.calcu_inter(costo, actor.velocidad)

        actor.tiempo_siguiente = self.reloj + intervalo
        evento = self.programar_evento(actor.tiempo_siguiente,"ACCION_ACTOR", actor)
        actor.evento_actual = evento
        return evento

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

        print(f"Tiempo {self.reloj}: ejecutando {evento.tipo}")

        if actor is not None:
            print(f"Actor: {actor.id}")

            if isinstance(actor, Enemigo):

                accion = self.accion_enemigo(actor,self.jugador )
                print("Acción:", accion)

                if accion == "MOVER":

                    resultado = self.salida_errante(actor)
                    if resultado is None:
                        print("No hay salidas abiertas")

                    else:
                        direccion, salida = resultado

                        print("Salida elegida:", direccion)
                        movio = self.mover_enemigo(actor, self.salas, salida )

                        if movio:
                            print("Enemigo movido a sala:",actor.sala.id )
                        else:
                            print("No se encontró la sala destino")

                elif accion == "ATACAR":

                   self.atacar(actor,self.jugador)

                elif accion == "ESPERAR":

                    print("El enemigo espera")

                if actor.esta_vivo():# verificacion porque actor muerto no puede ejecutar eventos
                    self.proxima_accion(actor,100)

    def cambiar_velocidad(self, actor, nueva_velocidad):

        velocidad_anterior = actor.velocidad
        tiempo_restante = actor.tiempo_siguiente - self.reloj
        restante_nuevo = max(1,tiempo_restante * velocidad_anterior )// nueva_velocidad

        # Cancelar el evento anterior
        if actor.evento_actual is not None:
            actor.evento_actual.cancelar()

        actor.velocidad = nueva_velocidad
        nuevo_tiempo = self.reloj + restante_nuevo
        actor.tiempo_siguiente = nuevo_tiempo
        evento = self.programar_evento(nuevo_tiempo,"ACCION_ACTOR",actor)
        actor.evento_actual = evento

        return evento

    def activar_enemigo(self, enemigo):
        if enemigo.activo:
            return
        enemigo.activo = True
        self.proxima_accion(enemigo,100)

    def activar_enemigos(self, enemigos):
        enemigos_ordenados = sorted( enemigos, key=lambda enemigo: enemigo.id )

        for enemigo in enemigos_ordenados:
            self.activar_enemigo(enemigo)

    def salidas_abiertas(self, sala):
        abiertas = []

        for direccion, salida in sala.salidas.items():
            if not salida.cerrada:
                abiertas.append((direccion, salida))

        return abiertas

    def salida_errante(self, enemigo):
        salidas = self.salidas_abiertas(enemigo.sala)

        if not salidas:
            return None

        return self.azar.choice(salidas)

    def mover_enemigo(self,enemigo,salas,salida):
        sala_destino = self.buscar_sala(salas,salida.sala_destino)
        if sala_destino is None:
            return False
        enemigo.sala= sala_destino
        return True

    def accion_enemigo(self, enemigo, jugador):

        if enemigo.sala == jugador.sala:
            return "ATACAR"

        if enemigo.comportamiento == "guardian":
            return "ESPERAR"

        if enemigo.comportamiento == "errante":
            return "MOVER"

        if enemigo.comportamiento == "rastreador":
            return "MOVER_RASTRO"

        return "ESPERAR"

    def buscar_sala(self,salas, id_sala):
        for sala in salas:
            if sala.id == id_sala:
                return sala
        return None

    def atacar(self, atacante, defensor):

        #enunciado daño = max(1, ataque_atacante + azar.randint(0, 4) - defensa_defensor)
        azar = self.azar.randint(0, 4)
        dano = max( 1, atacante.ataque + azar - defensor.defensa)
        defensor.recibir_dano(dano)

        print("Ataque:",atacante.id, "->",defensor.id )
        print("Daño:",  dano)
        print("Vida de",defensor.id, ":", defensor.vida)

        if not defensor.esta_vivo():
            print("Actor", defensor.id,"ha muerto" )

        return dano