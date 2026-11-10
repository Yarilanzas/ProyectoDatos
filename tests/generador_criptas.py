"""Generador de criptas sintéticas para pruebas y bench (spec 002, T002; también lo usa la T003 de la spec 003).

Este archivo no lleva prefijo test: `unittest discover` no lo ejecuta. No contiene datos de criptas reales
(Principio IV): las dimensiones (por ejemplo 300 salas, ≈ 760 salidas y 4 llaves) son parámetros.

Interfaz
--------
``generar_cripta(semilla, salas, llaves, resoluble=True, con_ciclo=False, llave_de_enemigo=False,
costo_ida=1, costo_vuelta=1, id_cripta="sint") -> CriptaSintetica``

Determinista por semilla: usa solo una instancia local ``random.Random(semilla)``, nunca el ``random`` global.

``CriptaSintetica`` ofrece:

- ``detalles``: ``CriptaDetalles`` (``sala_inicial``, ``sala_salida``, ``llave_salida``,
  ``presupuesto_solicitudes``...); ``detalles_json`` es el mismo dato en el formato de ``GET /criptas/<id>``.
- ``salas_json``: lista en el formato de ``GET /criptas/<id>/salas`` (``id``, ``nombre``, ``salidas``).
- ``llaves_json``: lista en el formato de ``GET /criptas/<id>/llaves`` (``id``, ``sala``, ``enemigo`` opcional).
- ``esqueleto()`` → ``list[SalaEsqueleto]`` y ``ubicaciones()`` → ``list[UbicacionLlave]``.
- ``llaves``: ids de las llaves en el orden de la cadena (``llaves[0]`` es k1; la última es ``llave_salida``).
- ``regiones``: lista de pares ``(primera, ultima)`` de ids de sala por región; ``region_de(id_sala)``.
- ``entrada``: por región, la llave que piden las puertas que entran a ella (``None`` = abiertas;
  ``SIN_LLAVE`` = cerradas sin llave).

``escribir_paquete(carpeta, cripta, escribir_llaves=True)`` escribe un paquete offline completo con el mismo esquema
que ``crear_paquete_niebla`` de ``tests/utiles_niebla.py`` más ``criptas/<id>/llaves.json``.

Forma de la cripta
------------------
- Cuadrícula de ``salas`` salas con ids enteros contiguos desde 1, recorrida en serpentina (las filas pares de izquierda
  a derecha y las impares al revés), así que dos ids consecutivos siempre son vecinos y cualquier rango de ids es
  conexo. Salidas en N, S, E y O: la serpentina más vecinos verticales al azar hasta unas 2,5 salidas por sala
  (300 salas → 760 salidas). Las salidas son **dirigidas**: A→B y B→A tienen estado, llave y costo propios;
  ``costo_ida`` vale para la salida que va hacia el id mayor y ``costo_vuelta`` para la otra.
- ``sala_inicial`` = 1 y ``sala_salida`` = ``salas`` (sola en la última región). Las salas 1..salas−1 se reparten en
  ``llaves`` regiones R0..R(K−1) de ids contiguos. La llave k(j) está en una sala al azar de R(j−1).
- Variante resoluble: las puertas que entran a R(i) desde una región menor piden k(i); las que entran a la sala de
  salida piden ``llave_salida`` = k(K). Las puertas que vuelven a una región menor están abiertas. Así k1 se alcanza
  sin abrir puertas y cada k(i+1) está detrás de puertas que piden k(i): oleadas 1, 2, ..., K.
- Variante no resoluble (``resoluble=False``): toda puerta que entra a una región, venga de donde venga, pide la llave
  de entrada de esa región (las que entran a R0 quedan abiertas). Así la zona de cada llave no obtenible es su propia
  región y las zonas no se solapan (para que M3 mida el caso lineal de SC-005).
  - Sin ciclo (K ≥ 2): las puertas que entran a R(K−1), donde está ``llave_salida``, están cerradas sin llave.
  - Con ciclo (K ≥ 4): R(K−3) pide k(K−1) y guarda k(K−2); R(K−2) pide k(K−2) y guarda k(K−1) (ciclo por cadena
    k(K−2) ↔ k(K−1)); R(K−1) pide k(K) y guarda k(K) (ciclo directo, la puerta K→K). Además la puerta 2→1 de R0 queda
    cerrada sin llave (no cambia lo alcanzable: 1 es la sala inicial).
  En ambas hay frontera bloqueada: las puertas que salen de lo alcanzable hacia una región cerrada.
- ``llave_de_enemigo=True``: k1 la suelta un enemigo (``enemigo`` en ``llaves_json``) que inicia en su sala.

Lo que es solo de terreno (colocar jugador y cazadores) queda en ``tests/utiles_terreno.py`` (spec 003).
"""

