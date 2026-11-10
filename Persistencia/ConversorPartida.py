# Puente entre el motor y el archivo binario de la partida (S4.10)
# - registros_desde_motor / registro_jugador_desde_motor: estado vivo -> registros para guardar
# - RestauradorPartida: al cargar, cada sala se lee del archivo SOLO cuando el motor la necesita (busqueda binaria sobre el indice, sin leer el archivo completo)

# Lo que NO se guarda (igual que el historial de retroceso es de sesion):
# los efectos temporales (veneno, antorcha, velocidad) y los cierres automaticos de puertas pendientes
# Los enemigos activos si conservan el instante de su siguiente accion

from DTOS.ContenidoSala import ContenidoSala
from DTOS.EnemigoInstancia import EnemigoInstancia
from DTOS.TrampaInstancia import TrampaInstancia
from Modelo.ordenamiento import elegir_algoritmo
from Modelo.retroceso import Historial
from Persistencia.ArchivoPartida import LectorPartida
from Persistencia.FormatoBinario import VersionIncompatible
from Persistencia.RegistroConocimiento import RegistroConocimiento
from Persistencia.RegistroJugador import RegistroJugador
from Persistencia.RegistroSala import RegistroSala

REARME_POR_DEFECTO = 300  # el mismo valor que usa el motor si la ficha no trae rearme

# guardar: motor -> registros

def _buscar_registro(registros, sala_id):
    # busqueda binaria: los registros se arman en orden de id de sala
    inicio, fin = 0, len(registros) - 1
    while inicio <= fin:
        medio = (inicio + fin) // 2
        if registros[medio].sala_id == sala_id:
            return registros[medio]
        if registros[medio].sala_id < sala_id:
            inicio = medio + 1
        else:
            fin = medio - 1
    return None


def _contenido_de(motor, sala_id):
    for contenido in motor.contenidos_salas:
        if contenido.id_sala == sala_id:
            return contenido
    return None


def _asegurar_salas_con_estado(motor):
    # un enemigo errante puede entrar a una sala que el jugador nunca cargo.
    # Antes de guardar se carga esa sala, asi cada registro guardado queda completo (sus enemigos, objetos y trampas originales mas lo que llego despues)
    pendientes = []
    for enemigo in motor.enemigos:
        if enemigo.esta_vivo() and enemigo.sala is not None:
            if not motor.contenido_disponible(enemigo.sala.id):
                pendientes.append(enemigo.sala)

    for id_sala, objetos in motor.objetos_suelo:
        if objetos and not motor.contenido_disponible(id_sala):
            pendientes.append(motor.buscar_sala(motor.salas, id_sala))

    for sala in pendientes:
        if not motor.contenido_disponible(sala.id):
            motor.preparar_sala(sala)


def registros_desde_motor(motor):
    _asegurar_salas_con_estado(motor)

    # una entrada por cada sala con contenido cargado, ordenadas por id
    ids = motor._ordenado(motor._salas_contenido_cargado, lambda id_sala: id_sala)
    registros = []

    for id_sala in ids:
        sala = motor.buscar_sala(motor.salas, id_sala)
        rastro = getattr(sala, "rastro", None)
        contenido = _contenido_de(motor, id_sala)

        trampas = []
        if contenido is not None:
            for trampa in contenido.trampas:
                armada = motor._obtener_estado_trampa(trampa.instancia, True)
                trampas.append((str(trampa.instancia), str(trampa.tipo), armada))

        objetos = [(str(objeto.instancia_id), str(objeto.tipo_id))
                   for objeto in motor.obtener_objetos_suelo(sala)]

        puertas = [(direccion, bool(salida.cerrada))
                   for direccion, salida in sala.salidas.items()]

        registros.append(RegistroSala(
            id_sala, -1 if rastro is None else rastro, [], objetos, trampas, puertas
        ))

    # cada enemigo vivo se guarda en la sala donde esta AHORA (no donde nacio)
    for enemigo in motor.enemigos:
        if not enemigo.esta_vivo():
            continue

        registro = _buscar_registro(registros, enemigo.sala.id)
        if registro is None:
            raise RuntimeError(f"No se pudo guardar la sala del enemigo {enemigo.id}")

        tiempo = enemigo.tiempo_siguiente if enemigo.activo else -1
        registro.enemigos.append((str(enemigo.id), str(enemigo.tipo_id), enemigo.vida, tiempo))

    # salas que venian en la partida cargada y que todavia no se visitaron: se copian tal cual
    if motor.restaurador is not None:
        registros.extend(motor.restaurador.registros_pendientes(motor))

    return registros


