import random
from Modelo.Evento import Evento
from Modelo.AgendaEventos import AgendaEventos
from Modelo.Enemigo import Enemigo
from Modelo.retroceso import Historial

class MotorSimulacion:

    def __init__(self,semilla=None):
        self.reloj = 0
        self.secuencia = 0
        self.agenda = AgendaEventos()
        self.azar = random.Random(semilla)
        self.salas = []
        self.jugador = None
        self.historial = Historial()

    def sig_secu(self):
        secuencia = self.secuencia
        self.secuencia += 1
        return secuencia

    def calcu_inter(self, costo, velocidad):
        return max(1, costo * 100 // velocidad)

    def programar_evento(self, tiempo, tipo, actor=None):
        secuencia_anterior = self.secuencia

        secuencia = self.sig_secu()
        evento = Evento(tiempo, secuencia, tipo, actor)
        self.agenda.agregar(evento)

        def deshacer():
            evento.cancelar()
        self.historial.registrar(
            deshacer=deshacer,
            description=f"programación de evento {tipo}"
        )

        return evento

    def proxima_accion(self, actor, costo=100):

        intervalo = self.calcu_inter(costo, actor.velocidad)

        actor.tiempo_siguiente = self.reloj + intervalo
        evento = self.programar_evento(actor.tiempo_siguiente,"ACCION_ACTOR", actor)
        actor.evento_actual = evento
        return evento

    def ejecu_sig_evento(self):
        reloj_anterior = self.reloj
        estado_azar_anterior = self.azar.getstate()

        evento = self.agenda.extraer()

        if evento is None:
            return False

        def deshacer():
            self.reloj = reloj_anterior
            self.azar.setstate(estado_azar_anterior)

            if not self.agenda.contiene(evento):
                self.agenda.agregar(evento)

            evento.cancelado = False

        # Registrar antes de ejecutar el evento.
        self.historial.registrar(
            deshacer=deshacer,
            description=f"ejecución de evento {evento.tipo}"
        )

        self.reloj = evento.tiempo
        self.ejecutar_evento(evento)
        return True

    def avanzar_hasta_jugador(self):

        jugador = self.jugador

        if jugador is None:
            return False

        # Procesar eventos hasta que llegue el momento del jugador.
        while not self.agenda.esta_vacia():
            evento = self.agenda.siguiente()

            if evento is None:
                return False

            # El jugador vuelve a tener una decisión.
            if (evento.actor is jugador and evento.tiempo == jugador.tiempo_siguiente):
                self.reloj = evento.tiempo
                return True

            self.ejecu_sig_evento()

        return False

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
        restante_nuevo = max(1,(tiempo_restante * velocidad_anterior )// nueva_velocidad)

        # Cancelar el evento anterior
        if actor.evento_actual is not None:
            actor.evento_actual.cancelar()

        actor.velocidad = nueva_velocidad
        nuevo_tiempo = self.reloj + restante_nuevo
        actor.tiempo_siguiente = nuevo_tiempo
        evento = self.programar_evento(nuevo_tiempo,"ACCION_ACTOR",actor)
        actor.evento_actual = evento

        return evento

    def cambiar_velocidad_reversible(self, actor, nueva_velocidad):
        velocidad_anterior = actor.velocidad
        tiempo_anterior = actor.tiempo_siguiente
        evento_anterior = actor.evento_actual

        cancelado_anterior = (
            evento_anterior.cancelado
            if evento_anterior is not None
            else None
        )

        evento_nuevo = self.cambiar_velocidad(actor, nueva_velocidad)

        def deshacer():
            evento_nuevo.cancelar()

            if evento_anterior is not None:
                if not self.agenda.contiene(evento_anterior):
                    self.agenda.agregar(evento_anterior)

                evento_anterior.cancelado = cancelado_anterior

            actor.velocidad = velocidad_anterior
            actor.tiempo_siguiente = tiempo_anterior
            actor.evento_actual = evento_anterior

        self.historial.registrar(
            deshacer=deshacer,
            description=f"cambio de velocidad de {actor.id}"
        )

        return evento_nuevo

    def activar_enemigo(self, enemigo):
        if enemigo.activo:
            return
        enemigo.activo = True
        self.proxima_accion(enemigo,100)

    def activar_enemigos(self, enemigos):

        enemigos_ordenados = list(enemigos)
        
        # Ordenamiento por inserción según el id.
        for i in range(1, len(enemigos_ordenados)):
            actual = enemigos_ordenados[i]
            j = i - 1

            while j >= 0 and enemigos_ordenados[j].id > actual.id:
                enemigos_ordenados[j + 1] = enemigos_ordenados[j]
                j -= 1

            enemigos_ordenados[j + 1] = actual

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

        sala_anterior = enemigo.sala
        enemigo.sala = sala_destino

        self.historial.registrar(
            deshacer=lambda:
            setattr(enemigo, "sala", sala_anterior),
            description=f"movimiento de {enemigo.id}"
        )
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

        estado_azar_anterior = self.azar.getstate()

        #enunciado daño = max(1, ataque_atacante + azar.randint(0, 4) - defensa_defensor)
        azar = self.azar.randint(0, 4)
        dano = max( 1, atacante.ataque + azar - defensor.defensa)

       # Guardar el estado anterior del daño

        vida_anterior = defensor.vida
        vivo_anterior = defensor.vivo

        defensor.recibir_dano(dano)

        def deshacer():
            defensor.vida = vida_anterior
            defensor.vivo = vivo_anterior
            self.azar.setstate(estado_azar_anterior)

        self.historial.registrar(
            deshacer=deshacer,
            description=f"daño de {atacante.id} a {defensor.id}"
        )

        print("Ataque:",atacante.id, "->",defensor.id )
        print("Daño:",  dano)
        print("Vida de",defensor.id, ":", defensor.vida)

        if not defensor.esta_vivo():
            print("Actor", defensor.id,"ha muerto" )

        return dano

    def accion_jugador(self):
        if self.jugador is None:
            return False

        self.historial.abrir_intervalo()
        return True

    def mover_jugador(self, direccion):
        jugador = self.jugador

        if jugador is None or jugador.sala is None:
            return False

        # Buscar la salida en la dirección indicada.
        salida = jugador.sala.salidas.get(direccion)

        if salida is None or salida.cerrada:
            print("No existe una salida abierta en esa dirección.")
            return False

        # Buscar la sala de destino.
        sala_destino = self.buscar_sala(
            self.salas,
            salida.sala_destino
        )

        if sala_destino is None:
            print("No se encontró la sala destino.")
            return False

        # Guardar el estado anterior para poder deshacer el movimiento.
        sala_anterior = jugador.sala

        # Abrir el intervalo antes de modificar el estado.
        self.accion_jugador()

        jugador.sala = sala_destino

        self.historial.registrar(
            deshacer=lambda: setattr(jugador, "sala", sala_anterior),
            description="movimiento del jugador"
        )

        # Programar la siguiente acción del jugador.
        self.proxima_accion(jugador, costo=100)
        self.avanzar_hasta_jugador()

        return True
