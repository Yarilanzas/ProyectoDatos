# Pruebas de integracion: motor (A) + gestor (B) + inventario (C)
# detras del controlador, con guardado binario, bitacora y --replay
# Usan un paquete offline pequeño creado en una carpeta temporal (no hace falta red)

import json
import os
import tempfile
import unittest

from API.Fuentes import FuenteDatosOffline
from Bitacora.BitacoraPartida import leer_bitacora
from Controlador.ControladorPartida import ControladorPartida, ruta_bitacora_de
from Gestor.GestorDatos import GestorDatos
from Gestor.PreparadorPartida import preparar_partida, cargar_partida
from Modelo.Inventario import Inventario, NodoInventario
from Persistencia.ArchivoPartida import LectorPartida, guardar_partida
from Persistencia.FormatoBinario import VersionIncompatible
from Persistencia.RegistroJugador import RegistroJugador
from main import ejecutar_replay

CRIPTA = "cripta-test"

# mapa:  1 -E- 2 -E- 3 -E(cerrada, llave)- 4 (salida)
#             |
#             S
#             5
SALAS = [
    {"id": 1, "nombre": "Entrada", "salidas": {"E": {"sala": 2}}},
    {"id": 2, "nombre": "Pasillo", "salidas": {"O": {"sala": 1}, "E": {"sala": 3}, "S": {"sala": 5}}},
    {"id": 3, "nombre": "Antecámara", "salidas": {
        "O": {"sala": 2}, "E": {"sala": 4, "cerrada": True, "llave": "itm_llave_salida"}}},
    {"id": 4, "nombre": "Salida", "salidas": {"O": {"sala": 3}}},
    {"id": 5, "nombre": "Nido", "salidas": {"N": {"sala": 2}}},
]

CONTENIDO = [
    {"sala": 1, "enemigos": [], "trampas": [], "objetos": ["itm_daga", "itm_pocion", "itm_pergamino"]},
    {"sala": 2, "enemigos": [{"instancia": "e-rata-1", "tipo": "ent_rata"}],
     "trampas": [{"instancia": "t-dardos-1", "tipo": "trp_dardos"}], "objetos": ["itm_llave_salida"]},
    {"sala": 3, "enemigos": [{"instancia": "e-rata-2", "tipo": "ent_rata", "vida": 4}], "trampas": [], "objetos": []},
    {"sala": 4, "enemigos": [], "trampas": [], "objetos": []},
    {"sala": 5, "enemigos": [{"instancia": "e-murcielago-1", "tipo": "ent_murcielago"}], "trampas": [], "objetos": []},
]

CATALOGO = [
    {"id": "ent_rata", "clase": "enemigo", "nombre": "Rata", "vida_max": 8, "ataque": 3, "defensa": 0,
     "velocidad": 100, "comportamiento": "guardian", "suelta": ["itm_pocion"]},
    {"id": "ent_murcielago", "clase": "enemigo", "nombre": "Murciélago", "vida_max": 5, "ataque": 2,
     "defensa": 0, "velocidad": 150, "comportamiento": "errante"},
    {"id": "itm_daga", "clase": "arma", "nombre": "Daga", "peso": 2, "valor": 5, "ataque_bonus": 3},
    {"id": "itm_pocion", "clase": "pocion", "nombre": "Poción", "peso": 1, "valor": 3, "cura": 10},
    {"id": "itm_pergamino", "clase": "pergamino_retroceso", "nombre": "Pergamino", "peso": 0, "valor": 10},
    {"id": "itm_llave_salida", "clase": "llave", "nombre": "Llave de salida", "peso": 0, "valor": 0, "abre": "4"},
    {"id": "trp_dardos", "clase": "trampa", "nombre": "Dardos", "daño": 3, "rearme": 300},
]


def _escribir(carpeta, ruta, datos):
    archivo = os.path.join(carpeta, ruta)
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)


