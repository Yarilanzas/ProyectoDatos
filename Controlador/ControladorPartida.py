# Controlador (MVC): recibe los comandos del jugador, se los pasa al motor
# y deja constancia de cada accion aceptada en la bitacora (S4.11)
# Tambien guarda y carga la partida en el archivo binario (S4.10)
# La vista solo muestra; el motor solo simula; aqui se decide qué se hace con cada comando

import os
import random
import shutil

from Bitacora.BitacoraPartida import BitacoraPartida
from Gestor.PreparadorPartida import preparar_partida, cargar_partida
from Persistencia.ArchivoPartida import guardar_partida
from Persistencia.ConversorPartida import (RestauradorPartida, registros_desde_motor, registro_jugador_desde_motor)
from Persistencia.FormatoBinario import VersionIncompatible

# acciones del motor que consumen tiempo y por eso van a la bitacora
ACCIONES = ("mover", "abrir", "atacar", "recoger", "soltar", "equipar", "usar", "esperar", "retroceder")
ATAJOS = {"n": ("mover", "N"), "s": ("mover", "S"), "e": ("mover", "E"), "o": ("mover", "O")}
CRITERIOS_INVENTARIO = ("peso", "valor", "nombre")
ARCHIVO_GUARDADO = "partida.cripta"

# errores esperables al guardar o cargar: se muestran al jugador sin cerrar el juego
ERRORES_ARCHIVO = (VersionIncompatible, ValueError, RuntimeError, OSError)


def ruta_bitacora_de(ruta_guardado):
    # junto a cada partida guardada va una copia de su bitacora, asi el --replay
    # sigue funcionando para las partidas que se cargan y se continuan
    return ruta_guardado + ".log"


def _misma_ruta(ruta_a, ruta_b):
    return os.path.abspath(ruta_a) == os.path.abspath(ruta_b)


