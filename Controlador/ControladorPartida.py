# Controlador (MVC): recibe los comandos del jugador, se los pasa al motor
# y deja constancia de cada accion aceptada en la bitacora (S4.11)
# Tambien guarda y carga la partida en el archivo binario (S4.10)
# La vista solo muestra; el motor solo simula; aqui se decide que se hace con cada comando

import os
import random
import shutil

from Bitacora.BitacoraPartida import BitacoraPartida
from Gestor.PreparadorPartida import preparar_partida, cargar_partida
from Modelo.rutas_ir_a import primer_paso
from Modelo.Viaje import (DANO, DESTINO, ENEMIGOS, RECHAZO_ACTUAL, RECHAZO_SIN_RUTA, SIN_RUTA)
from Persistencia.ArchivoPartida import guardar_partida
from Persistencia.ConversorPartida import (RestauradorPartida, registros_desde_motor, registro_jugador_desde_motor,
                                           registro_conocimiento_desde_motor)
from Persistencia.FormatoBinario import VersionIncompatible
from Persistencia.TablaPuntajes import TablaPuntajes, Puntaje, CRITERIOS_PUNTAJES

# acciones del motor que consumen tiempo y por eso van a la bitacora
ACCIONES = ("mover", "abrir", "atacar", "recoger", "soltar", "equipar", "usar", "esperar", "retroceder")
ATAJOS = {"n": ("mover", "N"), "s": ("mover", "S"), "e": ("mover", "E"), "o": ("mover", "O")}
CRITERIOS_INVENTARIO = ("peso", "valor", "nombre")
ARCHIVO_GUARDADO = "partida.cripta"
PUNTAJES_EN_PANTALLA = 10  # cuantos puntajes se muestran al terminar una partida o con el comando puntajes

# errores esperables al guardar o cargar: se muestran al jugador sin cerrar el juego
ERRORES_ARCHIVO = (VersionIncompatible, ValueError, RuntimeError, OSError)


def ruta_bitacora_de(ruta_guardado):
    # junto a cada partida guardada va una copia de su bitacora, asi el --replay
    # sigue funcionando para las partidas que se cargan y se continuan
    return ruta_guardado + ".log"


def guardar_motor(motor, ruta, gestor):
    """Guarda el motor en `ruta` (CRPT 3), sin vista ni bitácora: lo usan `guardar` y la recarga del
    --replay (FR-015, FR-017, PR-12).

    Si el motor viene de una partida cargada, su archivo se cierra antes de reemplazarlo (en Windows no se
    puede reemplazar un archivo abierto) y el motor queda leyendo las salas pendientes del archivo nuevo.
    """
    # primero se arma todo en memoria (puede leer salas pendientes del archivo cargado)
    registros = registros_desde_motor(motor)
    jugador = registro_jugador_desde_motor(motor)
    conocimiento = registro_conocimiento_desde_motor(motor)  # FR-015

    anterior = motor.restaurador
    ruta_lectura = None
    if anterior is not None:
        ruta_lectura = anterior.ruta
        anterior.cerrar()
        motor.restaurador = None

    try:
        guardar_partida(
            ruta, motor.cripta_id,
            gestor.version_cripta(motor.cripta_id), gestor.version_catalogo(),
            motor.semilla, motor.reloj, registros, jugador, conocimiento=conocimiento,
        )
        if anterior is not None:
            ruta_lectura = ruta  # las salas pendientes ahora estan en el archivo nuevo
    finally:
        if ruta_lectura is not None:
            motor.restaurador = RestauradorPartida(ruta_lectura)


def _misma_ruta(ruta_a, ruta_b):
    # normcase: en Windows X.LOG y x.log son el mismo archivo
    return os.path.normcase(os.path.abspath(ruta_a)) == os.path.normcase(os.path.abspath(ruta_b))


def _rechazar_bitacora_del_guardado(ruta_bitacora, ruta_guardado):
    """La bitácora activa no puede ser la copia de bitácora de un guardado (`<guardado>.log`): `@cargar`
    asume que esa copia termina en el guardado. Error de uso (FR-017, pedido de Persona D, FR-030 de la spec
    004, contracts/comandos.md). ValueError: main.py lo muestra como «! Error: ...» con código 1 al cargar,
    y en la partida el comando se rechaza sin cerrar el juego."""
    copia = ruta_bitacora_de(ruta_guardado)
    if _misma_ruta(ruta_bitacora, copia):
        raise ValueError(f"la bitácora no puede ser {copia}, que es la copia de bitácora de la partida "
                         "guardada; use otra con --bitacora")


