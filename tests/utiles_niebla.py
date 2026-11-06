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
TRAMPA = "trp_dardos"
JUGADOR = {"vida_max": 40, "ataque": 6, "defensa": 1, "velocidad": 100}

CATALOGO_NIEBLA = [
    {"id": ENEMIGO, "clase": "enemigo", "nombre": "Rata", "vida_max": 8, "ataque": 3, "defensa": 0,
     "velocidad": 100, "comportamiento": "guardian"},
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


def contenido_sala(sala, enemigos=(), trampas=(), objetos=()):
    # `enemigos` y `trampas` son ids de instancia; el tipo es ENEMIGO y TRAMPA.
    return {
        "sala": sala,
        "enemigos": [{"instancia": instancia, "tipo": ENEMIGO} for instancia in enemigos],
        "trampas": [{"instancia": instancia, "tipo": TRAMPA} for instancia in trampas],
        "objetos": list(objetos),
    }


def crear_paquete_niebla(carpeta, salas, contenido=(), sala_inicial=None, sala_salida=None,
                         llave_salida=None, jugador=None, inventario_max=5):
    """Genera un paquete offline con el formato de `crear_paquete_offline`.

    `salas` es la lista del esqueleto: {"id", "nombre", "salidas": {dirección: salida(...)}}.
    `contenido` trae solo las salas que tienen algo: las demás quedan vacías.
    Por defecto se empieza en la primera sala y se sale por la última.
    """
    ids = [sala["id"] for sala in salas]
    declaradas = [c["sala"] for c in contenido]
    vacias = [contenido_sala(id_sala) for id_sala in ids if id_sala not in declaradas]

    _escribir(carpeta, "criptas.json", {"criptas": [
        {"id": CRIPTA_NIEBLA, "nombre": "Cripta de niebla", "salas": len(salas), "dificultad": "fácil"}]})
    _escribir(carpeta, f"criptas/{CRIPTA_NIEBLA}.json", {
        "id": CRIPTA_NIEBLA, "version": "v1", "salas_total": len(salas),
        "sala_inicial": ids[0] if sala_inicial is None else sala_inicial,
        "sala_salida": ids[-1] if sala_salida is None else sala_salida,
        "llave_salida": llave_salida, "presupuesto_solicitudes": 500, "inventario_max": inventario_max,
        "jugador": JUGADOR if jugador is None else jugador})
    _escribir(carpeta, f"criptas/{CRIPTA_NIEBLA}/version.json", {"version": "v1"})
    _escribir(carpeta, f"criptas/{CRIPTA_NIEBLA}/salas.json", {"salas": salas, "total_paginas": 1})
    _escribir(carpeta, f"criptas/{CRIPTA_NIEBLA}/contenido.json", {"contenido": list(contenido) + vacias})
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