import json
import os
import random
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from DTOS.CriptaDetalles import CriptaDetalles
from DTOS.SalaEsqueleto import SalaEsqueleto
from DTOS.UbicacionLlave import UbicacionLlave

# Marca de «puerta cerrada que no indica llave» en `CriptaSintetica.entrada`.
SIN_LLAVE = "<sin llave>"

# Salidas por sala buscadas: 760 salidas / 300 salas.
SALIDAS_POR_SALA = 760 / 300

DIRECCIONES = ("N", "S", "E", "O")
VERSION = "v1"
PRESUPUESTO = 500
INVENTARIO_MAX = 5
JUGADOR = {"vida_max": 40, "ataque": 6, "defensa": 1, "velocidad": 100}
TIPO_ENEMIGO = "ent_guardian_sint"


class CriptaSintetica:
    """Cripta generada: datos en el formato del servicio y la estructura con que se armó."""

    def __init__(self, id_cripta, semilla, detalles_json, salas_json, llaves_json, llaves, regiones, entrada):
        self.id_cripta = id_cripta
        self.semilla = semilla
        self.detalles_json = detalles_json
        self.detalles = CriptaDetalles.desde_json(detalles_json)
        self.salas_json = salas_json
        self.llaves_json = llaves_json
        self.llaves = llaves
        self.regiones = regiones
        self.entrada = entrada

    def esqueleto(self):
        return [SalaEsqueleto.desde_json(sala) for sala in self.salas_json]

    def ubicaciones(self):
        return [UbicacionLlave.desde_json(llave) for llave in self.llaves_json]

    def region_de(self, id_sala):
        for indice in range(len(self.regiones)):
            primera, ultima = self.regiones[indice]
            if primera <= id_sala <= ultima:
                return indice
        return -1


def _validar(salas, llaves, resoluble, con_ciclo):
    if llaves < 1:
        raise ValueError("Hace falta al menos una llave")
    minimo_llaves = 1
    if not resoluble:
        minimo_llaves = 4 if con_ciclo else 2
    if llaves < minimo_llaves:
        raise ValueError(f"Esta variante necesita al menos {minimo_llaves} llaves")
    # una sala por región (dos en R0 con ciclo, por la puerta 2→1) más la sala de salida
    minimo_salas = llaves + 1 + (1 if (not resoluble and con_ciclo) else 0)
    if salas < minimo_salas:
        raise ValueError(f"Con {llaves} llaves hacen falta al menos {minimo_salas} salas")


def _posiciones(salas, ancho):
    # posicion[id] = (fila, columna) en serpentina; celda[fila][columna] = id o 0
    filas = (salas + ancho - 1) // ancho
    posicion = [None] * (salas + 1)
    celda = [[0] * ancho for _ in range(filas)]
    for id_sala in range(1, salas + 1):
        indice = id_sala - 1
        fila = indice // ancho
        columna = indice % ancho if fila % 2 == 0 else ancho - 1 - indice % ancho
        posicion[id_sala] = (fila, columna)
        celda[fila][columna] = id_sala
    return posicion, celda


def _vecino(celda, fila, columna, direccion):
    if direccion == "N":
        fila -= 1
    elif direccion == "S":
        fila += 1
    elif direccion == "E":
        columna += 1
    else:
        columna -= 1
    if fila < 0 or fila >= len(celda) or columna < 0 or columna >= len(celda[0]):
        return 0
    return celda[fila][columna]


def _direccion_hacia(posicion, origen, destino):
    fila_o, col_o = posicion[origen]
    fila_d, col_d = posicion[destino]
    if fila_d < fila_o:
        return "N"
    if fila_d > fila_o:
        return "S"
    if col_d > col_o:
        return "E"
    return "O"


