# Reproduccion de una partida a partir de su bitacora (S4.11)
# no pide nada al usuario ni conoce la vista, solo le entrega las acciones al motor en orden
from Bitacora.BitacoraPartida import CARGAR, leer_bitacora
from Persistencia.FormatoBinario import VersionIncompatible

class Reproductor:
    # recargar(motor) -> motor: repite lo que hizo la carga real de la partida (FR-017, PR-12).
    # Sin recargar, una bitacora con "@cargar" da error: no se puede ignorar sin perder fidelidad.
    # observador (opcional, pedido de Persona D, P-D02 de la spec 004): recibe al_crear_motor(motor),
    # despues_de_accion(motor, nombre, argumento) por cada accion aceptada y despues_de_carga(motor) con el
    # motor nuevo tras cada @cargar. Sin observador, todo es igual que antes (contracts/formato-bitacora.md)
    def __init__(self, fabrica_motor, version_cripta,
                 version_catalogo, recargar=None, observador=None):
        self._fabrica_motor = fabrica_motor
        self._version_cripta = version_cripta
        self._version_catalogo = version_catalogo
        self._recargar = recargar
        self._observador = observador

    def reproducir(self, ruta):
        encabezado, acciones = leer_bitacora(ruta)
        return self.reproducir_acciones(encabezado, acciones)

    def reproducir_acciones(self, encabezado, acciones):
        # reproduce en memoria lo que devuelve leer_bitacora: (encabezado, [(nombre, argumento), ...])
        if encabezado.version_cripta != self._version_cripta:
            raise VersionIncompatible("No se puede garantizar una reproduccion fiel: la versión de la cripta no coincide")

        if encabezado.version_catalogo != self._version_catalogo:
            raise VersionIncompatible("No se puede garantizar una reproducción fiel: la versión del catalogo no coincide")

        motor = self._fabrica_motor(encabezado.cripta_id, encabezado.semilla)

        if hasattr(motor, "cripta_id"):
            if motor.cripta_id != encabezado.cripta_id:
                raise VersionIncompatible("El motor creado corresponde a otra cripta" )

        observador = self._observador
        if observador is not None:
            observador.al_crear_motor(motor)

        for nombre, argumento in acciones:
            if nombre == CARGAR:
                if self._recargar is None:
                    raise ValueError("La reproducción se detuvo: la bitácora tiene @cargar y no hay cómo recargar la partida")
                motor = self._recargar(motor)
                if motor is None:
                    raise ValueError("La reproducción se detuvo: @cargar no devolvió un motor")
                if observador is not None:
                    observador.despues_de_carga(motor)  # el motor nuevo; recargar ya cerró el anterior
                continue

            resultado = motor.ejecutar_accion(nombre,  argumento)

            if resultado is False:
                raise ValueError(f"La reproducción se detuvo: el motor rechazó la acción '{nombre}' con argumento '{argumento}'" )

            if observador is not None:
                observador.despues_de_accion(motor, nombre, argumento)

        return motor