# Copia estructurada del estado de la partida (spec 004, T015 y T016; data-model.md#puntocontrol; FR-017, FR-021, FR-008, PR-02).
#
# `copy.deepcopy(motor)` a secas no sirve: recorre por recursión el esqueleto (cada sala llega a la siguiente por la caché
# `Salida._destino`) y el inventario (lista doble), y falla con RecursionError en criptas de unas decenas de salas o
# inventarios de 165 nodos (medido en T003). Aquí se copia el estado del motor **sin recorrer** el esqueleto:
#
#   copiar(motor)      -> PuntoControl: deepcopy(motor, memo) con el esqueleto compartido (cada Sala y Salida se mapea a sí
#                         misma), más una foto de lo único que cambia en el esqueleto (`rastro` y `cerrada`).
#   materializar(...)  -> un clon jugable: esqueleto propio, deepcopy del estado mapeado a ese esqueleto, gestor histórico.
#
# El único `dict` de este módulo es el `memo` (de una sola llamada) de `copy.deepcopy`, autorizado por el profesor el
# 2026-11-12 (tasks.md, T003). No se usa como índice del dominio. Todo lo demás son listas.
#
# Sobre `Salida.cerrada`: este archivo la escribe solo sobre las salidas de la COPIA del esqueleto que arma `materializar`,
# antes de que exista el clon, nunca sobre las del motor en juego (por eso A lo excluye por nombre de 003-T015). No usa
# `MotorSimulacion._escribir_cerrada`: no hay motor al que sumarle `version_puertas`, y el entero que el clon recibe en
# `estado` ya es el de la decisión de la foto, así que `cerrada` y `version_puertas` salen coherentes.

import copy

from Modelo.PuntoControl import PuntoControl, SIN_RASTRO
from Modelo.retroceso import Historial

# Campos que cambian durante la partida en el esqueleto (HL3). Se extienden si A agrega uno nuevo a `Sala` o `Salida`.
# `Salida.cerrada_en_esqueleto` NO está aquí: es constante (la fija `Salida.__init__`), `copy.copy` la conserva.
CAMPOS_MUTABLES_SALA = ("rastro",)
CAMPOS_MUTABLES_SALIDA = ("cerrada",)


def _par(nodo, memo):
    """El nodo copiado que corresponde a `nodo` (None si es None)."""
    if nodo is None:
        return None
    copia = memo.get(id(nodo))
    if copia is None:
        copia = copy.copy(nodo)
        memo[id(nodo)] = copia
    return copia


def _registrar_inventario(inventario, memo):
    """Copia `inventario` con un bucle sobre la lista doble, sin recursión, y deja el resultado en el `memo` para que
    `deepcopy` no recorra la cadena de nodos (T003 midió RecursionError desde 165 nodos). O(nodos).

    Los nodos solo guardan texto y enteros, así que `copy.copy` basta; los enlaces y los cinco punteros del inventario
    (cabeza, cola, cursor, arma y armadura equipadas) se re-ligan a las copias."""
    if inventario is None or id(inventario) in memo:
        return
    nuevo = copy.copy(inventario)
    memo[id(inventario)] = nuevo

    nodo = inventario._cabeza
    while nodo is not None:
        memo[id(nodo)] = copy.copy(nodo)
        nodo = nodo.siguiente

    nodo = inventario._cabeza
    while nodo is not None:
        copia = memo[id(nodo)]
        copia.anterior = _par(nodo.anterior, memo)
        copia.siguiente = _par(nodo.siguiente, memo)
        nodo = nodo.siguiente

    nuevo._cabeza = _par(inventario._cabeza, memo)
    nuevo._cola = _par(inventario._cola, memo)
    nuevo._cursor = _par(inventario._cursor, memo)
    nuevo._arma_equipada = _par(inventario._arma_equipada, memo)
    nuevo._armadura_equipada = _par(inventario._armadura_equipada, memo)


def foto_rastros(motor):
    """Lista con `Sala.rastro` por ordinal de sala; SIN_RASTRO si la sala no tiene el atributo. O(N)."""
    return [getattr(sala, "rastro", SIN_RASTRO) for sala in motor.salas]


def foto_cerradas(motor):
    """Lista de `bool` con `Salida.cerrada` por ordinal de salida, en el orden de recorrido de las salas. O(N + E)."""
    resultado = []
    for sala in motor.salas:
        for _direccion, salida in sala.salidas.items():
            resultado.append(bool(salida.cerrada))
    return resultado


