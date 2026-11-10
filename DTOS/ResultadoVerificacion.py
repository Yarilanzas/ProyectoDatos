# Resultado de la verificación de resolubilidad (spec 002, data-model.md §3).
# Solo datos, sin lógica: cruza del modelo a la vista y al controlador (Principio II).
# Todas las listas llegan ya ordenadas: la vista no ordena nada.


class LlaveOrdenada:
    """Una llave del orden de obtención (FR-007): oleada en que se obtiene y si es la llave de salida."""

    def __init__(self, id_llave: str, oleada: int, es_salida: bool):
        self.id_llave = id_llave
        self.oleada = oleada
        self.es_salida = es_salida


class PuertaReporte:
    """Una salida del reporte (frontera o puertas hacia la sala de salida, FR-009).

    `llave` es None cuando la puerta está cerrada sin indicar llave («sin llave»).
    """

    def __init__(self, origen: int, direccion: str, destino: int, destino_existe: bool, llave: "str | None"):
        self.origen = origen
        self.direccion = direccion
        self.destino = destino
        self.destino_existe = destino_existe
        self.llave = llave


class LugarLlave:
    """Un lugar donde está una llave (FR-010). `enemigo` es None si está en la sala y no la suelta un enemigo."""

    def __init__(self, sala: int, sala_existe: bool, enemigo: "str | None"):
        self.sala = sala
        self.sala_existe = sala_existe
        self.enemigo = enemigo


class UbicacionesLlave:
    """Todos los lugares de una llave, por sala y luego enemigo (FR-010, FR-014).

    `lugares` vacía = ubicación desconocida.
    """

    def __init__(self, id_llave: str, lugares: list):
        self.id_llave = id_llave
        self.lugares = lugares


class DependenciaLlave:
    """La llave de la que depende una llave no obtenible (FR-011). `depende_de` None = sin dependencia."""

    def __init__(self, id_llave: str, depende_de: "str | None"):
        self.id_llave = id_llave
        self.depende_de = depende_de


class CicloLlaves:
    """Un ciclo de dependencias (FR-011).

    `llaves` empieza por la menor y no repite la primera al final; `directo` es True si es K -> K.
    """

    def __init__(self, llaves: list, directo: bool):
        self.llaves = llaves
        self.directo = directo


class ResultadoVerificacion:
    """Resultado completo de una verificación (FR-006 a FR-011, FR-014).

    - `orden` (si es resoluble): lista de LlaveOrdenada por oleada y luego id.
    - Si no es resoluble: `no_obtenibles` (ids, por id), `frontera` y `puertas_salida` (PuertaReporte, por sala de
      origen y dirección), `existe_puerta_salida`, `ubicaciones` (UbicacionesLlave, por id), `dependencias`
      (DependenciaLlave, por id) y `ciclos` (CicloLlaves, por la menor llave de cada ciclo).
    """

    def __init__(self, cripta_id: str, resoluble: bool, sala_salida: int, llave_salida: str,
                 orden=None, no_obtenibles=None, frontera=None, puertas_salida=None,
                 existe_puerta_salida: bool = True, ubicaciones=None, dependencias=None, ciclos=None):
        self.cripta_id = cripta_id
        self.resoluble = resoluble
        self.sala_salida = sala_salida
        self.llave_salida = llave_salida
        self.orden = [] if orden is None else orden
        self.no_obtenibles = [] if no_obtenibles is None else no_obtenibles
        self.frontera = [] if frontera is None else frontera
        self.puertas_salida = [] if puertas_salida is None else puertas_salida
        self.existe_puerta_salida = existe_puerta_salida
        self.ubicaciones = [] if ubicaciones is None else ubicaciones
        self.dependencias = [] if dependencias is None else dependencias
        self.ciclos = [] if ciclos is None else ciclos