def _regiones(salas, llaves):
    # salas 1..salas-1 en `llaves` regiones de ids contiguos; la última región es solo la sala de salida
    disponibles = salas - 1
    base = disponibles // llaves
    sobra = disponibles % llaves
    regiones = []
    primera = 1
    for indice in range(llaves):
        tamano = base + (1 if indice < sobra else 0)
        regiones.append((primera, primera + tamano - 1))
        primera += tamano
    regiones.append((salas, salas))
    return regiones


def _entradas(nombres, resoluble, con_ciclo):
    k = len(nombres)
    entrada = [None] * (k + 1)
    for indice in range(1, k):
        entrada[indice] = nombres[indice - 1]  # R(i) pide k(i)
    entrada[k] = nombres[k - 1]  # sala de salida: llave_salida
    if not resoluble:
        if con_ciclo:
            entrada[k - 3] = nombres[k - 2]  # R(K-3) pide k(K-1)
            entrada[k - 2] = nombres[k - 3]  # R(K-2) pide k(K-2)
            entrada[k - 1] = nombres[k - 1]  # R(K-1) pide k(K): ciclo directo
        else:
            entrada[k - 1] = SIN_LLAVE
    return entrada


def generar_cripta(semilla, salas, llaves, resoluble=True, con_ciclo=False, llave_de_enemigo=False,
                   costo_ida=1, costo_vuelta=1, id_cripta="sint"):
    """Genera una cripta sintética determinista por `semilla`. Ver el docstring del módulo."""
    _validar(salas, llaves, resoluble, con_ciclo)
    azar = random.Random(semilla)

    ancho = 1
    while ancho * ancho < salas:
        ancho += 1
    posicion, celda = _posiciones(salas, ancho)

    ancho_nombre = max(2, len(str(llaves)))
    nombres = [f"llave_{j:0{ancho_nombre}d}" for j in range(1, llaves + 1)]
    regiones = _regiones(salas, llaves)
    entrada = _entradas(nombres, resoluble, con_ciclo)

    region = [0] * (salas + 1)
    for indice in range(len(regiones)):
        primera, ultima = regiones[indice]
        for id_sala in range(primera, ultima + 1):
            region[id_sala] = indice

    # aristas no dirigidas (menor, mayor): la serpentina y vecinos verticales elegidos al azar
    aristas = [(id_sala, id_sala + 1) for id_sala in range(1, salas)]
    candidatas = []
    for id_sala in range(1, salas + 1):
        fila, columna = posicion[id_sala]
        abajo = _vecino(celda, fila, columna, "S")
        if abajo != 0 and abajo != id_sala + 1 and abajo != id_sala - 1:
            candidatas.append((id_sala, abajo) if id_sala < abajo else (abajo, id_sala))
    objetivo = round(salas * SALIDAS_POR_SALA)
    extra = (objetivo - 2 * len(aristas)) // 2
    extra = max(0, min(extra, len(candidatas)))
    aristas.extend(azar.sample(candidatas, extra))

    # salidas[id][d] = dict de la salida en la dirección DIRECCIONES[d], o None
    salidas = [[None] * len(DIRECCIONES) for _ in range(salas + 1)]

    def puerta(origen, destino, costo):
        r_origen, r_destino = region[origen], region[destino]
        llave = None
        if r_destino != r_origen and (not resoluble or r_destino > r_origen):
            llave = entrada[r_destino]
        datos = {"sala": destino, "cerrada": llave is not None}
        if llave is not None and llave != SIN_LLAVE:
            datos["llave"] = llave
        datos["costo"] = costo
        return datos

    for menor, mayor in aristas:
        d_ida = DIRECCIONES.index(_direccion_hacia(posicion, menor, mayor))
        d_vuelta = DIRECCIONES.index(_direccion_hacia(posicion, mayor, menor))
        salidas[menor][d_ida] = puerta(menor, mayor, costo_ida)
        salidas[mayor][d_vuelta] = puerta(mayor, menor, costo_vuelta)

    if not resoluble and con_ciclo:
        # la puerta 2→1 (dentro de R0) queda cerrada sin llave
        d = DIRECCIONES.index(_direccion_hacia(posicion, 2, 1))
        salidas[2][d]["cerrada"] = True
        salidas[2][d].pop("llave", None)

    salas_json = []
    for id_sala in range(1, salas + 1):
        de_la_sala = {}
        for d in range(len(DIRECCIONES)):
            if salidas[id_sala][d] is not None:
                de_la_sala[DIRECCIONES[d]] = salidas[id_sala][d]
        salas_json.append({"id": id_sala, "nombre": f"Sala {id_sala}", "salidas": de_la_sala})

    llaves_json = []
    for j in range(1, llaves + 1):
        primera, ultima = regiones[j - 1]
        ubicacion = {"id": nombres[j - 1], "sala": azar.randint(primera, ultima)}
        if llave_de_enemigo and j == 1:
            ubicacion["enemigo"] = f"e-{id_cripta}-1"
        llaves_json.append(ubicacion)

    detalles_json = {
        "id": id_cripta, "version": VERSION, "salas_total": salas, "sala_inicial": 1, "sala_salida": salas,
        "llave_salida": nombres[-1], "presupuesto_solicitudes": PRESUPUESTO, "inventario_max": INVENTARIO_MAX,
        "jugador": dict(JUGADOR),
    }
    return CriptaSintetica(id_cripta, semilla, detalles_json, salas_json, llaves_json, nombres, regiones, entrada)


