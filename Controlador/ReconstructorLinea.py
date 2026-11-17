# Reconstrucción de la línea de tiempo al cargar una partida (spec 004, T083; FR-022, FR-025, FR-030; research R8 y R10).
#
# El archivo guarda el **guion** de la línea (`RegistroLinea`), no los puntos de control. Para entregar la línea viva,
# este módulo reproduce el guion desde la cripta y la semilla del encabezado con `Reproductor.reproducir_acciones` y un
# `ObservadorLinea`, con un gestor histórico que solo lee del disco (nunca pide nada a la red, Principio VII). Cada
# `@cargar` del guion se repite como lo hace el replay: se guarda el motor en un temporal y se vuelve a cargar.
#
# Qué se verifica (cualquier diferencia es `VersionIncompatible: la línea de tiempo no coincide con la partida`, código 2,
# y no se carga nada):
#
#   1. El guion reproducido da el mismo registro que el guardado: mismas acciones y, en cada una, el mismo sello
#      `(reloj, secuencia)` de la decisión previa; los retrocesos dejan las mismas acciones vigentes.
#   2. Al final, reloj, sala, vida y acciones del motor reproducido coinciden con el encabezado y el bloque del jugador.
#
# Si falta un dato local que el disco debería tener, se lanza `SinDatosParaHistoria` (código 1): no se puede reproducir
# sin pedirlo a la red. En ambos casos no queda nada: ni la carpeta temporal ni las copias.
#
# Archivos propios: una carpeta temporal por reconstrucción (`carpeta`) donde viven las copias privadas del archivo de cada
# época (las que hace el observador al repetir cada carga y la de la carga actual). Los temporales de las recargas viven
# en una subcarpeta que se borra al terminar, después de cerrar los restauradores (en Windows no se puede borrar un archivo
# abierto). `cerrar()` borra el resto, también después de cerrar el clon que la línea tenga abierto sobre una copia.
#
# Complejidad: reproducir el guion cuesta O(n · a + C · S) (n acciones del guion, a el costo de una acción, C puntos de
# control y S el tamaño del estado); memoria O(n + C · S) para la línea que se entrega.

import os
import shutil
import tempfile

from Bitacora.BitacoraPartida import CARGAR
from Bitacora.Reproductor import Reproductor
from Controlador.ObservadorLinea import ObservadorLinea
from Gestor.GestorHistorico import GestorHistorico
from Gestor.PreparadorPartida import cargar_partida, preparar_partida
from Modelo.LineaTiempo import ErrorReconstruccion, K_POR_OMISION, LineaTiempo
from Persistencia.ConversorPartida import RestauradorPartida
from Persistencia.FormatoBinario import VersionIncompatible
from Persistencia.RegistroLinea import ACCION, RETROCESO

NO_COINCIDE = "la línea de tiempo no coincide con la partida"
SUBCARPETA_RECARGAS = "recargas"


def _cerrar_restaurador(motor):
    if motor is not None and motor.restaurador is not None:
        motor.restaurador.cerrar()
        motor.restaurador = None


def acciones_del_guion(registro):
    """El guion como lista de pares `(nombre, argumento)` que entiende `Reproductor.reproducir_acciones`: una carga es
    `@cargar` y un retroceso es `retroceder`. O(n)."""
    acciones = []
    for entrada in registro.registros:
        if entrada[0] == ACCION:
            acciones.append((entrada[1], entrada[2]))
        elif entrada[0] == RETROCESO:
            acciones.append(("retroceder", ""))
        else:
            acciones.append((CARGAR, ""))
    return acciones


