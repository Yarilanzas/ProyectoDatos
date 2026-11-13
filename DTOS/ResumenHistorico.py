# DTO del estado pasado que muestran `historia` y `--replay --hasta` (spec 004, T030; data-model.md#resumenhistorico-dto;
# FR-006, FR-007, PR-07). Cruza de modelo a vista (Principio II): es de solo lectura y no guarda referencias al motor.
# Las secuencias son tuplas; `mapa` es el DTO MapaConocido de la capacidad 001 (también sin referencias al motor).

REFERENCIA_INSTANTE = "instante"   # ("instante", t)
REFERENCIA_ACCION = "accion"       # ("accion", k)
REFERENCIA_ACTUAL = "actual"       # ("actual", None)
REFERENCIA_FINAL = "final"         # ("final", None)

EFECTO_VENENO = "VENENO"                  # detalle: (daño, intervalo, fin)
EFECTO_VELOCIDAD = "FIN_VELOCIDAD"        # detalle: (cambio de velocidad, fin)
EFECTO_ANTORCHA = "APAGAR_ANTORCHA"       # detalle: (instante en que se apaga o None si no hay evento,)


class ResumenHistorico:
    """Campos (data-model.md):

    - ``referencia``: ``("instante", t)``, ``("accion", k)``, ``("actual", None)`` o ``("final", None)``.
    - ``reloj``: el consultado, no el del último evento ejecutado.
    - ``sala``: ``(id, nombre)``.
    - ``vida``, ``vida_max``, ``ataque``, ``defensa``, ``velocidad``.
    - ``arma``, ``armadura``: nombre del equipo o ``None``.
    - ``inventario``: tupla de ``(nombre, cantidad)`` en el orden del inventario.
    - ``efectos``: tupla de ``(tipo, detalle)`` del jugador (veneno, velocidad temporal, antorcha).
    - ``enemigos``: tupla de ``(id, tipo, vida, vida_max)`` de los vivos en la sala, por id.
    - ``mapa``: ``MapaConocido``.
    - ``resultado``: ``"victoria"``, ``"derrota"`` o ``None`` (solo en un estado final terminado).
    """

    __slots__ = ("referencia", "reloj", "sala", "vida", "vida_max", "ataque", "defensa", "velocidad", "arma",
                 "armadura", "inventario", "efectos", "enemigos", "mapa", "resultado", "_congelado")

    def __init__(self, referencia, reloj, sala, vida, vida_max, ataque, defensa, velocidad, arma, armadura,
                 inventario, efectos, enemigos, mapa, resultado):
        self.referencia = tuple(referencia)
        self.reloj = reloj
        self.sala = tuple(sala)
        self.vida = vida
        self.vida_max = vida_max
        self.ataque = ataque
        self.defensa = defensa
        self.velocidad = velocidad
        self.arma = arma
        self.armadura = armadura
        self.inventario = tuple(inventario)
        self.efectos = tuple(efectos)
        self.enemigos = tuple(enemigos)
        self.mapa = mapa
        self.resultado = resultado
        object.__setattr__(self, "_congelado", True)

    def __setattr__(self, nombre, valor):
        if getattr(self, "_congelado", False):
            raise AttributeError("ResumenHistorico es de solo lectura")
        object.__setattr__(self, nombre, valor)
