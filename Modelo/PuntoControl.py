# Punto de control de la línea de tiempo (spec 004, T015; data-model.md#puntocontrol; FR-017, FR-021, PR-02).
# Principio I: solo listas y campos; sin dict ni set como índice.


class _SinRastro:
    """Centinela de `foto_rastros`: «esta sala no tenía el atributo `rastro`» (nunca visitada). Es distinto de `None`,
    porque `actualizar_rastro` crea el atributo y su deshacer lo borra: una sala puede no tenerlo (HL3)."""

    __slots__ = ()

    def __repr__(self):
        return "SIN_RASTRO"


SIN_RASTRO = _SinRastro()


class PuntoControl:
    """Copia del motor real en una decisión del jugador, más la foto de lo que cuelga del esqueleto.

    - ``estado``: copia de ``MotorSimulacion`` hecha por ``CopiaEstado.copiar``. **Nunca se ejecuta directamente**: sus
      salas y salidas son las del motor real (compartidas); solo se ejecuta un clon ``materializar``-ado.
    - ``foto_rastros``: ``Sala.rastro`` por ordinal de sala (``SIN_RASTRO`` si la sala no tenía el atributo).
    - ``foto_cerradas``: ``Salida.cerrada`` (``bool``) por ordinal de salida, en el orden de recorrido de las salas.
    - ``accion``, ``reloj``, ``secuencia``: posición y sello de la decisión.
    - ``epoca``: índice de la época a la que pertenece.

    ``ciclo`` y ``version_puertas`` (enteros del motor que solo crecen) viajan dentro de ``estado``: no se guardan aparte.
    """

    __slots__ = ("estado", "foto_rastros", "foto_cerradas", "accion", "reloj", "secuencia", "epoca")

    def __init__(self, estado, foto_rastros, foto_cerradas, accion, reloj, secuencia, epoca=0):
        self.estado = estado
        self.foto_rastros = foto_rastros
        self.foto_cerradas = foto_cerradas
        self.accion = accion
        self.reloj = reloj
        self.secuencia = secuencia
        self.epoca = epoca
