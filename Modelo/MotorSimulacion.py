import random
from Modelo.Evento import Evento
from Modelo.RegistroMensajes import RegistroMensajes
from Modelo.AgendaEventos import AgendaEventos
from Modelo.Enemigo import Enemigo
from Modelo.Inventario import NodoInventario
from Modelo.ordenamiento import elegir_algoritmo
from Modelo.retroceso import (Historial, recoger_reversible, soltar_reversible, equipar_reversible, usar_pergamino)

TIPOS_EFECTO = ("VENENO", "REGENERAR", "FIN_VELOCIDAD", "APAGAR_ANTORCHA")
INTERVALO_VENENO = 80
DURACION_VENENO = 400
INTERVALO_REGENERACION = 200
COSTO_USAR = 50


class MotorSimulacion:

    def __init__(self, semilla=None, gestor_datos=None):
        self.reloj = 0
        self.secuencia = 0
        self.agenda = AgendaEventos()
        self.azar = random.Random(semilla)
        self.semilla = semilla
        self.salas = []
        self.jugador = None
        self.enemigos = []
        self.historial = Historial()
        self.contenidos_salas = []
        self.objetos_suelo = []
        self._salas_contenido_cargado = []
        self._estado_trampas = []
        self.cripta_id = None
        self.mensajes = RegistroMensajes()
        self.eco = False
        self.acciones_jugador = 0
        self.enemigos_derrotados = 0
        self.sala_salida = None
        self.llave_salida = None
        self._llave_salida_usada = False
        self.victoria = False
        self._indice_salas = []  # salas ordenadas por id (búsqueda binaria)
        self._indice_origen = None
        # Una única instancia del gestor para este motor.
        self.gestor_datos = gestor_datos
        self.restaurador = None

        if self.gestor_datos is not None:
            self.gestor_datos.conectar_estado_juego(self)

    def _mensaje(self, texto):
        sobreescribio, anterior= self.mensajes.agregar(texto)

        self.historial.registrar(
            deshacer=lambda: self.mensajes.deshacer_ultimo(sobreescribio,anterior),
            description="mensaje agregado")

        if self.eco:
            print(texto)

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
                raise RuntimeError(f"No se encontró una ficha válida para la trampa: {trampa.tipo}")

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

            self._mensaje(f"¡Trampa activada! {ficha.nombre}: {ficha.danio} de daño.")

            # Programar el rearme.
            self.programar_evento(self.reloj + intervalo, "REARMAR_TRAMPA", trampa)

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
                instancia_id = (f"obj-{id_cripta}-{id_sala}-{tipo_id}-{indice}")
                objetos_convertidos.append(self.crear_objeto(instancia_id, tipo_id))

            objetos_por_sala.append([id_sala, objetos_convertidos])

            # Construir enemigos sin duplicar sus instancias.
            for instancia in contenido.enemigos:
                id_enemigo = instancia.instancia

                existe = (any(enemigo.id == id_enemigo for enemigo in self.enemigos) or any(
                    enemigo.id == id_enemigo for enemigo in enemigos_nuevos))

                if existe:
                    continue

                # Enemigo comienza inactivo, según su constructor.
                enemigos_nuevos.append( self.crear_enemigo(id_enemigo, instancia.tipo, instancia.vida, sala))

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

    def crear_objeto(self, instancia_id, tipo_id):
        # Construye el nodo de un objeto a partir de su ficha del catálogo.
        # Lo usan la carga desde la API y la carga de una partida guardada.
        ficha = self.gestor_datos.obtener_ficha(tipo_id)

        if ficha is None:
            raise RuntimeError(f"No se encontró la ficha del objeto {tipo_id}.")

        if not hasattr(ficha, "peso") or not hasattr(ficha, "valor"):
            raise RuntimeError(f"La ficha {tipo_id} no contiene los atributos requeridos para un objeto.")

        return NodoInventario(
            instancia_id=instancia_id,
            tipo_id=tipo_id,
            nombre=ficha.nombre,
            peso=ficha.peso,
            valor=ficha.valor,
            clase=ficha.clase,
            ataque_bonus=getattr(ficha, "ataque_bonus", 0),
            defensa_bonus=getattr(ficha, "defensa_bonus", 0),
        )

    def crear_enemigo(self, id_enemigo, tipo_id, vida, sala):
        # Construye un enemigo (inactivo) con su botín. vida=None usa vida_max.
        ficha = self.gestor_datos.obtener_ficha(tipo_id)

        if ficha is None:
            raise RuntimeError(f"No se encontró la ficha {tipo_id} del enemigo {id_enemigo}.")

        if ficha.clase != "enemigo":
            raise RuntimeError(f"La ficha {tipo_id} no es una ficha de enemigo.")

        enemigo = Enemigo(
            id=id_enemigo,
            vida=ficha.vida_max if vida is None else vida,
            vida_max=ficha.vida_max,
            ataque=ficha.ataque,
            defensa=ficha.defensa,
            velocidad=ficha.velocidad,
            comportamiento=ficha.comportamiento,
            sala=sala,
            tipo_id=tipo_id,
        )

        enemigo.regeneracion = getattr(ficha, "regeneracion", 0) or 0
        enemigo.botin = []

        for k, tipo_botin in enumerate(getattr(ficha, "suelta", None) or []):
            enemigo.botin.append(
                self.crear_objeto(f"bot-{id_enemigo}-{k}-{tipo_botin}", tipo_botin)
            )

        return enemigo

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

    def iniciar_partida(self, jugador, salas, enemigos, contenidos_salas=None,
                        sala_salida=None, llave_salida=None, cripta_id=None):

        # Reiniciar el estado de la simulación
        self.reloj = 0
        self.secuencia = 0
        self.agenda = AgendaEventos()
        self.historial = Historial()
        self.mensajes = RegistroMensajes()
        self.enemigos = []
        self.objetos_suelo = []
        self.jugador = jugador
        self.salas = salas
        self._salas_contenido_cargado.clear()
        self._estado_trampas.clear()
        self.acciones_jugador = 0
        self.enemigos_derrotados = 0
        self.sala_salida = sala_salida
        self.llave_salida = llave_salida
        if cripta_id is not None:
            self.cripta_id = cripta_id
        self._llave_salida_usada = False
        self.victoria = False
        self._indice_origen = None

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

        # Deja al jugador en su primer punto de decisión (reloj 0).
        self.avanzar_hasta_jugador()

    def sig_secu(self):
        secuencia = self.secuencia
        self.secuencia += 1
        return secuencia

    def calcu_inter(self, costo, velocidad):
        return max(1, costo * 100 // velocidad)

    def programar_evento(self, tiempo, tipo, actor=None, datos=None):

        secuencia_anterior = self.secuencia
        evento_anterior_actor = (
            getattr(actor, "evento_actual", None)
            if actor is not None else None
        )
        secuencia = self.sig_secu()
        evento = Evento(tiempo, secuencia, tipo, actor, datos)
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

    def _contar_accion(self):
        self._asignar_reversible(self, "acciones_jugador", self.acciones_jugador + 1)

    def proxima_accion(self, actor, costo=100):

        tiempo_anterior = actor.tiempo_siguiente
        intervalo = self.calcu_inter(costo, actor.velocidad)
        actor.tiempo_siguiente = self.reloj + intervalo

        evento = self.programar_evento(actor.tiempo_siguiente, "ACCION_ACTOR", actor)
        actor.evento_actual = evento

        if actor is self.jugador:
            self._contar_accion()

        self.historial.registrar(
            deshacer=lambda: setattr(
                actor, "tiempo_siguiente", tiempo_anterior
            ),
            description=f"restaurar tiempo siguiente de {actor.id}"
        )

        return evento

    def ejecu_sig_evento(self):
        reloj_anterior = self.reloj

        evento = self.agenda.extraer()

        if evento is None:
            return False

        cancelado_anterior = evento.cancelado

        def deshacer():
            self.reloj = reloj_anterior

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

        if jugador is None or not jugador.esta_vivo() or self.victoria:
            return False

        while not self.agenda.esta_vacia():
            evento = self.agenda.siguiente()

            if evento is None:
                return False

            if evento.actor is jugador and evento.tipo == "ACCION_ACTOR":
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

        if evento.tipo == "CERRAR_PUERTA":
            # actor es la Salida; si ya está cerrada no hay nada que hacer.
            if actor is not None and not actor.cerrada:
                actor.cerrada = True
                self.historial.registrar(
                    deshacer=lambda: setattr(actor, "cerrada", False),
                    description="cierre automático de puerta"
                )
                self._mensaje("Una puerta se cerró sola.")
            return

        if evento.tipo in TIPOS_EFECTO:
            self._ejecutar_efecto(evento)
            return

        if evento.tipo == "REARMAR_TRAMPA":
            if actor is not None:
                self.cambiar_estado_trampa_reversible(actor, True)
                self._mensaje(f"La trampa {actor.instancia} se rearmó.")
            return

        if actor is not None and hasattr(actor, "esta_vivo"):
            if not actor.esta_vivo():
                return

        if isinstance(actor, Enemigo):
            accion = self.accion_enemigo(actor, self.jugador)

            if accion == "MOVER":
                resultado = self.salida_errante(actor)

                if resultado is not None:
                    self.mover_enemigo(actor, self.salas, resultado[1])

            elif accion == "MOVER_RASTRO":
                salida = self.salida_rastro(actor)

                if salida is not None:
                    self.mover_enemigo(actor, self.salas, salida)

            elif accion == "ATACAR":
                self.atacar(actor, self.jugador)

            # ESPERAR no hace nada: solo se reprograma la siguiente acción.

            if actor.esta_vivo():  # un actor muerto no ejecuta más eventos
                self.proxima_accion(actor, 100)

    def cambiar_velocidad(self, actor, nueva_velocidad):

        nueva_velocidad = max(1, nueva_velocidad)
        velocidad_anterior = actor.velocidad
        evento_previo = actor.evento_actual

        actor.velocidad = nueva_velocidad

        if (evento_previo is None or evento_previo.cancelado
                or not self.agenda.contiene(evento_previo)):
            return None

        tiempo_restante = actor.tiempo_siguiente - self.reloj
        restante_nuevo = max(1, (tiempo_restante * velocidad_anterior) // nueva_velocidad)

        evento_previo.cancelar()

        nuevo_tiempo = self.reloj + restante_nuevo
        actor.tiempo_siguiente = nuevo_tiempo
        evento = self.programar_evento(nuevo_tiempo, "ACCION_ACTOR", actor)
        actor.evento_actual = evento

        return evento

    def cambiar_velocidad_reversible(self, actor, nueva_velocidad):
        velocidad_anterior = actor.velocidad
        tiempo_anterior = actor.tiempo_siguiente
        evento_anterior = actor.evento_actual
        cancelado_anterior = (
            evento_anterior.cancelado if evento_anterior is not None else None
        )

        evento_nuevo = self.cambiar_velocidad(actor, nueva_velocidad)

        def deshacer():
            if evento_nuevo is not None:
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



    def _asignar_reversible(self, objeto, nombre, valor):
        anterior = getattr(objeto, nombre, None)
        setattr(objeto, nombre, valor)
        self.historial.registrar(
            deshacer=lambda: setattr(objeto, nombre, anterior),
            description=f"{nombre} de {getattr(objeto, 'id', objeto)}"
        )

    def _cancelar_evento_reversible(self, evento):
        if evento is None or evento.cancelado:
            return

        evento.cancelar()

        def deshacer():
            evento.cancelado = False

        self.historial.registrar(deshacer=deshacer,
                                 description=f"cancelación de {evento.tipo}")

    def _aplicar_dano_reversible(self, actor, dano):
        vida_anterior = actor.vida
        vivo_anterior = actor.vivo

        actor.recibir_dano(dano)

        def deshacer():
            actor.vida = vida_anterior
            actor.vivo = vivo_anterior

        self.historial.registrar(deshacer=deshacer,
                                 description=f"daño directo a {actor.id}")

        if not actor.esta_vivo():
            self._al_morir(actor)

    def _curar_reversible(self, actor, cantidad):
        vida_anterior = actor.vida
        actor.vida = min(actor.vida_max, actor.vida + cantidad)

        def deshacer():
            actor.vida = vida_anterior

        self.historial.registrar(deshacer=deshacer,
                                 description=f"curación de {actor.id}")

    def _al_morir(self, actor):
        # Un actor muerto deja de ejecutar eventos: se cancelan su acción
        # pendiente y sus efectos activos sin recorrer la agenda.
        self._mensaje(f"{actor.id} ha muerto.")
        if isinstance(actor, Enemigo):
            self._asignar_reversible(self, "enemigos_derrotados", self.enemigos_derrotados + 1)
            self._soltar_botin(actor)
        self._cancelar_evento_reversible(actor.evento_actual)
        self._cancelar_evento_reversible(getattr(actor, "veneno", None))
        self._cancelar_evento_reversible(getattr(actor, "evento_regen", None))

    def _soltar_botin(self, enemigo):
        # Los objetos de `suelta` ya se convirtieron en nodos al cargar el
        # contenido; al morir pasan al suelo de la sala del enemigo.
        botin = getattr(enemigo, "botin", None)

        if not botin or enemigo.sala is None:
            return

        entrada = None
        for existente in self.objetos_suelo:
            if existente[0] == enemigo.sala.id:
                entrada = existente
                break

        creada = entrada is None
        if creada:
            entrada = [enemigo.sala.id, []]
            self.objetos_suelo.append(entrada)

        objetos = entrada[1]
        objetos.extend(botin)
        soltados = list(botin)
        self._asignar_reversible(enemigo, "botin", [])

        def deshacer():
            for nodo in soltados:
                if nodo in objetos:
                    objetos.remove(nodo)
            if creada and entrada in self.objetos_suelo:
                self.objetos_suelo.remove(entrada)

        self.historial.registrar(deshacer=deshacer,
                                 description=f"botín de {enemigo.id}")

    def aplicar_veneno(self, actor, dano):
        # Daño cada 80 unidades durante 400. Reaplicarlo reinicia la duración.
        if actor is None or not actor.esta_vivo() or dano <= 0:
            return None

        self._cancelar_evento_reversible(getattr(actor, "veneno", None))

        fin = self.reloj + DURACION_VENENO
        evento = self.programar_evento(
            self.reloj + INTERVALO_VENENO, "VENENO", actor, (dano, fin)
        )
        self._asignar_reversible(actor, "veneno", evento)
        return evento

    def cancelar_veneno(self, actor):
        veneno = getattr(actor, "veneno", None)

        if veneno is None or veneno.cancelado:
            return False

        self._cancelar_evento_reversible(veneno)
        self._asignar_reversible(actor, "veneno", None)
        return True

    def _velocidad_con_modificador(self, base, modificador):
        # Un solo punto donde se define cómo actúa modificador_velocidad.
        return max(1, base + modificador)

    def aplicar_velocidad_temporal(self, actor, modificador, duracion):
        nueva = self._velocidad_con_modificador(actor.velocidad, modificador)
        delta = nueva - actor.velocidad

        self.cambiar_velocidad_reversible(actor, nueva)
        self.programar_evento(self.reloj + duracion, "FIN_VELOCIDAD", actor, delta)

    def _programar_regeneracion(self, enemigo):
        if not getattr(enemigo, "regeneracion", 0):
            return

        evento = self.programar_evento(
            self.reloj + INTERVALO_REGENERACION, "REGENERAR", enemigo
        )
        self._asignar_reversible(enemigo, "evento_regen", evento)

    def _ejecutar_efecto(self, evento):
        actor = evento.actor

        if actor is None or not actor.esta_vivo():
            return

        if evento.tipo == "VENENO":
            dano, fin = evento.datos
            self._mensaje(f"El veneno inflige {dano} de daño a {actor.id}.")
            self._aplicar_dano_reversible(actor, dano)

            if not actor.esta_vivo():
                return

            siguiente = self.reloj + INTERVALO_VENENO

            if siguiente <= fin:
                nuevo = self.programar_evento(siguiente, "VENENO", actor, (dano, fin))
                self._asignar_reversible(actor, "veneno", nuevo)
            else:
                self._asignar_reversible(actor, "veneno", None)

        elif evento.tipo == "REGENERAR":
            self._curar_reversible(actor, actor.regeneracion)
            self._programar_regeneracion(actor)

        elif evento.tipo == "FIN_VELOCIDAD":
            self.cambiar_velocidad_reversible(actor, actor.velocidad - evento.datos)

        elif evento.tipo == "APAGAR_ANTORCHA":
            self._asignar_reversible(actor, "antorcha_encendida", False)

    def activar_enemigo(self, enemigo):
        if enemigo.activo:
            return
        self._asignar_reversible(enemigo, "activo", True)
        self.proxima_accion(enemigo, 100)
        self._programar_regeneracion(enemigo)

    def activar_enemigos_de_sala(self, sala):

        enemigos = self.obtener_enemigos(sala=sala, solo_vivos=True)
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

        # El estado del azar se guarda una sola vez por acción del jugador
        # (ver accion_jugador), no en cada movimiento.
        return self.azar.choice(salidas)

    def mover_enemigo(self, enemigo, salas, salida):

        sala_destino = self._destino(salida)

        if sala_destino is None:
            return False

        sala_anterior = enemigo.sala
        enemigo.sala = sala_destino

        self.historial.registrar(
            deshacer=lambda:
            setattr(enemigo, "sala", sala_anterior),
            description=f"movimiento de {enemigo.id}"
        )

        jugador = self.jugador
        if jugador is not None:
            if sala_destino is jugador.sala:
                self._mensaje(f"{enemigo.id} entra a la sala.")
            elif sala_anterior is jugador.sala:
                self._mensaje(f"{enemigo.id} sale de la sala.")

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

            destino = self._destino(salida)

            if destino is None:
                continue

            rastro = getattr(destino, "rastro", None)
            if rastro is None:
                continue

            if self.reloj - rastro >= 400:
                continue

            if (mejor is None or rastro > mejor_tiempo or (
                    rastro == mejor_tiempo and destino.id < mejor[1].sala_destino)):
                mejor = (direccion, salida)
                mejor_tiempo = rastro
        return mejor[1] if mejor is not None else None

    def _reconstruir_indice_salas(self):
        # Índice propio: salas ordenadas por id con el ordenamiento del proyecto.
        # Búsqueda binaria O(log n) en vez de recorrer todas las salas.
        algoritmo = elegir_algoritmo(len(self.salas))
        self._indice_salas, _ = algoritmo(self.salas, lambda s: s.id)
        self._indice_origen = self.salas

    def buscar_sala(self, salas, id_sala):
        if salas is not self.salas:
            for sala in salas:
                if sala.id == id_sala:
                    return sala
            return None

        if (self._indice_origen is not self.salas
                or len(self._indice_salas) != len(self.salas)):
            self._reconstruir_indice_salas()

        indice = self._indice_salas
        ini, fin = 0, len(indice)

        while ini < fin:
            medio = (ini + fin) // 2
            if indice[medio].id < id_sala:
                ini = medio + 1
            else:
                fin = medio

        if ini < len(indice) and indice[ini].id == id_sala:
            return indice[ini]

        return None

    def _destino(self, salida):
        # La sala destino se resuelve una vez y queda en la salida:
        # decidir un movimiento cuesta O(salidas), no O(salas).
        destino = getattr(salida, "_destino", None)

        if destino is None:
            destino = self.buscar_sala(self.salas, salida.sala_destino)
            if destino is not None:
                salida._destino = destino

        return destino

    def atacar(self, atacante, defensor):

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

        dano = max(1, (atacante.ataque + bono_ataque) + azar - (defensor.defensa + bono_defensa))

        # Guardar el estado anterior del defensor.
        vida_anterior = defensor.vida
        vivo_anterior = defensor.vivo

        defensor.recibir_dano(dano)

        def deshacer():
            defensor.vida = vida_anterior
            defensor.vivo = vivo_anterior

        self.historial.registrar(
            deshacer=deshacer,
            description=f"daño de {atacante.id} a {defensor.id}"
        )

        self._mensaje(
            f"{atacante.id} ataca a {defensor.id}: {dano} de daño "
            f"(vida {defensor.vida})."
        )

        if not defensor.esta_vivo():
            self._al_morir(defensor)

        return dano

    def accion_jugador(self):
        if self.jugador is None:
            return False

        self.historial.abrir_intervalo()

        # Copiar el estado del azar es caro (625 enteros). Se copia una sola vez
        # al abrir el intervalo: al retroceder, este cambio se deshace al final
        # y deja el azar exactamente como estaba antes de la acción.
        estado_azar = self.azar.getstate()
        self.historial.registrar(
            deshacer=lambda: self.azar.setstate(estado_azar),
            description="estado del azar al inicio de la acción"
        )
        return True
    
    def preparar_sala(self, sala):
        # Trae y carga el contenido de una sala. La espera de red no modifica
        # el reloj virtual. Sin gestor o sin cripta_id no hace nada.
        # En una partida cargada, la sala se toma del archivo si está guardada ahí.

        if self.restaurador is not None and self.restaurador.restaurar_sala(self, sala.id):
            return

        if self.gestor_datos is None or self.cripta_id is None:
            return

        if hasattr(self.gestor_datos, "asegurar_sala"):
            contenido = self.gestor_datos.asegurar_sala(sala.id)

            if contenido is None:
                raise RuntimeError(f"No se pudo cargar el contenido de la sala {sala.id}")

        self.cargar_contenido_salas(self.cripta_id, [sala.id])

    def contenido_disponible(self, id_sala):
        if id_sala in self._salas_contenido_cargado:
            return True

        return any(c.id_sala == id_sala for c in self.contenidos_salas)

    def estado_partida(self):
        if self.jugador is not None and not self.jugador.esta_vivo():
            return "derrota"
        if self.victoria:
            return "victoria"
        return "en_curso"

    def resumen_puntaje(self):
        return {
            "resultado": self.estado_partida(),
            "acciones": self.acciones_jugador,
            "enemigos_derrotados": self.enemigos_derrotados,
            "tiempo_final": self.reloj,
        }

    def mover_jugador(self, direccion):
        jugador = self.jugador

        if jugador is None or jugador.sala is None:
            return False

        salida = jugador.sala.salidas.get(direccion)

        if salida is None or salida.cerrada:
            self._mensaje(f"No hay una salida abierta hacia {direccion}.")
            return False

        sala_destino = self._destino(salida)

        if sala_destino is None:
            self._mensaje("No se encontró la sala destino.")
            return False

        # §2.4/§4.2: el contenido se prepara antes de cambiar jugador.sala; si la
        # carga falla, el movimiento no se confirma.
        if not self.contenido_disponible(sala_destino.id):
            try:
                self.preparar_sala(sala_destino)
            except (RuntimeError, ValueError) as error:
                self._mensaje(f"No se pudo cargar la sala destino: {error}")
                return False

        # Nunca se confirma un movimiento sin el contenido destino.
        if not self.contenido_disponible(sala_destino.id):
            self._mensaje("El contenido de esa sala aún no está disponible.")
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

        # Victoria: entrar a la sala de salida tras abrir su puerta con la llave.
        if (self.sala_salida is not None and sala_destino.id == self.sala_salida
                and (self.llave_salida is None or self._llave_salida_usada)):
            self.victoria = True
            self._contar_accion()
            return True

        self.activar_enemigos_de_sala(sala_destino)
        self.proxima_accion(jugador, costo=100)
        self.avanzar_hasta_jugador()

        return True

    def _jugador_tiene_llave(self, llave):
        # Sin llave requerida, la puerta se abre libremente.
        if llave is None:
            return True

        for objeto in self.jugador.inventario:
            if objeto.clase != "llave":
                continue

            if objeto.tipo_id == llave:
                return True

        return False

    def abrir_salida(self, direccion):
        jugador = self.jugador

        if jugador is None or jugador.sala is None:
            return False

        salida = jugador.sala.salidas.get(direccion)

        # Solo se puede abrir una salida que existe y está cerrada.
        if salida is None or not salida.cerrada:
            return False

        if not self._jugador_tiene_llave(getattr(salida, "llave", None)):
            self._mensaje("Necesitas la llave para abrir esta puerta.")
            return False

        self.accion_jugador()

        salida.cerrada = False
        self.historial.registrar(
            deshacer=lambda: setattr(salida, "cerrada", True),
            description=f"apertura de puerta {direccion}"
        )

        if (self.llave_salida is not None
                and getattr(salida, "llave", None) == self.llave_salida):
            self._asignar_reversible(self, "_llave_salida_usada", True)

        # Si la puerta se cierra sola, se agenda el cierre.
        cierre = getattr(salida, "cierre_automatico", None)
        if cierre:
            self.programar_evento(self.reloj + cierre, "CERRAR_PUERTA", salida)

        self.actualizar_rastro(jugador.sala)
        self.proxima_accion(jugador, costo=50)
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

        # §2.11: los pergaminos quedan fuera del retroceso, también en el suelo.
        if nodo.clase != "pergamino_retroceso":
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

        # §2.11: soltar un pergamino no se deshace al retroceder.
        if resultado.clase != "pergamino_retroceso":
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

        resultado = equipar_reversible(jugador.inventario, self.historial)

        if resultado is None:
            return None

        self.actualizar_rastro(jugador.sala)
        self.proxima_accion(jugador, costo=50)
        self.avanzar_hasta_jugador()

        return resultado

    def usar_objeto(self):
        # Poción, antídoto o antorcha: el objeto actual del inventario (costo 50).
        jugador = self.jugador

        if jugador is None:
            return None

        nodo = jugador.inventario.actual()

        if nodo is None or nodo.clase not in ("pocion", "antidoto", "antorcha"):
            return None

        ficha = (self.gestor_datos.obtener_ficha(nodo.tipo_id)
                 if self.gestor_datos is not None else None)

        if ficha is None and nodo.clase != "antidoto":
            raise RuntimeError(f"No se encontró la ficha del objeto {nodo.tipo_id}.")

        # Validaciones antes de modificar nada.
        if nodo.clase == "antidoto":
            veneno = getattr(jugador, "veneno", None)
            if veneno is None or veneno.cancelado:
                return None

        if nodo.clase == "antorcha" and getattr(jugador, "antorcha_encendida", False):
            return None

        self.accion_jugador()

        if nodo.clase == "antidoto":
            self.cancelar_veneno(jugador)

        elif nodo.clase == "antorcha":
            self._asignar_reversible(jugador, "antorcha_encendida", True)
            self.programar_evento(self.reloj + ficha.duracion, "APAGAR_ANTORCHA", jugador)

        else:
            if getattr(ficha, "cura", None):
                self._curar_reversible(jugador, ficha.cura)

            if getattr(ficha, "modificador_velocidad", None):
                self.aplicar_velocidad_temporal(
                    jugador, ficha.modificador_velocidad, ficha.duracion or 0
                )

        # El objeto se consume (sale del inventario, reversible).
        soltar_reversible(jugador.inventario, nodo, self.historial)

        self.actualizar_rastro(jugador.sala)
        self.proxima_accion(jugador, costo=COSTO_USAR)
        self.avanzar_hasta_jugador()

        return nodo

    def usar_pergamino_retroceso(self, nodo_pergamino):
        if self.jugador is None or self.victoria:
            return False

        return usar_pergamino(self.jugador.inventario, self.historial, nodo_pergamino)

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

        # §4.4: solo cuentan los objetos del suelo de la sala actual.
        if self.jugador is not None and self.jugador.sala is not None:
            for objeto in self.obtener_objetos_suelo(self.jugador.sala):
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

    def _seleccionar_en_inventario(self, objeto_id):
        # Coloca el cursor del inventario en el objeto con ese ID usando solo la
        # API pública de Inventario (no se modifica el módulo de Persona C).
        inv = self.jugador.inventario
        if not any(str(n.instancia_id) == str(objeto_id) for n in inv):
            return None
        previo = None
        while inv.actual() is not previo:  # rebobina hasta el primer nodo
            previo = inv.actual()
            inv.retrocede()
        while str(inv.actual().instancia_id) != str(objeto_id):
            inv.avanza()  # existe: lo comprobamos arriba
        return inv.actual()

    def ejecutar_accion(self, nombre, argumento=""):

        # Contrato estable para replay. False significa acción rechazada
        # Acciones: mover(N/S/E/O), abrir(N/S/E/O), usar(id_objeto_actual), retroceder, esperar, atacar(id_enemigo), recoger(id_objeto),soltar(id_objeto_actual) y equipar(id_objeto_actual)

        if self.jugador is None or not self.jugador.esta_vivo() or self.victoria:
            return False

        if nombre == "retroceder":
            # Pergamino de retroceso (§2.11): sin costo de tiempo. Debe existir
            # como acción para que --replay reproduzca los retrocesos de la partida.
            pergamino = next((o for o in self.jugador.inventario
                              if o.clase == "pergamino_retroceso"), None)
            return pergamino is not None and self.usar_pergamino_retroceso(pergamino)

        if nombre == "mover":
            return self.mover_jugador(str(argumento).upper())

        if nombre == "abrir":
            return self.abrir_salida(str(argumento).upper())

        if nombre == "esperar":
            self.accion_jugador()
            self.actualizar_rastro(self.jugador.sala)
            self.proxima_accion(self.jugador, costo=100)
            # La acción ya se aceptó aunque el jugador muera esperando: debe
            # devolver True para que quede en la bitácora y el replay no se detenga.
            self.avanzar_hasta_jugador()
            return True

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

        if nombre in ("recoger", "soltar", "equipar", "usar"):
            objeto_id = str(argumento)

            if nombre == "recoger":
                nodo = next((o for o in self.obtener_objetos_suelo(self.jugador.sala)
                             if str(o.instancia_id) == objeto_id), None)
                return self.recoger_objeto(nodo) if nodo is not None else False

            # El objeto se identifica por su ID, no por la posición del cursor.
            if self._seleccionar_en_inventario(objeto_id) is None:
                return False

            if nombre == "soltar":
                return self.soltar_objeto() is not None

            if nombre == "usar":
                return self.usar_objeto() is not None

            return self.equipar_objeto() is not None

        return False

    def _ordenado(self, elementos, clave):
        # Orden estable para comparar estados; usa el ordenamiento propio del
        # proyecto (§4.9 prohíbe sorted()/list.sort()).
        elementos = list(elementos)
        resultado, _ = elegir_algoritmo(len(elementos))(elementos, clave)
        return resultado

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
                for e in self._ordenado(self.enemigos, lambda x: str(x.id))
            ],

            "eventos": self._ordenado(
                [(
                    ev.tiempo,
                    ev.secuencia,
                    ev.tipo,
                    None if ev.actor is None else getattr(ev.actor, "id", None),
                    ev.cancelado
                )
                for ev in self.agenda.heap
                if not ev.cancelado  # la cancelación es perezosa: no cuentan
            ], lambda t: t),

            "puertas": self._ordenado(
                [(sala.id, direccion, salida.cerrada)
                 for sala in self.salas
                 for direccion, salida in sala.salidas.items()],
                lambda t: t),

            "acciones": self.acciones_jugador,
            "derrotados": self.enemigos_derrotados,

            "azar": self.azar.getstate(),
        }