def _escribir(carpeta, ruta, datos):
    archivo = os.path.join(carpeta, ruta)
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)


def escribir_paquete(carpeta, cripta, escribir_llaves=True):
    """Escribe un paquete offline de `cripta` en `carpeta` (esquema de `crear_paquete_niebla` + `llaves.json`).

    Cada llave está como objeto en su sala, salvo la que suelta un enemigo: en su sala se pone ese enemigo, cuya ficha
    del catálogo la suelta. `escribir_llaves=False` deja el paquete sin `llaves.json` (US5.3).
    """
    id_cripta = cripta.id_cripta
    objetos = [[] for _ in range(len(cripta.salas_json) + 1)]
    enemigos = [[] for _ in range(len(cripta.salas_json) + 1)]
    sueltas = []
    for ubicacion in cripta.llaves_json:
        if ubicacion.get("enemigo") is not None:
            enemigos[ubicacion["sala"]].append({"instancia": ubicacion["enemigo"], "tipo": TIPO_ENEMIGO})
            sueltas.append(ubicacion["id"])
        else:
            objetos[ubicacion["sala"]].append(ubicacion["id"])
    contenido = [{"sala": sala["id"], "enemigos": enemigos[sala["id"]], "trampas": [],
                  "objetos": objetos[sala["id"]]} for sala in cripta.salas_json]

    catalogo = [{"id": TIPO_ENEMIGO, "clase": "enemigo", "nombre": "Guardián", "vida_max": 8, "ataque": 3,
                 "defensa": 0, "velocidad": 100, "comportamiento": "guardian", "suelta": sueltas}]
    for id_llave in cripta.llaves:
        catalogo.append({"id": id_llave, "clase": "llave", "nombre": id_llave, "peso": 0, "valor": 0,
                         "abre": "puerta"})

    _escribir(carpeta, "criptas.json", {"criptas": [
        {"id": id_cripta, "nombre": f"Cripta sintética {id_cripta}", "salas": len(cripta.salas_json),
         "dificultad": "fácil"}]})
    _escribir(carpeta, f"criptas/{id_cripta}.json", cripta.detalles_json)
    _escribir(carpeta, f"criptas/{id_cripta}/version.json", {"version": cripta.detalles_json["version"]})
    _escribir(carpeta, f"criptas/{id_cripta}/salas.json", {"salas": cripta.salas_json, "total_paginas": 1})
    _escribir(carpeta, f"criptas/{id_cripta}/contenido.json", {"contenido": contenido})
    if escribir_llaves:
        _escribir(carpeta, f"criptas/{id_cripta}/llaves.json", {"llaves": cripta.llaves_json})
    _escribir(carpeta, "catalogo.json", {"entidades": catalogo})
    _escribir(carpeta, "catalogo/version.json", {"version": "cat-1"})
