# Texto del resumen histórico (spec 004, T032; contracts/comandos-historia.md#salida-resumen-histórico-fr-006; FR-006, FR-007,
# FR-028, PR-07). Funciones de MÓDULO: `--replay --hasta` las usa sin instanciar `VistaConsola` (Principio II). Solo da
# formato a un `ResumenHistorico`: no tiene reglas de juego y no depende de K (FR-028).

from DTOS.ResumenHistorico import (EFECTO_ANTORCHA, EFECTO_VELOCIDAD, EFECTO_VENENO, REFERENCIA_ACCION,
                                   REFERENCIA_ACTUAL, REFERENCIA_FINAL, REFERENCIA_INSTANTE)

RAYA = "—"  # «sin armadura» y el guion largo del título


def _titulo(resumen):
    tipo, valor = resumen.referencia
    if tipo == REFERENCIA_INSTANTE:
        return f"Historia {RAYA} instante {valor}"
    if tipo == REFERENCIA_ACCION:
        return f"Historia {RAYA} antes de la acción {valor} (reloj {resumen.reloj})"
    if tipo == REFERENCIA_ACTUAL:
        return f"Historia {RAYA} estado actual (reloj {resumen.reloj})"
    if tipo == REFERENCIA_FINAL:
        return f"Historia {RAYA} estado final (reloj {resumen.reloj})"
    raise ValueError(f"Referencia desconocida: {resumen.referencia!r}")


def _texto_efecto(tipo, detalle):
    if tipo == EFECTO_VENENO:
        dano, intervalo, fin = detalle
        return f"veneno ({dano} de daño cada {intervalo}, hasta {fin})"
    if tipo == EFECTO_VELOCIDAD:
        cambio, fin = detalle
        return f"velocidad {cambio:+d} (hasta {fin})"
    if tipo == EFECTO_ANTORCHA:
        return "antorcha encendida"
    return tipo


def _texto_inventario(inventario):
    total = 0
    partes = []
    for nombre, cantidad in inventario:
        total += cantidad
        partes.append(nombre if cantidad == 1 else f"{nombre} x{cantidad}")
    return f"Inventario ({total}): {', '.join(partes) if partes else 'ninguno'}"


def lineas_mapa(mapa):
    """Bloque `Mapa conocido:` con el mismo formato que `VistaConsola.mostrar_mapa` (comando `mapa`)."""
    lineas = ["Mapa conocido:"]
    for sala in mapa.exploradas:
        lineas.append(f"  Sala {sala.id}: {sala.nombre}")
        for salida in sala.salidas:
            lineas.append(f"    {salida.direccion} -> sala {salida.destino_id}   "
                          f"costo {salida.costo}   {salida.estado}")
    avistadas = ", ".join(str(id_sala) for id_sala in mapa.avistadas)
    lineas.append(f"Avistadas: {avistadas or 'ninguna'}")
    return lineas


def lineas_resumen(resumen):
    """Lista de líneas del resumen. O(tamaño del resumen)."""
    lineas = [_titulo(resumen)]
    lineas.append(f"Sala {resumen.sala[0]}: {resumen.sala[1]}")
    lineas.append(f"Vida: {resumen.vida}/{resumen.vida_max}   Ataque: {resumen.ataque}   "
                  f"Defensa: {resumen.defensa}   Velocidad: {resumen.velocidad}")
    lineas.append(f"Equipo: arma {resumen.arma or RAYA}; armadura {resumen.armadura or RAYA}")
    lineas.append(_texto_inventario(resumen.inventario))
    efectos = "; ".join(_texto_efecto(tipo, detalle) for tipo, detalle in resumen.efectos)
    lineas.append(f"Efectos: {efectos or 'ninguno'}")
    enemigos = ", ".join(f"{id_enemigo} ({vida}/{vida_max})" for id_enemigo, _tipo, vida, vida_max in resumen.enemigos)
    lineas.append(f"Enemigos en la sala: {enemigos or 'ninguno'}")
    lineas.extend(lineas_mapa(resumen.mapa))
    if resumen.resultado is not None:
        lineas.append(f"Resultado: {resumen.resultado}")
    return lineas


def texto_resumen(resumen):
    """El resumen como un solo texto, con saltos de línea."""
    return "\n".join(lineas_resumen(resumen))
