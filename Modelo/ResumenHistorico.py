# Arma el DTO del estado pasado desde un motor (el clon) (spec 004, T031; FR-006, FR-007, FR-028, PR-07).
# Solo lee: no cambia el motor. Ordena con el ordenamiento propio del proyecto (no `sorted`).

from DTOS.ResumenHistorico import (EFECTO_ANTORCHA, EFECTO_VELOCIDAD, EFECTO_VENENO, REFERENCIA_ACTUAL,
                                   REFERENCIA_FINAL, ResumenHistorico)
from Modelo.MotorSimulacion import INTERVALO_VENENO
from Modelo.ordenamiento import elegir_algoritmo

CLASE_PERGAMINO = "pergamino_retroceso"
NOMBRE_PERGAMINO = "Pergamino de retroceso"


def _ordenar(elementos, clave):
    elementos = list(elementos)
    resultado, _ = elegir_algoritmo(len(elementos))(elementos, clave)
    return resultado


def _inventario(motor, pergaminos):
    """Tupla de (nombre, cantidad) en el orden del inventario (primera aparición). Si `pergaminos` no es None, la
    cantidad de pergaminos de retroceso es esa y no la del clon (FR-029; T048 la toma de la serie)."""
    nombres = []
    cantidades = []
    nombre_pergamino = NOMBRE_PERGAMINO
    for nodo in motor.jugador.inventario:
        if nodo.clase == CLASE_PERGAMINO:
            nombre_pergamino = nodo.nombre
            if pergaminos is not None:
                continue
        posicion = -1
        for indice in range(len(nombres)):
            if nombres[indice] == nodo.nombre:
                posicion = indice
        if posicion == -1:
            nombres.append(nodo.nombre)
            cantidades.append(1)
        else:
            cantidades[posicion] += 1
    if pergaminos is not None and pergaminos > 0:
        nombres.append(nombre_pergamino)
        cantidades.append(pergaminos)
    return tuple((nombres[i], cantidades[i]) for i in range(len(nombres)))


def _efectos(motor):
    """Veneno, velocidad temporal y antorcha del jugador, leídos de la agenda del clon (todo el montículo, también los
    eventos que el corte oculta) y de `antorcha_encendida`. Orden: por (tiempo, secuencia) y la antorcha al final."""
    jugador = motor.jugador
    eventos = [ev for ev in motor.agenda.heap if not ev.cancelado and ev.actor is jugador]
    eventos = _ordenar(eventos, lambda ev: (ev.tiempo, ev.secuencia))
    efectos = []
    apagado = None
    for ev in eventos:
        if ev.tipo == EFECTO_VENENO:
            dano, fin = ev.datos
            efectos.append((EFECTO_VENENO, (dano, INTERVALO_VENENO, fin)))
        elif ev.tipo == EFECTO_VELOCIDAD:
            efectos.append((EFECTO_VELOCIDAD, (ev.datos, ev.tiempo)))
        elif ev.tipo == EFECTO_ANTORCHA:
            apagado = ev.tiempo
    if getattr(jugador, "antorcha_encendida", False):
        efectos.append((EFECTO_ANTORCHA, (apagado,)))
    return efectos


def resumir(motor, reloj, referencia, pergaminos=None):
    """``ResumenHistorico`` de `motor` (un clon, o el vivo solo para leerlo) con el reloj consultado `reloj`.

    - `referencia`: ``("instante", t)``, ``("accion", k)``, ``("actual", None)`` o ``("final", None)``.
    - `pergaminos`: cantidad de pergaminos de retroceso en ese momento; ``None`` usa los del inventario del clon.
    - `resultado` solo se llena en las referencias «actual» y «final» y si la partida terminó.
    - `mapa` es ``motor.mapa_conocido()``, sin recalcular con información posterior.

    Complejidad: O(inventario + agenda + enemigos·log) más el mapa conocido; O(S) en el peor caso.
    """
    jugador = motor.jugador
    sala = jugador.sala
    enemigos = [(e.id, e.tipo_id, e.vida, e.vida_max)
                for e in _ordenar(motor.obtener_enemigos(sala=sala, solo_vivos=True), lambda e: str(e.id))]
    arma = motor.jugador.inventario.arma_equipada()
    armadura = motor.jugador.inventario.armadura_equipada()
    resultado = None
    if referencia[0] in (REFERENCIA_ACTUAL, REFERENCIA_FINAL):
        estado = motor.estado_partida()
        resultado = None if estado == "en_curso" else estado
    return ResumenHistorico(
        referencia, reloj, (sala.id, sala.nombre), jugador.vida, jugador.vida_max, jugador.ataque,
        jugador.defensa, jugador.velocidad, None if arma is None else arma.nombre,
        None if armadura is None else armadura.nombre, _inventario(motor, pergaminos), _efectos(motor),
        enemigos, motor.mapa_conocido(), resultado)