def crear_paquete_offline(carpeta, version_cripta="v1", version_catalogo="cat-1"):
    _escribir(carpeta, "criptas.json", {"criptas": [
        {"id": CRIPTA, "nombre": "Cripta de prueba", "salas": 5, "dificultad": "fácil"}]})
    _escribir(carpeta, f"criptas/{CRIPTA}.json", {
        "id": CRIPTA, "version": version_cripta, "salas_total": 5, "sala_inicial": 1, "sala_salida": 4,
        "llave_salida": "itm_llave_salida", "presupuesto_solicitudes": 500, "inventario_max": 5,
        "jugador": {"vida_max": 40, "ataque": 6, "defensa": 1, "velocidad": 100}})
    _escribir(carpeta, f"criptas/{CRIPTA}/version.json", {"version": version_cripta})
    _escribir(carpeta, f"criptas/{CRIPTA}/salas.json", {"salas": SALAS, "total_paginas": 1})
    _escribir(carpeta, f"criptas/{CRIPTA}/contenido.json", {"contenido": CONTENIDO})
    _escribir(carpeta, "catalogo.json", {"entidades": CATALOGO})
    _escribir(carpeta, "catalogo/version.json", {"version": version_catalogo})


class VistaFalsa:
    # misma interfaz que VistaConsola, pero guarda lo que se mostraria
    def __init__(self):
        self.lineas = []

    def __getattr__(self, nombre):
        if nombre.startswith("mostrar"):
            return lambda *args: self.lineas.append((nombre, args))
        raise AttributeError(nombre)

    def pedir_texto(self, mensaje):
        return None

    def pedir_comando(self):
        return None


# recoge en la entrada, se equipa, cruza al pasillo (dispara la trampa) y mata la rata de un golpe
# Termina en reloj 300: la trampa sigue desarmada (se rearma en 400) y el botin queda en el suelo
COMANDOS_PARTIDA = [
    f"recoger obj-{CRIPTA}-1-itm_daga-0",
    f"equipar obj-{CRIPTA}-1-itm_daga-0",
    f"recoger obj-{CRIPTA}-1-itm_pocion-1",
    "e",
    "atacar e-rata-1",
]


