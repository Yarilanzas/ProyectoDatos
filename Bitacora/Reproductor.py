# reproduccion de una partida a partir de su bitacora (S4.11)
# no pide nada al usuario ni conoce la vista, solo le entrega las acciones al motor en orden
from Bitacora.BitacoraPartida import leer_bitacora
from Persistencia.FormatoBinario import VersionIncompatible

class Reproductor:
    def __init__(self, fabrica_motor, version_cripta,
                 version_catalogo):
        self._fabrica_motor = fabrica_motor
        self._version_cripta = version_cripta
        self._version_catalogo = version_catalogo

    def reproducir(self, ruta):
        encabezado, acciones = leer_bitacora(ruta)

        if encabezado.version_cripta != self._version_cripta:
            raise VersionIncompatible("No se puede garantizar una reproduccion fiel: la versión de la cripta no coincide")

        if encabezado.version_catalogo != self._version_catalogo:
            raise VersionIncompatible("No se puede garantizar una reproducción fiel: la versión del catalogo no coincide")

        motor = self._fabrica_motor(encabezado.cripta_id, encabezado.semilla)

        if hasattr(motor, "cripta_id"):
            if motor.cripta_id != encabezado.cripta_id:
                raise VersionIncompatible("El motor creado corresponde a otra cripta" )

        for nombre, argumento in acciones:
            resultado = motor.ejecutar_accion(nombre,  argumento)

            if resultado is False:
                raise ValueError(f"La reproducción se detuvo: el motor rechazó la acción '{nombre}' con argumento '{argumento}'" )

        return motor