def registro_jugador_desde_motor(motor):
    jugador = motor.jugador
    return RegistroJugador(
        sala_id=jugador.sala.id,
        vida=jugador.vida,
        acciones=motor.acciones_jugador,
        derrotados=motor.enemigos_derrotados,
        llave_usada=bool(motor._llave_salida_usada),
        inventario=jugador.inventario,
    )


def _puerta_puede_diferir(salida):
    # contracts/formato-partida.md: hoy cerrada, o con llave, o con cierre automatico
    return (bool(salida.cerrada) or getattr(salida, "llave", None) is not None
            or bool(getattr(salida, "cierre_automatico", None)))


def registro_conocimiento_desde_motor(motor):
    """Bloque de conocimiento del motor (FR-015, PR-06, PR-07); None si el motor no tiene conocimiento.

    Exploradas y recuerdos salen de `Conocimiento.exportar`. Las puertas reales son las salidas que
    `_puerta_puede_diferir`, de TODAS las salas (tambien las que no tienen bloque), para que al cargar se
    corrijan sin leer bloques de sala (H2). El costo de las salidas no se guarda: sale del esqueleto.

    O(n + e) para recorrer las n salas y sus e salidas, mas el orden canonico del registro
    (O(k log k + p log p + r log r) con `elegir_algoritmo`).
    """
    if motor.conocimiento is None:
        return None

    exploradas, recuerdos = motor.conocimiento.exportar()
    reales = []
    for sala in motor.salas:
        for direccion, salida in sala.salidas.items():
            if _puerta_puede_diferir(salida):
                reales.append((sala.id, direccion, bool(salida.cerrada)))

    return RegistroConocimiento(exploradas, recuerdos, reales)


# cargar: registros -> motor

def restaurar_jugador(motor, registro):
    sala = motor.buscar_sala(motor.salas, registro.sala_id)
    if sala is None:
        raise VersionIncompatible(f"La sala {registro.sala_id} del jugador no existe en la cripta")

    jugador = motor.jugador
    jugador.sala = sala
    jugador.vida = registro.vida
    jugador.vivo = registro.vida > 0
    jugador.inventario = registro.inventario

    motor.acciones_jugador = registro.acciones
    motor.enemigos_derrotados = registro.derrotados
    motor._llave_salida_usada = registro.llave_usada


def _salas_por_id(motor):
    # Salas ordenadas por id, para buscar con busqueda binaria (sin dict). O(n log n).
    ordenadas, _ = elegir_algoritmo(len(motor.salas))(list(motor.salas), lambda sala: sala.id)
    return ordenadas


def _buscar_por_id(ordenadas, id_sala):
    # Busqueda binaria sobre las salas ordenadas por id. O(log n); None si no esta.
    inicio, fin = 0, len(ordenadas)
    while inicio < fin:
        medio = (inicio + fin) // 2
        if ordenadas[medio].id < id_sala:
            inicio = medio + 1
        else:
            fin = medio
    if inicio < len(ordenadas) and ordenadas[inicio].id == id_sala:
        return ordenadas[inicio]
    return None


def aplicar_puertas_reales(motor, registro):
    """Pone cada puerta real en su estado guardado, sin leer bloques de sala (FR-006, PR-07, H2).

    Primero valida todo: una sala o direccion que no existe lanza VersionIncompatible sin cambiar nada.
    No pasa por el Historial: cargar no es una accion del jugador. O(n log n + r log n).
    """
    ordenadas = _salas_por_id(motor)
    cambios = []
    for id_sala, direccion, cerrada in registro.puertas_reales:
        sala = _buscar_por_id(ordenadas, id_sala)
        if sala is None:
            raise VersionIncompatible(f"La sala {id_sala} de una puerta guardada no existe en la cripta")
        salida = sala.salidas.get(direccion)
        if salida is None:
            raise VersionIncompatible(f"La sala {id_sala} no tiene la salida {direccion} guardada")
        cambios.append((salida, cerrada))

    for salida, cerrada in cambios:
        salida.cerrada = cerrada