class ControladorPartida:

    def __init__(self, gestor, vista, ruta_bitacora="partida.log"):
        self.gestor = gestor
        self.vista = vista
        self.ruta_bitacora = ruta_bitacora
        self.motor = None
        self.bitacora = None

    # inicio de partida

    def elegir_cripta(self):
        criptas = self.gestor.listar_criptas()
        self.vista.mostrar_criptas(criptas)
        respuesta = self.vista.pedir_texto("ID de la cripta: ")
        return None if respuesta is None else respuesta.strip()

    def nueva_partida(self, cripta_id, semilla=None):
        if semilla is None:
            semilla = random.randrange(2 ** 31)

        motor = preparar_partida(cripta_id, semilla, self.gestor)

        self._cerrar()
        self.motor = motor
        self.bitacora = BitacoraPartida(
            self.ruta_bitacora, cripta_id,
            self.gestor.version_cripta(cripta_id), self.gestor.version_catalogo(), semilla,
        )
        self.vista.mostrar_aviso(f"Partida nueva en {cripta_id} (semilla {semilla}).")

    def cargar(self, ruta):
        motor = cargar_partida(ruta, self.gestor)  # valida version de cripta y catalogo

        self._cerrar()
        self.motor = motor
        self.bitacora = self._continuar_bitacora(ruta)
        self.vista.mostrar_aviso(f"Partida cargada desde {ruta}.")

    def _continuar_bitacora(self, ruta_guardado):
        copia = ruta_bitacora_de(ruta_guardado)

        if not os.path.exists(copia):
            self.vista.mostrar_aviso("La partida no tiene bitácora: lo que se juegue ahora "
                                     "no se podrá reproducir con --replay.")
            return None

        # se continua sobre una copia, asi la bitacora guardada no cambia
        if not _misma_ruta(copia, self.ruta_bitacora):
            shutil.copyfile(copia, self.ruta_bitacora)

        bitacora, encabezado = BitacoraPartida.continuar(self.ruta_bitacora)

        if encabezado.cripta_id != self.motor.cripta_id or encabezado.semilla != self.motor.semilla:
            bitacora.cerrar()
            self.vista.mostrar_aviso("La bitácora no corresponde a esta partida; no se usará.")
            return None

        return bitacora

    # guardado

    def guardar(self, ruta):
        motor = self.motor

        if motor.estado_partida() != "en_curso":
            self.vista.mostrar_aviso("La partida terminó; ya no se puede guardar.")
            return False

        # primero se arma todo en memoria (puede leer salas pendientes del archivo cargado)
        registros = registros_desde_motor(motor)
        jugador = registro_jugador_desde_motor(motor)

        # el archivo cargado se cierra antes de reemplazarlo (en Windows no se puede reemplazar un archivo abierto) y se vuelve a abrir al terminar
        anterior = motor.restaurador
        ruta_lectura = None
        if anterior is not None:
            ruta_lectura = anterior.ruta
            anterior.cerrar()
            motor.restaurador = None

        try:
            guardar_partida(
                ruta, motor.cripta_id,
                self.gestor.version_cripta(motor.cripta_id), self.gestor.version_catalogo(),
                motor.semilla, motor.reloj, registros, jugador,
            )
            if anterior is not None:
                ruta_lectura = ruta  # las salas pendientes ahora estan en el archivo nuevo
        finally:
            if ruta_lectura is not None:
                motor.restaurador = RestauradorPartida(ruta_lectura)

        if self.bitacora is not None and not _misma_ruta(self.ruta_bitacora, ruta_bitacora_de(ruta)):
            shutil.copyfile(self.ruta_bitacora, ruta_bitacora_de(ruta))

        self.vista.mostrar_aviso(f"Partida guardada en {ruta}.")
        return True

    # comandos

    def _accion(self, nombre, argumento):
        # la direccion se normaliza aqui para que la bitacora guarde lo mismo que el motor uso
        if nombre in ("mover", "abrir"):
            argumento = argumento.upper()
        if nombre in ("esperar", "retroceder"):
            argumento = ""

        try:
            aceptada = self.motor.ejecutar_accion(nombre, argumento)
        except RuntimeError as error:
            self.vista.mostrar_error(str(error))
            return False

        if not aceptada:
            self.vista.mostrar_aviso("No se pudo realizar esa acción.")
            return False

        # solo se anota lo que el motor acepto: el --replay debe repetir exactamente esto
        if self.bitacora is not None:
            self.bitacora.registrar(nombre, argumento)
        return True

    def _inventario(self, criterio):
        criterio = criterio or "nombre"
        if criterio not in CRITERIOS_INVENTARIO:
            self.vista.mostrar_error("El criterio debe ser peso, valor o nombre.")
            return

        inventario = self.motor.jugador.inventario
        nodos, _ = inventario.vista_ordenada(criterio)
        self.vista.mostrar_inventario_ordenado(nodos, criterio, inventario)

    def ejecutar(self, linea):
        # devuelve False cuando el jugador quiere salir
        partes = linea.strip().split(maxsplit=1)
        if not partes:
            return True

        comando = partes[0].lower()
        argumento = partes[1].strip() if len(partes) > 1 else ""

        if comando in ATAJOS:
            comando, argumento = ATAJOS[comando]

        if comando == "salir":
            return False

        if comando in ACCIONES:
            self._accion(comando, argumento)
        elif comando == "ayuda":
            self.vista.mostrar_ayuda()
        elif comando == "inventario":
            self._inventario(argumento.lower())
        elif comando == "mensajes":
            self.vista.mostrar_mensajes(self.motor.mensajes.ultimos())
        elif comando == "red":
            self.vista.mostrar_red(self.gestor.resumen_red())
        elif comando == "guardar":
            try:
                self.guardar(argumento or ARCHIVO_GUARDADO)
            except ERRORES_ARCHIVO as error:
                self.vista.mostrar_error(f"No se pudo guardar: {error}")
        elif comando == "cargar":
            try:
                self.cargar(argumento or ARCHIVO_GUARDADO)
            except ERRORES_ARCHIVO as error:
                self.vista.mostrar_error(f"No se pudo cargar: {error}")
        else:
            self.vista.mostrar_error(f"Comando desconocido '{comando}'. Escriba 'ayuda'.")

        return True

    def jugar(self):
        self.vista.mostrar_bienvenida()
        try:
            while True:
                self.vista.mostrar_estado(self.motor)

                if self.motor.estado_partida() != "en_curso":
                    self.vista.mostrar_fin(self.motor.resumen_puntaje(),self.gestor.resumen_red())
                   # self.vista
                    break

                linea = self.vista.pedir_comando()
                if linea is None or not self.ejecutar(linea):
                    break
        finally:
            self._cerrar()

    def _cerrar(self):
        if self.bitacora is not None:
            self.bitacora.cerrar()
            self.bitacora = None
        if self.motor is not None and self.motor.restaurador is not None:
            self.motor.restaurador.cerrar()
            self.motor.restaurador = None