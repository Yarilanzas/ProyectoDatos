# Generadores de mapas sintéticos para las mediciones de la Fase 6 (T099; research R9).
# Atiende: SC-006, PR-15.
#
# Ningún dato de una cripta real (Principio IV): todo sale de una fórmula, sin red ni archivos.
# Cada mapa es la lista del esqueleto en el formato del servicio, la misma que recibe `crear_paquete_niebla`:
#   {"id", "nombre", "salidas": {dirección: {"sala": id_destino, "costo": entero >= 1}}}
# Los dicts son el registro JSON del esqueleto, no un índice ni una caché (Principio I): para ir de un id a su sala
# se usa la posición, porque los ids son 1..n en orden y la sala con id i está en `salas[i - 1]`.
#
# Las salas forman una rejilla rectangular de `ancho` columnas llenada por filas: N y S unen filas, E y O columnas.
# Toda salida tiene su salida de vuelta en la dirección opuesta con el mismo costo (costos simétricos), y el mapa
# es conexo: la primera fila está unida por E y O, y cada sala de otra fila tiene salida N a la fila de arriba.
#
# Iniciar una partida con estos mapas (`partida_niebla`, `nueva_partida`) necesita `forzar=True`: no tienen llaves
# ni contenido pensado para ganar, así que la verificación de resolubilidad de la spec 002 podría rechazarlos.
#
# | Operación                       | Complejidad |
# |---------------------------------|-------------|
# | cadena(V), grilla(V)            | O(V)        |
# | salas_sinteticas(n)             | O(n)        |
# | costo de una salida             | O(1)        |

COSTO_MAXIMO = 199   # costos en 1..199: variados y siempre enteros >= 1 (precondición de `primer_paso`)
_MASCARA = 0xFFFFFFFF


def _costo(a, b, semilla):
    # Costo de la puerta entre las salas a y b. Solo depende del par sin orden y de la semilla: simétrico.
    menor, mayor = (a, b) if a < b else (b, a)
    x = (menor * 73856093 + mayor * 19349663 + semilla * 83492791 + 0x9E3779B9) & _MASCARA
    x ^= x >> 16
    x = (x * 0x45D9F3B) & _MASCARA
    x ^= x >> 16
    return 1 + x % COSTO_MAXIMO


def _salida(origen, destino, semilla):
    return {"sala": destino, "costo": _costo(origen, destino, semilla)}


def _rejilla(cantidad, ancho, semilla):
    if cantidad < 1:
        raise ValueError("cantidad debe ser >= 1")
    salas = []
    for id_sala in range(1, cantidad + 1):
        columna = (id_sala - 1) % ancho
        salidas = {}
        # orden N, S, E, O, como ORDEN_DIRECCIONES de tests/utiles_niebla.py
        if id_sala - ancho >= 1:
            salidas["N"] = _salida(id_sala, id_sala - ancho, semilla)
        if id_sala + ancho <= cantidad:
            salidas["S"] = _salida(id_sala, id_sala + ancho, semilla)
        if columna + 1 < ancho and id_sala + 1 <= cantidad:
            salidas["E"] = _salida(id_sala, id_sala + 1, semilla)
        if columna > 0:
            salidas["O"] = _salida(id_sala, id_sala - 1, semilla)
        salas.append({"id": id_sala, "nombre": f"Sala {id_sala}", "salidas": salidas})
    return salas


def _raiz_entera(n):
    # Mayor r con r * r <= n, por búsqueda binaria. O(log n).
    ini, fin = 0, n
    while ini < fin:
        medio = (ini + fin + 1) // 2
        if medio * medio <= n:
            ini = medio
        else:
            fin = medio - 1
    return ini


def cadena(cantidad, semilla=0):
    """Cadena de ``cantidad`` salas unidas por E y O: 1 - 2 - ... - V. Es el peor caso de profundidad de ruta."""
    return _rejilla(cantidad, cantidad, semilla)


def grilla(cantidad, semilla=0):
    """Grilla cuadrada de ``cantidad`` salas (lado x lado). ``cantidad`` debe ser un cuadrado (25, 100, 400, 2500)."""
    lado = _raiz_entera(cantidad)
    if lado * lado != cantidad or cantidad < 1:
        raise ValueError(f"la grilla necesita un cuadrado perfecto, no {cantidad}")
    return _rejilla(cantidad, lado, semilla)


def salas_sinteticas(cantidad, semilla=0):
    """``cantidad`` salas cualesquiera (M1 a M3, n hasta 20000) en una rejilla casi cuadrada; la última fila puede
    quedar incompleta."""
    lado = _raiz_entera(cantidad)
    if lado * lado < cantidad:
        lado += 1
    return _rejilla(cantidad, lado, semilla)
