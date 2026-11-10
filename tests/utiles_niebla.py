# Utilidades de prueba de la capacidad de niebla de guerra, mapa conocido e «ir a».
# Este archivo no lleva prefijo test: `unittest discover` no lo ejecuta.
# Crean un paquete offline en una carpeta temporal (no hace falta red).
# Atiende: SC-001, PR-16.

import os
import sys

# Permite ejecutar este archivo desde cualquier carpeta (PyCharm, unittest o pytest).
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from API.Fuentes import FuenteDatosOffline
from Controlador.ControladorPartida import ControladorPartida
from Gestor.GestorDatos import GestorDatos
from tests.test_integracion import VistaFalsa, _escribir

CRIPTA_NIEBLA = "cripta-niebla"
LLAVE = "itm_llave"
ANTORCHA = "itm_antorcha"
PERGAMINO = "itm_pergamino"
ANTIDOTO = "itm_antidoto"
ENEMIGO = "ent_rata"
# Más lenta que el jugador: al entrar a su sala, el jugador vuelve a actuar antes de que ella ataque.
# Sirve para probar la parada por enemigos (FR-027b) sin que la tape la de daño (FR-027c).
ENEMIGO_LENTO = "ent_babosa"
TRAMPA = "trp_dardos"
JUGADOR = {"vida_max": 40, "ataque": 6, "defensa": 1, "velocidad": 100}

CATALOGO_NIEBLA = [
    {"id": ENEMIGO, "clase": "enemigo", "nombre": "Rata", "vida_max": 8, "ataque": 3, "defensa": 0,
     "velocidad": 100, "comportamiento": "guardian"},
    {"id": ENEMIGO_LENTO, "clase": "enemigo", "nombre": "Babosa", "vida_max": 8, "ataque": 3, "defensa": 0,
     "velocidad": 25, "comportamiento": "guardian"},
    {"id": LLAVE, "clase": "llave", "nombre": "Llave", "peso": 0, "valor": 0, "abre": "puerta"},
    {"id": ANTORCHA, "clase": "antorcha", "nombre": "Antorcha", "peso": 1, "valor": 2, "duracion": 1000},
    {"id": PERGAMINO, "clase": "pergamino_retroceso", "nombre": "Pergamino", "peso": 0, "valor": 10},
    {"id": ANTIDOTO, "clase": "antidoto", "nombre": "Antídoto", "peso": 1, "valor": 3},
    {"id": TRAMPA, "clase": "trampa", "nombre": "Dardos", "daño": 3, "rearme": 300},
]


def salida(sala, costo=None, cerrada=False, llave=None, cierre_automatico=None):
    # Una salida del esqueleto. Sin `costo`, la clave no se escribe (vale 100, FR-005).
    datos = {"sala": sala}
    if costo is not None:
        datos["costo"] = costo
    if cerrada:
        datos["cerrada"] = True
    if llave is not None:
        datos["llave"] = llave
    if cierre_automatico is not None:
        datos["cierre_automatico"] = cierre_automatico
    return datos


def contenido_sala(sala, enemigos=(), trampas=(), objetos=(), tipo_enemigo=ENEMIGO):
    # `enemigos` y `trampas` son ids de instancia; el tipo es `tipo_enemigo` y TRAMPA.
    return {
        "sala": sala,
        "enemigos": [{"instancia": instancia, "tipo": tipo_enemigo} for instancia in enemigos],
        "trampas": [{"instancia": instancia, "tipo": TRAMPA} for instancia in trampas],
        "objetos": list(objetos),
    }