class ReconstructorLinea:
    """Rehace la línea de una partida guardada. Un reconstructor sirve a una partida cargada a la vez: `reconstruir`
    borra lo de la reconstrucción anterior, y `cerrar` borra todo lo que creó (idempotente).

    `gestor` es el gestor de datos de la partida (el mismo que usa `cargar_partida`): de él salen las versiones actuales y
    los datos capturados para el gestor histórico."""

    def __init__(self, gestor):
        self._gestor = gestor
        self._carpeta = None
        self._observador = None

    @property
    def carpeta(self):
        """Carpeta temporal propia de la reconstrucción vigente, o None si no hay (todavía, o ya se cerró o falló)."""
        return self._carpeta

    @property
    def observador(self):
        """`ObservadorLinea` de la línea entregada (dueño de las copias privadas de sus épocas), o None."""
        return self._observador

    def reconstruir(self, registro, encabezado, jugador, motor_cargado=None, k=K_POR_OMISION):
        """Entrega la `LineaTiempo` de la partida guardada.

        - `registro`: el `RegistroLinea` del archivo, o None si `largo línea = 0`.
        - `encabezado` y `jugador`: `EncabezadoPartida` y `RegistroJugador` del mismo archivo.
        - `motor_cargado`: el motor que devolvió `cargar_partida` con ese archivo. Si se pasa, la línea queda lista para
          seguir jugando con él: se agrega la carga (`CARGA` al guion, punto de control del motor cargado y época con la
          copia privada del archivo). Con `registro = None` es obligatorio: la línea empieza en la carga.
        - `k`: solo se usa con `registro = None` (sin K guardado rige el de la ejecución); si no, rige el K guardado
          (FR-031).

        `VersionIncompatible` si el guion no coincide con la partida; `SinDatosParaHistoria` si falta un dato local.
        Ante cualquier error no queda ninguna carpeta ni copia. O(n · a + C · S)."""
        if registro is None and motor_cargado is None:
            raise ValueError("Sin bloque de línea hace falta el motor cargado: la línea empieza en la carga")
        self.cerrar()
        historico = GestorHistorico.desde_gestor(self._gestor, encabezado.cripta_id)
        try:
            self._carpeta = tempfile.mkdtemp(prefix="cripta_linea_")
            if registro is None:
                linea = self._linea_desde_la_carga(historico, motor_cargado, k)
            else:
                linea = self._reproducir(registro, encabezado, jugador, historico)
                if motor_cargado is not None:
                    self._observador.despues_de_carga(motor_cargado)
            return linea
        except BaseException:
            self.cerrar()
            raise

    def _linea_desde_la_carga(self, historico, motor_cargado, k):
        linea = LineaTiempo(k, historico, RestauradorPartida)
        self._observador = ObservadorLinea(linea, self._carpeta)
        self._observador.al_crear_motor(motor_cargado)
        linea.epocas_ruta[0] = self._observador.copiar_archivo_cargado(motor_cargado)
        return linea

    def _reproducir(self, registro, encabezado, jugador, historico):
        # `Reproductor` pide las versiones ACTUALES: si no coinciden con las del archivo lanza VersionIncompatible
        gestor = self._gestor
        linea = LineaTiempo(registro.k, historico, RestauradorPartida)
        self._observador = ObservadorLinea(linea, self._carpeta)
        recargas = os.path.join(self._carpeta, SUBCARPETA_RECARGAS)
        os.mkdir(recargas)
        abiertos = []  # motores que pueden tener un temporal abierto

        def fabrica_motor(cripta_id, semilla):
            return preparar_partida(cripta_id, semilla, historico)

        def recargar(motor):
            # lo mismo que `ejecutar_replay` de main.py: se repite la carga real (guardar y volver a cargar)
            from Controlador.ControladorPartida import guardar_motor  # aquí y no arriba: el controlador importa este módulo
            temporal = os.path.join(recargas, f"recarga_{len(abiertos)}.cripta")
            guardar_motor(motor, temporal, historico)
            _cerrar_restaurador(motor)  # el motor anterior ya no se usa
            nuevo = cargar_partida(temporal, historico)
            abiertos.append(nuevo)
            return nuevo

        reproductor = Reproductor(fabrica_motor, gestor.version_cripta(encabezado.cripta_id), gestor.version_catalogo(),
                                  recargar=recargar, observador=self._observador)
        historico.tomar_falta()  # olvida una falta anterior a esta reproducción
        try:
            try:
                motor = reproductor.reproducir_acciones(encabezado, acciones_del_guion(registro))
                self._verificar(motor, registro, linea, encabezado, jugador)
            except (ValueError, ErrorReconstruccion) as error:
                # el motor atrapa un dato local que falta y rechaza el paso: la causa es esa, no una divergencia
                falta = historico.tomar_falta()
                if falta is not None:
                    raise falta from error
                raise VersionIncompatible(NO_COINCIDE) from error
        finally:
            for motor in abiertos:
                _cerrar_restaurador(motor)
            shutil.rmtree(recargas, ignore_errors=True)
        return linea

    @staticmethod
    def _verificar(motor, registro, linea, encabezado, jugador):
        if linea.a_registro() != registro or not linea.sincronizada(motor):
            raise VersionIncompatible(NO_COINCIDE)
        if (motor.reloj != encabezado.reloj
                or motor.jugador.sala.id != jugador.sala_id
                or motor.jugador.vida != jugador.vida
                or motor.acciones_jugador != jugador.acciones):
            raise VersionIncompatible(NO_COINCIDE)

    def cerrar(self):
        """Borra lo que creó: cierra el clon que la línea tenga abierto sobre una copia, borra las copias privadas y la
        carpeta temporal. Idempotente. La línea que entregó deja de servir. O(L)."""
        if self._observador is not None:
            self._observador.linea.cerrar()  # suelta el clon (y su archivo) antes de borrar
            self._observador.cerrar()
            self._observador = None
        if self._carpeta is not None:
            shutil.rmtree(self._carpeta, ignore_errors=True)
            self._carpeta = None