class BaseIntegracion(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.paquete = os.path.join(self.carpeta.name, "paquete")
        crear_paquete_offline(self.paquete)
        self.ruta_log = os.path.join(self.carpeta.name, "partida.log")
        self.ruta_guardado = os.path.join(self.carpeta.name, "partida.cripta")

    def tearDown(self):
        self.carpeta.cleanup()

    def nuevo_gestor(self, nombre_cache="cache"):
        fuente = FuenteDatosOffline(self.paquete)
        return GestorDatos(fuente, ruta_base=os.path.join(self.carpeta.name, nombre_cache), cache_size=25)

    def jugar(self, comandos, semilla=7):
        controlador = ControladorPartida(self.nuevo_gestor(), VistaFalsa(), self.ruta_log)
        controlador.nueva_partida(CRIPTA, semilla)
        for comando in comandos:
            controlador.ejecutar(comando)
        return controlador


class PruebasPartidaNueva(BaseIntegracion):

    def test_preparar_partida_carga_sala_inicial(self):
        motor = preparar_partida(CRIPTA, 1, self.nuevo_gestor())
        self.assertEqual(motor.jugador.sala.id, 1)
        self.assertEqual(motor.jugador.vida, 40)
        self.assertEqual(len(motor.obtener_objetos_suelo(motor.jugador.sala)), 3)
        self.assertEqual(motor.semilla, 1)

    def test_offline_entrega_la_ficha_pedida(self):
        # antes, el modo offline devolvia la primera ficha del catalogo completo
        gestor = self.nuevo_gestor()
        self.assertEqual(gestor.obtener_ficha("trp_dardos").id, "trp_dardos")
        self.assertEqual(gestor.obtener_ficha("itm_pocion").id, "itm_pocion")
        self.assertGreater(gestor.resumen_red().solicitudes, 0)

    def test_comandos_mueven_y_combaten(self):
        controlador = self.jugar(COMANDOS_PARTIDA)
        motor = controlador.motor
        self.assertEqual(motor.jugador.sala.id, 2)
        self.assertLess(motor.jugador.vida, 40)  # trampa de dardos al entrar
        self.assertEqual(motor.jugador.inventario.arma_equipada().tipo_id, "itm_daga")
        controlador._cerrar()

    def test_bitacora_solo_tiene_acciones_aceptadas(self):
        controlador = self.jugar(COMANDOS_PARTIDA + ["atacar e-rata-1", "mover X", "inventario peso", "ayuda"])
        controlador._cerrar()
        _, acciones = leer_bitacora(self.ruta_log)
        self.assertEqual(acciones[3], ("mover", "E"))
        self.assertNotIn(("mover", "X"), acciones)  # rechazadas por el motor (la rata ya murio)
        self.assertEqual(len(acciones), len(COMANDOS_PARTIDA))

    def test_partida_ganada(self):
        comandos = COMANDOS_PARTIDA + [
            "recoger obj-cripta-test-2-itm_llave_salida-0", "e", "atacar e-rata-2", "abrir E", "e"]
        controlador = self.jugar(comandos)
        self.assertEqual(controlador.motor.estado_partida(), "victoria")
        controlador._cerrar()


class PruebasReplay(BaseIntegracion):

    def test_replay_reproduce_el_mismo_estado(self):
        controlador = self.jugar(COMANDOS_PARTIDA)
        esperado = controlador.motor.obtener_estado_resumen()
        controlador._cerrar()

        motor = ejecutar_replay(self.ruta_log, self.nuevo_gestor("cache_replay"), VistaFalsa())
        self.assertEqual(motor.obtener_estado_resumen(), esperado)

    def test_replay_detecta_catalogo_incompatible(self):
        self.jugar(COMANDOS_PARTIDA)._cerrar()
        crear_paquete_offline(self.paquete, version_catalogo="cat-2")
        with self.assertRaises(VersionIncompatible):
            ejecutar_replay(self.ruta_log, self.nuevo_gestor("cache_nueva"), VistaFalsa())


class PruebasGuardado(BaseIntegracion):

    def guardar_partida_jugada(self):
        # devuelve el motor de la partida original ya guardada (bitacora cerrada)
        controlador = self.jugar(COMANDOS_PARTIDA)
        self.assertTrue(controlador.guardar(self.ruta_guardado))
        controlador._cerrar()
        return controlador.motor

    def test_cargar_restaura_jugador_y_sala(self):
        original = self.guardar_partida_jugada()
        cargado = cargar_partida(self.ruta_guardado, self.nuevo_gestor())

        self.assertEqual(cargado.reloj, original.reloj)
        self.assertEqual(cargado.jugador.sala.id, original.jugador.sala.id)
        self.assertEqual(cargado.jugador.vida, original.jugador.vida)
        self.assertEqual([n.instancia_id for n in cargado.jugador.inventario],
                         [n.instancia_id for n in original.jugador.inventario])
        self.assertEqual(cargado.jugador.inventario.arma_equipada().instancia_id,
                         original.jugador.inventario.arma_equipada().instancia_id)
        self.assertEqual(cargado.acciones_jugador, original.acciones_jugador)
        self.assertEqual(cargado.enemigos_derrotados, original.enemigos_derrotados)

        sala = cargado.jugador.sala
        self.assertEqual([n.instancia_id for n in cargado.obtener_objetos_suelo(sala)],
                         [n.instancia_id for n in original.obtener_objetos_suelo(original.jugador.sala)])
        # la trampa ya se disparo: sigue desarmada
        self.assertFalse(cargado._obtener_estado_trampa("t-dardos-1"))
        cargado.restaurador.cerrar()

    def test_carga_perezosa_solo_lee_la_sala_actual(self):
        self.guardar_partida_jugada()
        motor = cargar_partida(self.ruta_guardado, self.nuevo_gestor())

        # salas 1 y 2 estan guardadas, pero solo se restauro la sala del jugador
        self.assertEqual(motor._salas_contenido_cargado, [2])
        self.assertLess(motor.restaurador.lector.bytes_leidos, os.path.getsize(self.ruta_guardado))

        # al volver a la sala 1 se lee del archivo (sin los objetos que ya se recogieron)
        motor.ejecutar_accion("mover", "O")
        self.assertEqual([n.tipo_id for n in motor.obtener_objetos_suelo(motor.jugador.sala)],
                         ["itm_pergamino"])
        motor.restaurador.cerrar()

    def test_guardar_otra_vez_conserva_salas_no_visitadas(self):
        self.guardar_partida_jugada()
        controlador = ControladorPartida(self.nuevo_gestor(), VistaFalsa(), self.ruta_log)
        controlador.cargar(self.ruta_guardado)

        # se guarda encima del mismo archivo sin haber visitado la sala 1
        controlador.guardar(self.ruta_guardado)
        with LectorPartida(self.ruta_guardado) as lector:
            self.assertEqual(lector.ids_salas(), [1, 2])
            objetos = lector.leer_sala(1).objetos
        self.assertEqual([tipo for _, tipo in objetos], ["itm_pergamino"])
        controlador._cerrar()

    def test_cargar_continua_la_bitacora(self):
        self.guardar_partida_jugada()
        controlador = ControladorPartida(self.nuevo_gestor(), VistaFalsa(), self.ruta_log)
        controlador.cargar(self.ruta_guardado)
        controlador.ejecutar("esperar")
        controlador._cerrar()

        _, acciones = leer_bitacora(self.ruta_log)
        self.assertEqual(len(acciones), len(COMANDOS_PARTIDA) + 1)
        # la copia guardada junto a la partida no cambia
        _, guardadas = leer_bitacora(ruta_bitacora_de(self.ruta_guardado))
        self.assertEqual(len(guardadas), len(COMANDOS_PARTIDA))

    def test_cargar_detecta_cripta_incompatible(self):
        self.guardar_partida_jugada()
        crear_paquete_offline(self.paquete, version_cripta="v2")
        with self.assertRaises(VersionIncompatible):
            cargar_partida(self.ruta_guardado, self.nuevo_gestor("cache_nueva"))

    def test_controlador_no_se_cae_con_archivo_invalido(self):
        controlador = self.jugar([])
        with open(self.ruta_guardado, "wb") as archivo:
            archivo.write(b"esto no es una partida" + bytes(300))
        self.assertTrue(controlador.ejecutar(f"cargar {self.ruta_guardado}"))
        self.assertEqual(controlador.vista.lineas[-1][0], "mostrar_error")
        controlador._cerrar()


class PruebasRegistroJugador(unittest.TestCase):

    def crear(self):
        inventario = Inventario(5)
        inventario.recoge(NodoInventario("obj-1", "itm_daga", "Daga", 2, 5, "arma", 3, 0))
        inventario.recoge(NodoInventario("obj-2", "itm_pocion", "Poción", 1, 3, "pocion"))
        inventario.equipar_actual()
        return RegistroJugador(2, 31, 9, 1, False, inventario)

    def test_ida_y_vuelta(self):
        leido = RegistroJugador.from_bytes(self.crear().to_bytes())
        self.assertEqual((leido.sala_id, leido.vida, leido.acciones, leido.derrotados, leido.llave_usada),
                         (2, 31, 9, 1, False))
        self.assertEqual([n.instancia_id for n in leido.inventario], ["obj-1", "obj-2"])
        self.assertEqual(leido.inventario.arma_equipada().instancia_id, "obj-1")

    def test_registro_truncado(self):
        with self.assertRaises(ValueError):
            RegistroJugador.from_bytes(self.crear().to_bytes()[:-1])

    def test_archivo_con_jugador(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "p.bin")
            guardar_partida(ruta, "c", "v", "cat", 1, 10, [], self.crear())
            with LectorPartida(ruta) as lector:
                self.assertEqual(lector.leer_jugador().vida, 31)
                self.assertEqual(lector.leer_todas_salas(), [])

    def test_archivo_sin_jugador(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "p.bin")
            guardar_partida(ruta, "c", "v", "cat", 1, 10, [])
            with LectorPartida(ruta) as lector:
                self.assertIsNone(lector.leer_jugador())


if __name__ == "__main__":
    unittest.main()