def copiar(motor, accion=None, epoca=0):
    """Copia estructurada del estado de `motor` como `PuntoControl` (la decisión en curso del jugador).

    `deepcopy(motor, memo)` con `memo` que mapea: `gestor_datos` y `restaurador` a None (no son estado de la partida: el
    gestor trae caché y una referencia de vuelta al motor, el restaurador un archivo abierto), `historial` a un
    `Historial()` vacío (sus cierres apuntan a objetos vivos), y cada `Sala` y `Salida` a sí misma (no se recorren; la
    foto guarda lo que cambia en ellas). El inventario se copia con un bucle. El `grafo_cripta` y el `espacio_busqueda`
    se copian con el resto: el grafo lee las puertas en vivo (no depende de `version_puertas`) y sus referencias a las
    salas y al motor se re-ligan por el `memo`; el espacio de búsqueda es solo espacio de trabajo.

    No escribe nada en `motor`. `accion` es la posición de la decisión (por omisión, `motor.acciones_jugador`).

    Complejidad (S = tamaño del estado vivo, N salas, E salidas): tiempo O(S + N + E), memoria O(S).
    """
    memo = {}
    if motor.gestor_datos is not None:
        memo[id(motor.gestor_datos)] = None
    if motor.restaurador is not None:
        memo[id(motor.restaurador)] = None
    memo[id(motor.historial)] = Historial()
    for sala in motor.salas:
        memo[id(sala)] = sala
        for _direccion, salida in sala.salidas.items():
            memo[id(salida)] = salida
    if motor.jugador is not None:
        _registrar_inventario(motor.jugador.inventario, memo)

    estado = copy.deepcopy(motor, memo)
    return PuntoControl(estado, foto_rastros(motor), foto_cerradas(motor),
                        motor.acciones_jugador if accion is None else accion,
                        motor.reloj, motor.secuencia, epoca)


def _esqueleto_propio(estado, punto, memo):
    """Pasada iterativa: `copy.copy` de cada sala y salida del respaldo (`estado.salas`), con `rastro` y `cerrada` de la
    foto, y deja en `memo` el par nuevo de cada objeto. Solo escribe sobre las copias. O(N + E)."""
    if len(punto.foto_rastros) != len(estado.salas):
        raise ValueError("La foto de rastros no corresponde a las salas del punto de control")

    salidas_nuevas = []
    ordinal_salida = 0
    for ordinal in range(len(estado.salas)):
        sala = estado.salas[ordinal]
        nueva = copy.copy(sala)
        nueva.salidas = copy.copy(sala.salidas)
        valor = punto.foto_rastros[ordinal]
        if valor is SIN_RASTRO:
            if hasattr(nueva, "rastro"):
                del nueva.rastro  # el vivo la visitó después de la foto: el clon no crea ni conserva el atributo
        else:
            nueva.rastro = valor
        memo[id(sala)] = nueva

        for direccion, salida in sala.salidas.items():
            nueva_salida = copy.copy(salida)
            nueva_salida.cerrada = punto.foto_cerradas[ordinal_salida]
            ordinal_salida += 1
            nueva.salidas[direccion] = nueva_salida
            memo[id(salida)] = nueva_salida
            salidas_nuevas.append(nueva_salida)

    if ordinal_salida != len(punto.foto_cerradas):
        raise ValueError("La foto de puertas no corresponde a las salidas del punto de control")

    # `_origen` y `_destino` (cachés del motor y de `Conocimiento`) apuntaban a salas del respaldo: se re-ligan a las nuevas
    for salida in salidas_nuevas:
        for nombre in ("_origen", "_destino"):
            anterior = getattr(salida, nombre, None)
            if anterior is not None and id(anterior) in memo:
                setattr(salida, nombre, memo[id(anterior)])


def materializar(punto, gestor_historico, abrir_copia=None, ruta_copia=None):
    """Clon **jugable** y propio del estado de `punto`: el único que se puede ejecutar (`punto.estado` nunca).

    1. Esqueleto propio (``_esqueleto_propio``): sala y salida nuevas, `rastro` y `cerrada` de la foto.
    2. ``deepcopy(punto.estado, memo)`` con el `memo` que mapea cada objeto del respaldo a su par nuevo (así también se
       re-liga `Evento.actor`: un `CERRAR_PUERTA` pendiente apunta a la salida del clon, no a la del vivo), el
       `historial` a un `Historial()` vacío y el inventario a su copia hecha con un bucle (sin recursión).
    3. ``clon.gestor_datos = gestor_historico`` y ``conectar_estado_juego(clon)``: sin gestor el clon no puede jugar (una
       sala con trampa lanza RuntimeError y una sala sin contenido se rechaza).
    4. Si `abrir_copia` y `ruta_copia` (la copia privada del archivo de la época), ``clon.restaurador = abrir_copia(ruta_copia)``.
    5. ``clon.eco = False``.

    Solo escribe `Salida.cerrada` y `Sala.rastro` sobre el clon, nunca sobre el motor vivo. Sin red, archivos ni consola:
    todo lo externo se inyecta (Principio II). Un solo clon vivo a la vez por `gestor_historico`
    (`GestorDatos.estado_juego` es único).

    `ciclo` y `version_puertas` llegan en `estado`; el clon no los baja ni los recalcula.

    Complejidad: tiempo O(S + N + E), memoria O(S).
    """
    estado = punto.estado
    memo = {}
    _esqueleto_propio(estado, punto, memo)
    memo[id(estado.historial)] = Historial()
    if estado.jugador is not None:
        _registrar_inventario(estado.jugador.inventario, memo)

    clon = copy.deepcopy(estado, memo)

    clon.gestor_datos = gestor_historico
    if gestor_historico is not None:
        gestor_historico.conectar_estado_juego(clon)
    clon.restaurador = None
    if abrir_copia is not None and ruta_copia is not None:
        clon.restaurador = abrir_copia(ruta_copia)
    clon.eco = False
    return clon