def restaurar_conocimiento(motor, registro):
    """Reemplaza el conocimiento del motor por el guardado, sin Historial (FR-015).

    Una sala o direccion inexistente, o un recuerdo invalido, lanza VersionIncompatible (FR-016).
    Complejidad: la de `Conocimiento.restaurar`.
    """
    try:
        motor.conocimiento.restaurar(registro.exploradas, registro.recuerdos)
    except ValueError as error:
        raise VersionIncompatible(f"El conocimiento guardado no corresponde a la cripta: {error}") from error


def _reactivar_enemigo(motor, enemigo, tiempo):
    # igual que motor.activar_enemigo, pero respetando el instante guardado
    enemigo.activo = True
    enemigo.tiempo_siguiente = max(tiempo, motor.reloj)
    enemigo.evento_actual = motor.programar_evento(enemigo.tiempo_siguiente, "ACCION_ACTOR", enemigo)
    motor._programar_regeneracion(enemigo)


def _aplicar_registro(motor, registro):
    sala = motor.buscar_sala(motor.salas, registro.sala_id)
    if sala is None:
        raise VersionIncompatible(f"La sala {registro.sala_id} del archivo no existe en la cripta")

    sala.rastro = None if registro.rastro < 0 else registro.rastro

    for direccion, cerrada in registro.puertas:
        salida = sala.salidas.get(direccion)
        if salida is not None:
            salida.cerrada = cerrada

    # objetos del suelo: conservan su id de instancia
    objetos = [motor.crear_objeto(instancia, tipo) for instancia, tipo in registro.objetos]
    entrada = None
    for existente in motor.objetos_suelo:
        if existente[0] == sala.id:
            entrada = existente
            break
    if entrada is None:
        motor.objetos_suelo.append([sala.id, objetos])
    else:
        entrada[1].extend(objetos)

    # enemigos: si ya esta en el motor es porque llego caminando a esta sala, no se duplica
    for instancia, tipo, vida, tiempo in registro.enemigos:
        if any(str(enemigo.id) == instancia for enemigo in motor.enemigos):
            continue

        enemigo = motor.crear_enemigo(instancia, tipo, vida, sala)
        motor.registrar_enemigo(enemigo)

        if tiempo >= 0:
            _reactivar_enemigo(motor, enemigo, tiempo)

    # trampas: una desarmada vuelve a programar su rearme (la agenda no se guarda)
    trampas = []
    for instancia, tipo, armada in registro.trampas:
        trampa = TrampaInstancia(instancia, tipo)
        trampas.append(trampa)
        motor._guardar_estado_trampa(instancia, armada)

        if not armada:
            ficha = motor.gestor_datos.obtener_ficha(tipo)
            intervalo = getattr(ficha, "rearme", None) or REARME_POR_DEFECTO
            motor.programar_evento(motor.reloj + intervalo, "REARMAR_TRAMPA", trampa)

    # la sala queda registrada igual que si su contenido viniera del gestor
    motor.contenidos_salas.append(ContenidoSala(
        sala.id,
        enemigos=[EnemigoInstancia(i, t, v) for i, t, v, _ in registro.enemigos],
        trampas=trampas,
        objetos=[tipo for _, tipo in registro.objetos],
    ))
    motor._salas_contenido_cargado.append(sala.id)


class RestauradorPartida:
    # lo usa el motor en preparar_sala(): primero el archivo, despues el gestor

    def __init__(self, ruta):
        self.ruta = ruta
        self.lector = LectorPartida(ruta)

    @property
    def encabezado(self):
        return self.lector.encabezado

    def leer_jugador(self):
        return self.lector.leer_jugador()

    def leer_conocimiento(self):
        return self.lector.leer_conocimiento()

    def restaurar_sala(self, motor, id_sala):
        registro = self.lector.leer_sala(id_sala)
        if registro is None:
            return False  # no estaba guardada: el motor la pide al gestor

        # lo restaurado no es parte de ninguna accion del jugador, asi que no debe quedar en el historial de retroceso
        historial = motor.historial
        motor.historial = Historial()
        try:
            _aplicar_registro(motor, registro)
        finally:
            motor.historial = historial

        return True

    def registros_pendientes(self, motor):
        # salas del archivo que el motor todavia no restauro (solo se lee el indice + esas salas)
        pendientes = []
        for id_sala in self.lector.ids_salas():
            if not motor.contenido_disponible(id_sala):
                pendientes.append(self.lector.leer_sala(id_sala))
        return pendientes

    def cerrar(self):
        self.lector.cerrar()