def _texto_rechazo_ir(rechazo):
    # avisos de contracts/comandos.md; el de sala desconocida es uno solo para no revelar si existe
    if rechazo == RECHAZO_ACTUAL:
        return "Ya estás en esa sala."
    if rechazo == RECHAZO_SIN_RUTA:
        return "No conoces una ruta hasta esa sala."
    return "No conoces esa sala."


def _texto_parada(viaje):
    # motivo de parada (FR-027). El fin de partida lo muestra el flujo normal, y un paso rechazado ya
    # mostro el mensaje de `mover`: en esos dos casos no se agrega nada
    if viaje.motivo == DANO:
        return "Viaje detenido: recibiste daño."
    if viaje.motivo == ENEMIGOS:
        return "Viaje detenido: hay enemigos en la sala."
    if viaje.motivo == DESTINO:
        return f"Llegaste a la sala {viaje.destino.id}."
    if viaje.motivo == SIN_RUTA:
        return "Viaje detenido: ya no conoces una ruta."
    return None


class ControladorPartida:

    # ruta_puntajes=None no registra nada: asi las pruebas y el --replay no escriben la tabla
    def __init__(self, gestor, vista, ruta_bitacora="partida.log", ruta_puntajes=None):
        self.gestor = gestor
        self.vista = vista
        self.ruta_bitacora = ruta_bitacora
        self.tabla_puntajes = TablaPuntajes(ruta_puntajes) if ruta_puntajes else None
        self.motor = None
        self.bitacora = None
        # búsqueda de la ruta de «ir a»; las pruebas la reemplazan por un buscador de prueba (PR-10)
        self.buscar_ruta = primer_paso

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
        self.vista.mostrar_aviso(f"Partida nueva en {cripta_id} (semilla {semilla})")

    def cargar(self, ruta):
        _rechazar_bitacora_del_guardado(self.ruta_bitacora, ruta)  # antes de cargar y de tocar la bitácora
        motor = cargar_partida(ruta, self.gestor)  # valida version de cripta y catalogo

        self._cerrar()
        self.motor = motor
        self.bitacora = self._continuar_bitacora(ruta)
        self.vista.mostrar_aviso(f"Partida cargada desde {ruta}")

    def _continuar_bitacora(self, ruta_guardado):
        copia = ruta_bitacora_de(ruta_guardado)

        if not os.path.exists(copia):
            self.vista.mostrar_aviso("La partida no tiene bitácora: lo que se juegue ahora no se podrá reproducir con --replay")
            return None

        # se continua sobre una copia, asi la bitacora guardada no cambia (cargar ya rechazo que sean la misma)
        shutil.copyfile(copia, self.ruta_bitacora)

        bitacora, encabezado = BitacoraPartida.continuar(self.ruta_bitacora)

        if encabezado.cripta_id != self.motor.cripta_id or encabezado.semilla != self.motor.semilla:
            bitacora.cerrar()
            self.vista.mostrar_aviso("La bitácora no corresponde a esta partida; no se usará")
            return None

        # el --replay repite aqui la carga: guarda y vuelve a cargar el motor (FR-017, contracts/formato-bitacora.md)
        bitacora.marcar_carga()
        return bitacora

    # guardado

    def guardar(self, ruta):
        motor = self.motor

        if motor.estado_partida() != "en_curso":
            self.vista.mostrar_aviso("La partida terminó; ya no se puede guardar")
            return False

        _rechazar_bitacora_del_guardado(self.ruta_bitacora, ruta)  # antes de escribir nada
        guardar_motor(motor, ruta, self.gestor)

        if self.bitacora is not None:
            shutil.copyfile(self.ruta_bitacora, ruta_bitacora_de(ruta))

        self.vista.mostrar_aviso(f"Partida guardada en {ruta}")
        return True

    # comandos

    def _accion(self, nombre, argumento, comentario=None):
        # la direccion se normaliza aqui para que la bitacora guarde lo mismo que el motor uso.
        # `comentario` va a la bitacora justo antes de la linea de la accion, y solo si el motor la acepto
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
            self.vista.mostrar_aviso("No se pudo realizar esa acción")
            return False

        # solo se anota lo que el motor acepto: el --replay debe repetir exactamente esto
        if self.bitacora is not None:
            if comentario is not None:
                self.bitacora.comentar(comentario)
            self.bitacora.registrar(nombre, argumento)
        return True

    def _ir(self, argumento):
        # «ir a <sala>» (FR-021): una sucesion de `mover` ordinarios. Cada paso pasa por _accion, asi que
        # cuesta lo mismo, cuenta como accion, corren los eventos y se anota en la bitacora (FR-025, FR-030)
        partes = argumento.split(maxsplit=1)
        if len(partes) != 2 or partes[0].lower() != "a":
            self.vista.mostrar_error("Use: ir a <sala>")
            return

        try:
            viaje, rechazo = self.motor.preparar_viaje(partes[1], self.buscar_ruta)
        except NotImplementedError:
            # temporal hasta T065: la busqueda real es Modelo/BusquedaRuta.py de Persona A (D-PEND-01)
            self.vista.mostrar_aviso("«ir a» aún no está disponible.")
            return

        if viaje is None:
            # un rechazo no consume tiempo ni va a la bitacora (FR-022, SC-005)
            self.vista.mostrar_aviso(_texto_rechazo_ir(rechazo))
            return

        # "# ir a <sala>" va inmediatamente antes del primer `mover`, despues de que el motor lo acepte:
        # si lo rechaza no queda ninguna linea (FR-030, SC-005). El --replay ignora el comentario
        comentario = f"ir a {viaje.destino.id}"
        while True:
            paso = viaje.siguiente_paso()
            if paso is None:
                break
            # si el motor rechaza el paso, _accion ya muestra el mismo mensaje que daria `mover` (FR-027f)
            aceptado = self._accion("mover", paso.direccion, comentario)
            if aceptado:
                comentario = None
            if viaje.terminar_paso(aceptado) is not None:
                break

        aviso = _texto_parada(viaje)
        if aviso is not None:
            self.vista.mostrar_aviso(aviso)

    def _inventario(self, criterio):
        criterio = criterio or "nombre"
        if criterio not in CRITERIOS_INVENTARIO:
            self.vista.mostrar_error("El criterio debe ser peso, valor o nombre")
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
        elif comando == "ir":
            self._ir(argumento)
        elif comando == "mapa":
            # consulta, igual que inventario: no consume tiempo ni va a la bitacora (FR-018, FR-019)
            self.vista.mostrar_mapa(self.motor.mapa_conocido())
        elif comando == "mensajes":
            self.vista.mostrar_mensajes(self.motor.mensajes.ultimos())
        elif comando == "red":
            self.vista.mostrar_red(self.gestor.resumen_red())
        elif comando == "puntajes":
            self.mostrar_puntajes(argumento.lower())
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
                    self.registrar_puntaje()
                    break

                linea = self.vista.pedir_comando()
                if linea is None or not self.ejecutar(linea):
                    break
        finally:
            self._cerrar()

    # tabla de puntajes (S2.12)

    def registrar_puntaje(self):
        # se pide el nombre al terminar, asi tambien sirve para las partidas que se cargaron
        if self.tabla_puntajes is None:
            return

        nombre = self.vista.pedir_texto("Nombre para la tabla de puntajes: ")
        puntaje = Puntaje.desde_resumen(
            nombre, self.motor.cripta_id,
            self.gestor.version_cripta(self.motor.cripta_id), self.motor.resumen_puntaje(),
        )

        try:
            self.tabla_puntajes.registrar(puntaje)
        except OSError as error:
            self.vista.mostrar_error(f"No se pudo registrar el puntaje: {error}")
            return

        self.vista.mostrar_aviso(f"Puntaje registrado en {self.tabla_puntajes.ruta}")
        self.mostrar_puntajes("mejores")

    def mostrar_puntajes(self, criterio=""):
        criterio = criterio or "mejores"
        if criterio not in CRITERIOS_PUNTAJES:
            self.vista.mostrar_error(f"El criterio debe ser uno de: {', '.join(CRITERIOS_PUNTAJES)}")
            return
        if self.tabla_puntajes is None:
            self.vista.mostrar_aviso("Esta sesión no tiene tabla de puntajes")
            return

        try:
            puntajes = self.tabla_puntajes.ordenados(criterio)
        except (ValueError, OSError) as error:
            self.vista.mostrar_error(f"No se pudo leer la tabla de puntajes: {error}")
            return
        self.vista.mostrar_puntajes(puntajes[:PUNTAJES_EN_PANTALLA], criterio)

    def _cerrar(self):
        if self.bitacora is not None:
            self.bitacora.cerrar()
            self.bitacora = None
        if self.motor is not None and self.motor.restaurador is not None:
            self.motor.restaurador.cerrar()
            self.motor.restaurador = None
