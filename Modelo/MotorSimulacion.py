import random
from Modelo.Evento import Evento
from Modelo.AgendaEventos import AgendaEventos
from Modelo.Enemigo import Enemigo
from Modelo.Inventario import NodoInventario
from Modelo.retroceso import (Historial,recoger_reversible,soltar_reversible,equipar_reversible, usar_pergamino)
from Gestor.GestorDatos import GestorDatos

class MotorSimulacion:

    def __init__(self,semilla=None, gestor_datos=None):
        self.reloj = 0
        self.secuencia = 0
        self.agenda = AgendaEventos()
        self.azar = random.Random(semilla)
        self.salas = []
        self.jugador = None
        self.enemigos = []
        self.historial = Historial()
        self.contenidos_salas = []
        self.objetos_suelo = []
        self._salas_contenido_cargado = []
        self._estado_trampas = []
        # Una única instancia del gestor para este motor.
        self.gestor_datos = gestor_datos

        if self.gestor_datos is not None:
            self.gestor_datos.conectar_estado_juego(self)

    def _guardar_estado_trampa(self, id_trampa, activa):
        for estado in self._estado_trampas:
            if estado[0] == id_trampa:
                estado[1] = activa
                return

        self._estado_trampas.append([id_trampa, activa])

    def _obtener_estado_trampa(self, id_trampa, defecto=True):
        for estado in self._estado_trampas:
            if estado[0] == id_trampa:
                return estado[1]

        return defecto

    def cambiar_estado_trampa_reversible(self, trampa, activa):
        # Cambia el estado de una trampa y registra cómo deshacerlo

        estado_anterior = self._obtener_estado_trampa(trampa.instancia, True)

        self._guardar_estado_trampa(trampa.instancia, activa)

        self.historial.registrar(
            deshacer=lambda: self._guardar_estado_trampa(
                trampa.instancia, estado_anterior
            ),
            description=f"estado de trampa {trampa.instancia}"
        )

    def activar_trampas_de_sala(self, sala):
        if sala is None or self.jugador is None:
            return

        # Buscar el contenido de la sala actual.
        contenido_sala = None

        for contenido in self.contenidos_salas:
            if contenido.id_sala == sala.id:
                contenido_sala = contenido
                break

        if contenido_sala is None:
            return

        # Revisar las trampas de esta sala.
        for trampa in contenido_sala.trampas:

            # No activar una trampa que ya está desactivada.
            if not self._obtener_estado_trampa(trampa.instancia, True):
                continue

            if self.gestor_datos is None:
                raise RuntimeError("No hay gestor de datos para consultar la ficha de la trampa.")

            ficha = self.gestor_datos.obtener_ficha(trampa.tipo)

            if ficha is None or ficha.clase != "trampa":
                raise RuntimeError( f"No se encontró una ficha válida para la trampa: {trampa.tipo}" )

            intervalo = ficha.rearme

            if intervalo is None:
                intervalo = 300

            if intervalo < 0:
                raise ValueError(f"El tiempo de rearme de la trampa {trampa.instancia} no puede ser negativo.")

            # Desactivar la trampa y registrar cómo deshacer el cambio.
            self.cambiar_estado_trampa_reversible(trampa, False)

            # Guardar el estado anterior del jugador.
            vida_anterior = self.jugador.vida
            vivo_anterior = self.jugador.vivo

            # Aplicar el daño.
            self.jugador.recibir_dano(ficha.danio)

            # Registrar cómo deshacer el daño.
            def deshacer_dano(
                    jugador=self.jugador,
                    vida=vida_anterior,
                    vivo=vivo_anterior
            ):
                jugador.vida = vida
                jugador.vivo = vivo

            self.historial.registrar(
                deshacer=deshacer_dano,
                description=f"daño de trampa {trampa.instancia}"
            )

            print(
                f"¡Trampa activada! {ficha.nombre} Daño recibido: {ficha.danio}" )

            # Programar el rearme.
            self.programar_evento(self.reloj + intervalo,"REARMAR_TRAMPA", trampa)

    def cargar_contenido_salas(self, id_cripta, ids_salas):

        gestor = self.gestor_datos

        if gestor is None:
            raise RuntimeError("El motor no tiene un GestorDatos configurado.")

        contenidos = gestor.obtener_contenido_salas(id_cripta, ids_salas)

        if contenidos is None:
            raise RuntimeError("No se pudo cargar el contenido de las salas.")

        # Validar todas las salas antes de modificar el estado.
        for contenido in contenidos:
            sala = self.buscar_sala(self.salas, contenido.id_sala)

            if sala is None:
                raise RuntimeError(f"La sala {contenido.id_sala} no existe en el esqueleto cargado.")

        # Identificar las salas cuyo contenido ya fue cargado.
        salas_cargadas = self._salas_contenido_cargado.copy()
        objetos_por_sala = []
        enemigos_nuevos = []
        contenidos_nuevos = []

        # Convertir el contenido de las salas nuevas.
        for contenido in contenidos:
            id_sala = contenido.id_sala

            # No reconstruir objetos ni enemigos de una sala cargada.
            if id_sala in salas_cargadas:
                continue

            sala = self.buscar_sala(self.salas, id_sala)
            objetos_convertidos = []

            # Convertir los objetos del catálogo a nodos.
            for indice, tipo_id in enumerate(contenido.objetos):
                ficha = gestor.obtener_ficha(tipo_id)

                if ficha is None:
                    raise RuntimeError(f"No se encontró la ficha del objeto {tipo_id}.")

                if not hasattr(ficha, "peso") or not hasattr(ficha, "valor"):
                    raise RuntimeError(f"La ficha {tipo_id} no contiene los atributos requeridos para un objeto.")

                instancia_id = (f"obj-{id_cripta}-{id_sala}-{tipo_id}-{indice}" )

                objeto = NodoInventario(
                    instancia_id=instancia_id,
                    tipo_id=tipo_id,
                    nombre=ficha.nombre,
                    peso=ficha.peso,
                    valor=ficha.valor,
                    clase=ficha.clase,
                    ataque_bonus=getattr(
                        ficha, "ataque_bonus", 0
                    ),
                    defensa_bonus=getattr(
                        ficha, "defensa_bonus", 0
                    ),
                )

                objetos_convertidos.append(objeto)

            objetos_por_sala.append([id_sala, objetos_convertidos])

            # Construir enemigos sin duplicar sus instancias.
            for instancia in contenido.enemigos:
                id_enemigo = instancia.instancia

                existe = (any( enemigo.id == id_enemigo for enemigo in self.enemigos) or any(enemigo.id == id_enemigo for enemigo in enemigos_nuevos))

                if existe:
                    continue

                ficha = gestor.obtener_ficha(instancia.tipo)

                if ficha is None:
                    raise RuntimeError(f"No se encontró la ficha {instancia.tipo} del enemigo {id_enemigo}.")

                if ficha.clase != "enemigo":
                    raise RuntimeError(f"La ficha {instancia.tipo} no es una ficha de enemigo.")

                vida = (ficha.vida_max if instancia.vida is None else instancia.vida)

                enemigo = Enemigo(
                    id=id_enemigo,
                    vida=vida,
                    vida_max=ficha.vida_max,
                    ataque=ficha.ataque,
                    defensa=ficha.defensa,
                    velocidad=ficha.velocidad,
                    comportamiento=ficha.comportamiento,
                    sala=sala,
                    tipo_id=instancia.tipo,
                )

                # Enemigo comienza inactivo, según su constructor.
                enemigos_nuevos.append(enemigo)

            contenidos_nuevos.append(contenido)

        # Registrar los enemigos después de completar la conversión.
        self.registrar_enemigos(enemigos_nuevos)

        # Incorporar los objetos sin reemplazar los existentes.
        for id_sala, objetos in objetos_por_sala:
            entrada_existente = None

            for entrada in self.objetos_suelo:
                if entrada[0] == id_sala:
                    entrada_existente = entrada
                    break

            if entrada_existente is None:
                self.objetos_suelo.append([id_sala, objetos])
            else:
                entrada_existente[1].extend(objetos)

            if id_sala not in self._salas_contenido_cargado:
                self._salas_contenido_cargado.append(id_sala)

        # Conservar el contenido de las salas cargadas anteriormente.
        ids_existentes = [
            contenido.id_sala
            for contenido in self.contenidos_salas
        ]

        for contenido in contenidos_nuevos:
            if contenido.id_sala in ids_existentes:
                continue

            self.contenidos_salas.append(contenido)
            ids_existentes.append(contenido.id_sala)

            # Registrar el estado inicial de las trampas.
            for trampa in contenido.trampas:
                self._guardar_estado_trampa(trampa.instancia, True)
            # Marcar también las salas nuevas que no tienen objetos.
            if contenido.id_sala not in self._salas_contenido_cargado:
                self._salas_contenido_cargado.append(contenido.id_sala)

    def registrar_enemigo(self, enemigo):
        for existente in self.enemigos:
            if existente.id == enemigo.id:
                raise ValueError(f"Ya existe un enemigo con ID {enemigo.id}")

        if not hasattr(enemigo, "tipo_id"):
            enemigo.tipo_id = None

        self.enemigos.append(enemigo)

    def registrar_enemigos(self, enemigos):

        for enemigo in enemigos:
            self.registrar_enemigo(enemigo)

    def obtener_enemigos(self, sala=None, solo_vivos=False):

        resultado = []

        for enemigo in self.enemigos:
            if sala is not None and enemigo.sala != sala:
                continue

            if solo_vivos and not enemigo.esta_vivo():
                continue

            resultado.append(enemigo)

        return resultado

    def iniciar_partida(self, jugador, salas, enemigos, contenidos_salas=None):

        # Reiniciar el estado de la simulación
        self.reloj = 0
        self.secuencia = 0
        self.agenda = AgendaEventos()
        self.historial = Historial()
        self.enemigos = []
        self.objetos_suelo = []
        self.jugador = jugador
        self.salas = salas
        self._salas_contenido_cargado.clear()
        self._estado_trampas.clear()

        if jugador.sala is not None:
            jugador.sala.rastro = 0

        if contenidos_salas is not None:
            self.contenidos_salas = contenidos_salas
        else:
            self.contenidos_salas = []

        for contenido in self.contenidos_salas:
            if contenido.id_sala not in self._salas_contenido_cargado:
                self._salas_contenido_cargado.append(contenido.id_sala)

            for trampa in contenido.trampas:
                self._guardar_estado_trampa(trampa.instancia, True)

        # Registrar los enemigos
        for enemigo in enemigos:
            self.registrar_enemigo(enemigo)

        jugador.tiempo_siguiente = 0
        evento = self.programar_evento(0, "ACCION_ACTOR", jugador)
        jugador.evento_actual = evento
        self.activar_enemigos_de_sala(jugador.sala)

    def sig_secu(self):
        secuencia = self.secuencia
        self.secuencia += 1
        return secuencia

    def calcu_inter(self, costo, velocidad):
        return max(1, costo * 100 // velocidad)

    def programar_evento(self, tiempo, tipo, actor=None):

        secuencia_anterior = self.secuencia
        evento_anterior_actor = (
            getattr(actor, "evento_actual", None)
            if actor is not None else None
        )
        secuencia = self.sig_secu()
        evento = Evento(tiempo, secuencia, tipo, actor)
        self.agenda.agregar(evento)

        def deshacer():
            evento.cancelar()
            self.secuencia = secuencia_anterior

            if actor is not None:
                actor.evento_actual = evento_anterior_actor

        self.historial.registrar(
            deshacer=deshacer,
            description=f"programación de evento {tipo}"
        )

        return evento

    def proxima_accion(self, actor, costo=100):

        tiempo_anterior = actor.tiempo_siguiente
        intervalo = self.calcu_inter(costo, actor.velocidad)
        actor.tiempo_siguiente = self.reloj + intervalo

        evento = self.programar_evento(actor.tiempo_siguiente,"ACCION_ACTOR",actor )
        actor.evento_actual = evento

        self.historial.registrar(
            deshacer=lambda: setattr(
                actor, "tiempo_siguiente", tiempo_anterior
            ),
            description=f"restaurar tiempo siguiente de {actor.id}"
        )

        return evento

    def ejecu_sig_evento(self):
        reloj_anterior = self.reloj
        estado_azar_anterior = self.azar.getstate()

        evento = self.agenda.extraer()

        if evento is None:
            return False

        cancelado_anterior = evento.cancelado

        def deshacer():
            self.reloj = reloj_anterior
            self.azar.setstate(estado_azar_anterior)

            if not self.agenda.contiene(evento):
                self.agenda.agregar(evento)

            evento.cancelado = cancelado_anterior

        self.historial.registrar(
            deshacer=deshacer,
            description=f"ejecución de evento {evento.tipo}"
        )

        self.reloj = evento.tiempo
        self.ejecutar_evento(evento)
        return True

    def avanzar_hasta_jugador(self):

        jugador = self.jugador

        if jugador is None or not jugador.esta_vivo():
            return False

        while not self.agenda.esta_vacia():
            evento = self.agenda.siguiente()

            if evento is None:
                return False

            if evento.actor is jugador:
                evento = self.agenda.extraer()

                if evento is None:
                    return False

                if evento.cancelado:
                    continue

                reloj_anterior = self.reloj
                cancelado_anterior = evento.cancelado

                def deshacer_turno_jugador():
                    self.reloj = reloj_anterior

                    if not self.agenda.contiene(evento):
                        self.agenda.agregar(evento)

                    evento.cancelado = cancelado_anterior

                self.reloj = evento.tiempo

                self.historial.registrar(
                    deshacer=deshacer_turno_jugador,
                    description="restaurar turno del jugador y reloj"
                )

                return True

            if not self.ejecu_sig_evento():
                return False

            if not jugador.esta_vivo():
                return False

        return False

    def ejecutar_evento(self, evento):

        actor = evento.actor
        if evento.tipo == "REARMAR_TRAMPA":
            if actor is not None:
                self.cambiar_estado_trampa_reversible(actor, True)
                print(f"Trampa {actor.instancia} rearmada.")
            return

        if actor is not None and hasattr(actor, "esta_vivo"):
            if not actor.esta_vivo():
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

                elif accion == "MOVER_RASTRO":
                    salida = self.salida_rastro(actor)

                    if salida is None:
                        print("El rastreador no encuentra rastros recientes")
                    else:
                        movio = self.mover_enemigo(actor, self.salas, salida)

                        if movio:
                            print("Rastreador movido a sala:", actor.sala.id)
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

    def activar_enemigos_de_sala(self, sala):

        enemigos = self.obtener_enemigos(sala=sala,solo_vivos=True)
        self.activar_enemigos(enemigos)

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

    def salida_rastro(self, enemigo):

        # Elige vecino accesible con rastro más reciente (<400 unidades).

        mejor = None
        mejor_tiempo = None

        for direccion, salida in self.salidas_abiertas(enemigo.sala):

            destino = self.buscar_sala(self.salas, salida.sala_destino)

            if destino is None:
                continue

            rastro = getattr(destino, "rastro", None)
            if rastro is None:
                continue

            if self.reloj - rastro >= 400:
                continue

            if (mejor is None or rastro > mejor_tiempo or(rastro == mejor_tiempo and destino.id < mejor[1].sala_destino)):
                mejor = (direccion, salida)
                mejor_tiempo = rastro
        return mejor[1] if mejor is not None else None

    def buscar_sala(self,salas, id_sala):
        for sala in salas:
            if sala.id == id_sala:
                return sala
        return None

    def atacar(self, atacante, defensor):

        estado_azar_anterior = self.azar.getstate()

        # Obtener la bonificación de ataque del arma equipada.
        bono_ataque = 0
        inventario_atacante = getattr(atacante, "inventario", None)

        if inventario_atacante is not None:
            arma = inventario_atacante.arma_equipada()

            if arma is not None:
                bono_ataque = arma.ataque_bonus

        # Obtener la bonificación de defensa de la armadura equipada.
        bono_defensa = 0
        inventario_defensor = getattr(defensor, "inventario", None)

        if inventario_defensor is not None:
            armadura = inventario_defensor.armadura_equipada()

            if armadura is not None:
                bono_defensa = armadura.defensa_bonus

        # Calcular el daño.
        azar = self.azar.randint(0, 4)

        dano = max(1,(atacante.ataque + bono_ataque)+ azar - (defensor.defensa + bono_defensa) )

        # Guardar el estado anterior del defensor.
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

        print("Ataque:", atacante.id, "->", defensor.id)
        print("Daño:", dano)
        print("Vida de", defensor.id, ":", defensor.vida)

        if not defensor.esta_vivo():
            print("Actor", defensor.id, "ha muerto")

            # Cancelar el evento futuro del actor muerto.
            evento_anterior = defensor.evento_actual

            if evento_anterior is not None:
                cancelado_anterior = evento_anterior.cancelado
                evento_anterior.cancelar()

                def deshacer_muerte():
                    evento_anterior.cancelado = cancelado_anterior

                self.historial.registrar(
                    deshacer=deshacer_muerte,
                    description=f"cancelación de evento de {defensor.id}"
                )

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

        salida = jugador.sala.salidas.get(direccion)

        if salida is None or salida.cerrada:
            print("No existe una salida abierta en esa dirección.")
            return False

        sala_destino = self.buscar_sala(
            self.salas, salida.sala_destino
        )

        if sala_destino is None:
            print("No se encontró la sala destino.")
            return False

        sala_anterior = jugador.sala

        # Abrir el intervalo antes de cambiar el estado.
        self.accion_jugador()

        jugador.sala = sala_destino

        # Registrar primero el movimiento, incluso si una trampa mata.
        self.historial.registrar(
            deshacer=lambda: setattr(jugador, "sala", sala_anterior),
            description="movimiento del jugador"
        )

        self.actualizar_rastro(sala_destino)

        # Las trampas se activan al entrar, antes de avanzar el reloj.
        self.activar_trampas_de_sala(sala_destino)

        if not jugador.esta_vivo():
            return True

        self.activar_enemigos_de_sala(sala_destino)
        self.proxima_accion(jugador, costo=100)
        self.avanzar_hasta_jugador()

        return True

    def actualizar_rastro(self, sala):
        # Actualiza el rastro de una sala y permite deshacer el cambio

        if sala is None:
            return

        tenia_rastro = hasattr(sala, "rastro")
        rastro_anterior = getattr(sala, "rastro", None)

        sala.rastro = self.reloj

        def deshacer_rastro():
            if tenia_rastro:
                sala.rastro = rastro_anterior
            elif hasattr(sala, "rastro"):
                delattr(sala, "rastro")

        self.historial.registrar(
            deshacer=deshacer_rastro,
            description=f"actualización del rastro de sala {sala.id}"
        )

    def obtener_objetos_suelo(self, sala):
        # Devuelve los objetos que están en el suelo de una sala.
        if sala is None:
            return []

        for entrada in self.objetos_suelo:
            if entrada[0] == sala.id:
                return entrada[1]

        return []

    def recoger_objeto(self, nodo):

        jugador = self.jugador

        if jugador is None or jugador.sala is None:
            return False

        inventario = jugador.inventario

        if inventario.lleno():
            return False

        objetos = self.obtener_objetos_suelo(jugador.sala)

        if not any(objeto is nodo for objeto in objetos):
            return False

        self.accion_jugador()
        objetos.remove(nodo)

        exito = recoger_reversible(inventario, nodo, self.historial)

        if not exito:
            objetos.append(nodo)
            return False

        self.historial.registrar(
            deshacer=lambda: objetos.append(nodo),
            description=f"retirar {nodo.nombre} del suelo"
        )
        self.actualizar_rastro(jugador.sala)
        self.proxima_accion(jugador, costo=25)
        self.avanzar_hasta_jugador()

        return True

    def soltar_objeto(self):
        jugador = self.jugador

        if jugador is None or jugador.sala is None:
            return None

        inventario = jugador.inventario
        nodo = inventario.actual()

        if nodo is None:
            return None

        # Buscar la lista real de objetos de esta sala.
        entrada_suelo = None

        for entrada in self.objetos_suelo:
            if entrada[0] == jugador.sala.id:
                entrada_suelo = entrada
                break

        # Si la sala no tiene una lista registrada, crearla.
        lista_nueva = entrada_suelo is None

        if lista_nueva:
            objetos = []
            entrada_suelo = [jugador.sala.id, objetos]
        else:
            objetos = entrada_suelo[1]

        self.accion_jugador()

        resultado = soltar_reversible(inventario, nodo, self.historial)

        if resultado is None:
            return None

        if lista_nueva:
            self.objetos_suelo.append(entrada_suelo)

        objetos.append(resultado)

        def deshacer_soltar():
            if resultado in objetos:
                objetos.remove(resultado)

            # Si la lista se creó con esta acción, eliminarla al retroceder.
            if lista_nueva and entrada_suelo in self.objetos_suelo:
                self.objetos_suelo.remove(entrada_suelo)

        self.historial.registrar(
            deshacer=deshacer_soltar,
            description=f"objeto soltado en sala {jugador.sala.id}"
        )

        self.actualizar_rastro(jugador.sala)
        self.proxima_accion(jugador, costo=25)
        self.avanzar_hasta_jugador()

        return resultado

    def equipar_objeto(self):
        jugador = self.jugador

        if jugador is None:
            return None

        nodo = jugador.inventario.actual()

        if nodo is None or nodo.clase not in ("arma", "armadura"):
            return None

        self.accion_jugador()

        resultado = equipar_reversible(jugador.inventario, self.historial )

        if resultado is None:
            return None

        self.actualizar_rastro(jugador.sala)
        self.proxima_accion(jugador, costo=50)
        self.avanzar_hasta_jugador()

        return resultado

    def usar_pergamino_retroceso(self, nodo_pergamino):
        if self.jugador is None:
            return False

        return usar_pergamino(self.jugador.inventario,self.historial,nodo_pergamino)

    def es_ficha_activa(self, id_ficha):
        # Revisar fichas de enemigos vivos.
        for enemigo in self.enemigos:
            if enemigo.esta_vivo() and enemigo.tipo_id == id_ficha:
                return True

        # Revisar fichas de objetos del inventario del jugador.
        if self.jugador is not None:
            for objeto in self.jugador.inventario:
                if objeto.tipo_id == id_ficha:
                    return True

        # Revisar objetos que están en el suelo.
        for entrada in self.objetos_suelo:
            objetos = entrada[1]

            for objeto in objetos:
                if objeto.tipo_id == id_ficha:
                    return True


        # Revisar las trampas únicamente en la sala actual.
        if self.jugador is not None and self.jugador.sala is not None:
            id_sala_actual = self.jugador.sala.id

            for contenido in self.contenidos_salas:
                if contenido.id_sala != id_sala_actual:
                    continue

                for trampa in contenido.trampas:
                    if trampa.tipo == id_ficha:
                        return True

        return False

    def ejecutar_accion(self, nombre, argumento=""):

        # Contrato estable para replay. False significa acción rechazada
        # Acciones: mover(N/S/E/O), esperar, atacar(id_enemigo), recoger(id_objeto),soltar(id_objeto_actual) y equipar(id_objeto_actual)


        if self.jugador is None or not self.jugador.esta_vivo():
            return False

        if nombre == "mover":
            return self.mover_jugador(str(argumento).upper())

        if nombre == "esperar":
            self.accion_jugador()
            self.actualizar_rastro(self.jugador.sala)
            self.proxima_accion(self.jugador, costo=100)
            return self.avanzar_hasta_jugador()

        if nombre == "atacar":
            enemigo = next((e for e in self.enemigos
                         if str(e.id) == str(argumento)), None)

            if (enemigo is None or not enemigo.esta_vivo() or enemigo.sala != self.jugador.sala):
                return False

            self.accion_jugador()
            self.atacar(self.jugador, enemigo)
            self.actualizar_rastro(self.jugador.sala)
            self.proxima_accion(self.jugador, costo=100)
            self.avanzar_hasta_jugador()
            return True

        if nombre in ("recoger", "soltar", "equipar"):
            inventario = self.jugador.inventario
            objeto_id = str(argumento)

            if nombre == "recoger":
                nodo = next((o for o in self.obtener_objetos_suelo(self.jugador.sala)
                             if str(o.instancia_id) == objeto_id), None)
                return self.recoger_objeto(nodo) if nodo is not None else False

            # Inventario no ofrece búsqueda por ID; se recorre usando su API pública
            # y se restaura el cursor original al terminar la búsqueda.
            cursor_original = inventario.actual()
            encontrado = None
            recorrido = []
            nodo = cursor_original

            while nodo is not None and nodo not in recorrido:

                recorrido.append(nodo)
                if str(nodo.instancia_id) == objeto_id:
                    encontrado = nodo
                    break
                nodo = nodo.siguiente

            if encontrado is None:

                nodo = cursor_original.anterior if cursor_original is not None else None
                while nodo is not None and nodo not in recorrido:
                    recorrido.append(nodo)
                    if str(nodo.instancia_id) == objeto_id:
                        encontrado = nodo
                        break
                    nodo = nodo.anterior

            if encontrado is None:
                return False

            # La operación existente  actúa sobre el cursor actual, solo se acepta el objeto señalado actualmente para no alterar su estructura

            if encontrado is not cursor_original:
                return False

            if nombre == "soltar":
                return self.soltar_objeto() is not None

            return self.equipar_objeto() is not None

        return False

    def obtener_estado_resumen(self):
        # Estado determinista mínimo para comparar pruebas/replay
        return {
            "reloj": self.reloj,
            "secuencia": self.secuencia,
            "jugador": None if self.jugador is None else {
                "id": self.jugador.id,
                "vida": self.jugador.vida,
                "sala": None if self.jugador.sala is None else self.jugador.sala.id,
                "inventario": [o.instancia_id for o in self.jugador.inventario],
            },
            "enemigos": [
                (e.id, e.vida, e.vivo,
                 None if e.sala is None else e.sala.id,
                 e.tiempo_siguiente, e.activo)
                for e in sorted(self.enemigos, key=lambda x: str(x.id)) # se usa para presentar los enemigos en un orden estable al comparar pruebas.
            ],

            "eventos": sorted(
                (
                    ev.tiempo,
                    ev.secuencia,
                    ev.tipo,
                    None if ev.actor is None else getattr(ev.actor, "id", None),
                    ev.cancelado
                )
                for ev in self.agenda.heap
            ),

            "azar": self.azar.getstate(),
        }