def crear_paquete_niebla(carpeta, salas, contenido=(), sala_inicial=None, sala_salida=None,
                         llave_salida=None, jugador=None, inventario_max=5, llaves=None, escribir_llaves=True):
    """Genera un paquete offline con el formato de `crear_paquete_offline`.

    `salas` es la lista del esqueleto: {"id", "nombre", "salidas": {dirección: salida(...)}}.
    `contenido` trae solo las salas que tienen algo: las demás quedan vacías.
    Por defecto se empieza en la primera sala y se sale por la última.

    `llaves` es la lista de `criptas/<id>/llaves.json` en el formato del servicio ({"id", "sala", "enemigo"
    opcional}); si es None, `llave_salida` en la sala inicial, o ninguna si la cripta no declara `llave_salida`.
    `escribir_llaves=False` deja el paquete sin ese archivo (spec 002, US5.3; FR-024, FR-028).
    """
    ids = [sala["id"] for sala in salas]
    inicial = ids[0] if sala_inicial is None else sala_inicial
    if llaves is None:
        llaves = [] if llave_salida is None else [{"id": llave_salida, "sala": inicial}]
    declaradas = [c["sala"] for c in contenido]
    vacias = [contenido_sala(id_sala) for id_sala in ids if id_sala not in declaradas]

    _escribir(carpeta, "criptas.json", {"criptas": [
        {"id": CRIPTA_NIEBLA, "nombre": "Cripta de niebla", "salas": len(salas), "dificultad": "fácil"}]})
    _escribir(carpeta, f"criptas/{CRIPTA_NIEBLA}.json", {
        "id": CRIPTA_NIEBLA, "version": "v1", "salas_total": len(salas),
        "sala_inicial": inicial,
        "sala_salida": ids[-1] if sala_salida is None else sala_salida,
        "llave_salida": llave_salida, "presupuesto_solicitudes": 500, "inventario_max": inventario_max,
        "jugador": JUGADOR if jugador is None else jugador})
    _escribir(carpeta, f"criptas/{CRIPTA_NIEBLA}/version.json", {"version": "v1"})
    _escribir(carpeta, f"criptas/{CRIPTA_NIEBLA}/salas.json", {"salas": salas, "total_paginas": 1})
    _escribir(carpeta, f"criptas/{CRIPTA_NIEBLA}/contenido.json", {"contenido": list(contenido) + vacias})
    if escribir_llaves:
        _escribir(carpeta, f"criptas/{CRIPTA_NIEBLA}/llaves.json", {"llaves": list(llaves)})
    _escribir(carpeta, "catalogo.json", {"entidades": CATALOGO_NIEBLA})
    _escribir(carpeta, "catalogo/version.json", {"version": "cat-1"})


def partida_niebla(carpeta, salas, contenido=(), semilla=7, veneno=0, **opciones):
    """Crea el paquete y empieza una partida. Devuelve (motor, controlador).

    El controlador usa VistaFalsa, y la cache y la bitácora quedan dentro de `carpeta`.
    Ningún dato del paquete envenena, así que `veneno` es el daño que se le aplica al jugador
    al empezar. `opciones` va tal cual a `crear_paquete_niebla`.
    """
    paquete = os.path.join(carpeta, "paquete")
    crear_paquete_niebla(paquete, salas, contenido, **opciones)

    gestor = GestorDatos(FuenteDatosOffline(paquete), ruta_base=os.path.join(carpeta, "cache"), cache_size=25)
    controlador = ControladorPartida(gestor, VistaFalsa(), os.path.join(carpeta, "partida.log"))
    controlador.nueva_partida(CRIPTA_NIEBLA, semilla)

    motor = controlador.motor
    if veneno:
        motor.aplicar_veneno(motor.jugador, veneno)
    return motor, controlador


# Orden de desempate entre dos salidas hacia la misma vecina con igual costo (FR-024, P-03).
ORDEN_DIRECCIONES = ("N", "S", "E", "O")


def _indice_direccion(direccion):
    for indice in range(len(ORDEN_DIRECCIONES)):
        if ORDEN_DIRECCIONES[indice] == direccion:
            return indice
    return len(ORDEN_DIRECCIONES)


def _etiqueta_menor(a, b):
    # Etiquetas (costo total, id de la primera vecina, índice de la dirección del primer paso).
    for indice in range(3):
        if a[indice] != b[indice]:
            return a[indice] < b[indice]
    return False


def buscador_prueba(grafo, origen, destino):
    """Buscador de prueba con la firma de `primer_paso` (contracts/interfaz-ruta.md). T042.

    Enumera todas las rutas simples por profundidad y se queda con la de etiqueta menor:
    (costo total, id de la primera vecina, dirección del primer paso en el orden N, S, E, O).
    Cumple las obligaciones 1 a 3 del contrato (FR-022, FR-024).

    Complejidad: exponencial en el peor caso (todas las rutas simples). Es solo una utilidad de
    prueba para grafos pequeños: no es candidata a implementación ni se mide en M4.
    """
    from Modelo.rutas_ir_a import Paso

    visitada = [False] * grafo.cantidad_salas
    visitada[grafo.ordinal(origen)] = True
    mejor = [None, None]  # [etiqueta, (dirección, vecina)]

    def recorrer(sala, costo, primero):
        if sala is destino:
            etiqueta = (costo, primero[1].id, _indice_direccion(primero[0]))
            if mejor[0] is None or _etiqueta_menor(etiqueta, mejor[0]):
                mejor[0], mejor[1] = etiqueta, primero
            return

        for direccion, vecina, costo_arista in grafo.aristas(sala):
            ordinal = grafo.ordinal(vecina)
            if visitada[ordinal]:
                continue
            visitada[ordinal] = True
            recorrer(vecina, costo + costo_arista, primero if primero is not None else (direccion, vecina))
            visitada[ordinal] = False

    recorrer(origen, 0, None)

    if mejor[0] is None:
        return None
    return Paso(mejor[1][0], mejor[1][1], mejor[0][0])
