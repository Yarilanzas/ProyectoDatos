# Gestor sin red para los clones de la línea de tiempo (spec 004, T029; research R10; FR-008, FR-025, PR-09).
#
# Un clon se juega con un `GestorDatos` propio: sin gestor no puede jugar (una trampa o una sala sin contenido cargado
# fallan), y el gestor de la partida no sirve (sus contadores `aciertos_cache` y `fallos_cache` y su caché son de la
# partida). `GestorHistorico` lee del MISMO disco que el gestor vivo (solo lectura) y con una fuente que no tiene red:
# las versiones y los detalles de la cripta salen de valores capturados al empezar o cargar, y cualquier otro pedido lanza
# `SinDatosParaHistoria`. Si el disco tiene el dato, nunca se llega a la fuente.

from Gestor.GestorDatos import GestorDatos


class SinDatosParaHistoria(RuntimeError):
    """Falta un dato local para reconstruir (y no se puede pedir: no hay red). Subclase de `RuntimeError` para que
    `main.py` la convierta en el código de salida 1 junto con los demás errores de datos (no es «versión incompatible»)."""

    def __init__(self, que):
        super().__init__(f"No se puede reconstruir sin nuevas solicitudes: faltan datos locales ({que})")
        self.que = que


class FuenteSinRed:
    """Fuente de datos que no hace solicitudes: devuelve las versiones y los detalles capturados y lanza
    `SinDatosParaHistoria` en cualquier otro método. `solicitudes_realizadas` vale siempre 0 (mismo contador que las
    otras fuentes, para que `GestorDatos.resumen_red()` funcione)."""

    def __init__(self, id_cripta, version_cripta, version_catalogo, detalles):
        self.id_cripta = id_cripta
        self._version_cripta = version_cripta
        self._version_catalogo = version_catalogo
        self._detalles = detalles
        self.solicitudes_realizadas = 0
        self.ultima_falta = None  # la última SinDatosParaHistoria lanzada, aunque alguien la haya atrapado

    def _faltan(self, que):
        """Registra y devuelve la excepción. El motor atrapa los `RuntimeError` al cargar una sala y rechaza el paso
        (``No se pudo cargar la sala destino``): la línea necesita saber que la causa fue un dato local que falta."""
        self.ultima_falta = SinDatosParaHistoria(que)
        return self.ultima_falta

    def obtener_version_cripta(self, id_cripta):
        if id_cripta != self.id_cripta:
            raise self._faltan(f"versión de la cripta {id_cripta}")
        return self._version_cripta

    def obtener_version_catalogo(self):
        return self._version_catalogo

    def obtener_detalles_cripta(self, id_cripta):
        if id_cripta != self.id_cripta:
            raise self._faltan(f"detalles de la cripta {id_cripta}")
        return self._detalles

    def list_criptas(self):
        raise self._faltan("lista de criptas")

    def obtener_llaves_cripta(self, id_cripta):
        raise self._faltan(f"llaves de la cripta {id_cripta}")

    def obtener_esqueleto_cripta(self, id_cripta):
        raise self._faltan(f"esqueleto de la cripta {id_cripta}")

    def obtener_contenido_sala(self, id_cripta, ids_salas):
        raise self._faltan(f"contenido de las salas {', '.join(str(i) for i in ids_salas)} de la cripta {id_cripta}")

    def obtener_fichas_catalogo(self, ids_fichas):
        raise self._faltan(f"fichas del catálogo {', '.join(str(i) for i in ids_fichas)}")

    def _obtener(self, ruta, params=None):
        raise self._faltan(ruta)


class GestorHistorico(GestorDatos):
    """``GestorDatos`` con ``FuenteSinRed`` que comparte el ``almacenamiento_disco`` del gestor vivo, sin compartir
    contadores ni caché de fichas con él. Ya viene con la cripta iniciada (``iniciar_cripta``), así que ``asegurar_sala``
    sirve las salas desde el disco.

    Construcción: ``GestorHistorico.desde_gestor(gestor_vivo, id_cripta)`` captura las versiones y los detalles del
    gestor vivo (que ya los tiene al empezar o cargar la partida). Un solo clon vivo a la vez por gestor
    (``estado_juego`` es único).
    """

    def __init__(self, almacenamiento_disco, id_cripta, version_cripta, version_catalogo, detalles, cache_size=25):
        super().__init__(FuenteSinRed(id_cripta, version_cripta, version_catalogo, detalles),
                         ruta_base=almacenamiento_disco.ruta_base, cache_size=cache_size)
        self.almacenamiento_disco = almacenamiento_disco  # el mismo objeto del gestor vivo: solo se lee
        self.iniciar_cripta(id_cripta)

    def tomar_falta(self):
        """Devuelve (y olvida) la última ``SinDatosParaHistoria`` que lanzó la fuente, o None. La línea la usa tras rehacer
        una acción: si el clon rechazó un paso porque faltaba un dato local, la causa es esta, no una divergencia."""
        falta = self.fuente.ultima_falta
        self.fuente.ultima_falta = None
        return falta

    @classmethod
    def desde_gestor(cls, gestor, id_cripta, cache_size=25):
        return cls(gestor.almacenamiento_disco, id_cripta, gestor.version_cripta(id_cripta),
                   gestor.version_catalogo(), gestor.obtener_detalles(id_cripta), cache_size)
