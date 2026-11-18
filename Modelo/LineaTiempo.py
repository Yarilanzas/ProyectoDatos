# Núcleo de la línea de tiempo (spec 004, T017; data-model.md#lineatiempo; FR-016, FR-017, FR-018, FR-021, PR-03).
#
# Guion, historia vigente, puntos de control, sellos, consultas, retroceso (T047), serie de pergaminos (T046), épocas y
# cargas (T082: `registrar_carga`), paso a datos (`a_registro`, `desde_registro`, T082) y contador de lo rehecho por la
# última consulta (`acciones_rehechas`, T096). Principio I: todo son listas paralelas; sin dict ni set como
# índice, sin bisect, sorted, sort, heapq ni collections. Principio II: no importa red, archivos ni consola; lo externo
# (gestor histórico, apertura de copias privadas) se inyecta. Lo único que importa de `Persistencia/` es la clase de datos
# `RegistroLinea` (solo `struct`): `a_registro` la arma y la guarda el archivo; la reconstrucción la hace el controlador.
#
# Complejidad (n acciones vigentes, K acciones entre puntos, S tamaño del estado vivo, N/E salas y salidas,
# C puntos de control):
#
#   | Operación          | Tiempo                         | Memoria                  |
#   |--------------------|--------------------------------|--------------------------|
#   | iniciar            | O(S + N + E)                   | O(S) + O(N + E)          |
#   | registrar_accion   | O(1), más O(S + N + E) cada K  | O(1), más O(S) + O(N + E) cada K |
#   | sello_de           | O(1)                           | O(1)                     |
#   | registrar_retroceso| O(V + S + N + E)               | O(S) + O(N + E)          |
#   | registrar_carga    | O(S + N + E)                   | O(S) + O(N + E), más la copia privada |
#   | a_registro         | O(n_guion)                     | O(n_guion)               |
#   | desde_registro     | O(n_guion)                     | O(n_guion)               |
#   | cerrar             | O(L)                           | O(L)                     |
#   | serie: registrar   | O(capacidad del inventario)    | O(1)                     |
#   | serie: plegar      | O(registros sacados)           | O(1)                     |
#   | serie: en          | O(log longitud)                | O(1)                     |
#   | consultar_accion  | O(log C + S + K·a)             | O(S + N + E) temporal    |
#   | consultar_instante | O(log n + log C + S + K·a)     | O(S + N + E) temporal    |
#   | clon_antes_de      | O(log C + S + K·a)             | O(S + N + E) (lo descarta quien lo pide) |
#   | comprobar_sello    | O(1)                           | O(1)                     |
#   | propiedades        | O(1)                           | O(1)                     |
#   | acciones_rehechas  | O(1)                           | O(1)                     |
#
#   Memoria total: O(n) para el guion y la historia vigente, más O(C·(S + N + E)) para los puntos de control (cada punto pesa O(S) + O(N + E): el estado copiado y las fotos de
#   rastros y de cerradas).
#   Cota de puntos de control: C <= ceil(n / K) + 1 + L + P, con L cargas y P usos del pergamino que no coinciden con un
#   punto existente (el +1 es el estado inicial). Cada carga agrega siempre un punto del motor cargado, aunque ya hubiera uno
#   regular en esa misma acción: `pc_accion` queda con repetidos y la búsqueda devuelve el último.

from DTOS.ResumenHistorico import REFERENCIA_ACCION, REFERENCIA_ACTUAL, REFERENCIA_INSTANTE
from Modelo.AgendaConCorte import AgendaConCorte
from Modelo.BusquedaBinaria import ultimo_menor_o_igual
from Modelo.CopiaEstado import copiar, materializar
from Modelo.ResumenHistorico import resumir
from Persistencia.RegistroLinea import ACCION, CARGA, RETROCESO, RegistroLinea

TIPO_ACCION = "ACCION"
TIPO_RETROCESO = "RETROCESO"
TIPO_CARGA = "CARGA"

K_POR_OMISION = 50
NOMBRE_CARGA = "@cargar"  # el mismo texto con que la bitácora anota una carga


class ReferenciaInvalida(Exception):
    """El instante `t` o la acción `k` pedidos están fuera de rango (por ejemplo `t > reloj_actual`, `k < 1`)."""

    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


class ErrorReconstruccion(Exception):
    """Al rehacer acciones, el sello `(reloj, secuencia)` del clon no coincide con el guardado, o el clon rechazó una
    acción: la re-simulación divergió (motor no determinista o línea corrupta)."""

    def __init__(self, detalle):
        super().__init__(detalle)
        self.detalle = detalle


def _es_entero(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


CLASE_PERGAMINO = "pergamino_retroceso"


def leer_pergaminos(motor):
    """``(cantidad, nombre)`` de los pergaminos de retroceso del inventario del jugador; `nombre` es el ``nombre`` del nodo
    (el mismo texto con que el juego muestra el pergamino en el inventario vivo) o None si no hay. O(capacidad)."""
    cuenta = 0
    nombre = None
    for nodo in motor.jugador.inventario:
        if nodo.clase == CLASE_PERGAMINO:
            cuenta += 1
            nombre = nodo.nombre
    return cuenta, nombre


def contar_pergaminos(motor):
    """Pergaminos de retroceso en el inventario del jugador. O(capacidad del inventario)."""
    return leer_pergaminos(motor)[0]


class SeriePergaminos:
    """Cantidad de pergaminos por instante (FR-029, research R6): pares ``(clave, cantidad)`` ordenados por clave
    estrictamente creciente. ``clave`` = acciones vigentes completadas cuando cambió la cantidad; ``inicial`` es la cantidad
    antes de cualquier cambio. No depende de los puntos de control.

    | Operación | Tiempo               |
    |-----------|----------------------|
    | registrar | O(1)                 |
    | plegar    | O(registros sacados) |
    | en        | O(log longitud)      |
    """

    def __init__(self, inicial=0):
        self.inicial = inicial
        self.nombre = None  # nombre del pergamino tal como lo muestra el inventario vivo (el primero que se vio)
        self.serie_clave = []
        self.serie_cantidad = []

    def ultima(self):
        """Cantidad vigente: la del último registro, o la inicial."""
        return self.serie_cantidad[-1] if self.serie_clave else self.inicial

    def registrar(self, clave, cantidad):
        """Agrega ``(clave, cantidad)`` si la cuenta cambió respecto de la última. Si ya hay un registro con esa clave (dos
        cambios dentro de la misma acción), lo actualiza: la serie sigue estrictamente creciente. O(1)."""
        if cantidad == self.ultima():
            return
        if self.serie_clave and self.serie_clave[-1] == clave:
            self.serie_cantidad[-1] = cantidad
        else:
            self.serie_clave.append(clave)
            self.serie_cantidad.append(cantidad)

    def plegar(self, nuevo_n, cantidad_actual):
        """Tras un retroceso a `nuevo_n`: saca los registros con clave ``> nuevo_n`` y agrega ``(nuevo_n, cantidad_actual)``
        solo si difiere de la última. Rige la última ocurrencia de esa posición (el presente). O(sacadas)."""
        while self.serie_clave and self.serie_clave[-1] > nuevo_n:
            self.serie_clave.pop()
            self.serie_cantidad.pop()
        self.registrar(nuevo_n, cantidad_actual)

    def en(self, clave):
        """Cantidad en la posición `clave`: la de la última clave ``<= clave``, o la inicial. O(log longitud)."""
        indice = ultimo_menor_o_igual(self.serie_clave, clave)
        return self.inicial if indice < 0 else self.serie_cantidad[indice]


class LineaTiempo:
    """Guion append-only, historia vigente y puntos de control de una partida.

    Arreglos paralelos (data-model.md):

    - ``guion_*``: un registro por comando aceptado (tipo, nombre, argumento, reloj y secuencia previos).
    - ``vig_guion``, ``vig_reloj``, ``vig_sec``: la historia vigente; ``vig_guion[j]`` es la posición en el guion de la
      acción ``j + 1`` y ``(vig_reloj[j], vig_sec[j])`` el sello de la decisión **previa** a ella.
    - ``pc_accion``, ``pc_reloj``, ``pc_epoca``, ``pc_punto``: puntos de control, no decrecientes en ``pc_accion``.

    El sello previo de la acción *k* se toma **al terminar el aviso anterior** (``iniciar`` o la acción *k - 1*), de
    ``motor.reloj`` y ``motor.secuencia`` (nunca de ``jugador.evento_actual``, HL7): ``registrar_accion`` llega con el motor
    ya avanzado. La línea no guarda el motor.

    Complejidad (contracts/interfaz-linea.md y data-model.md). `n` acciones vigentes, `K` acciones entre puntos, `C` puntos de
    control, `S` tamaño del estado vivo, `N` y `E` salas y salidas, `a` costo de una acción, `V` acciones recortadas, `L`
    cargas y `P` retrocesos:

    | Operación            | Tiempo                         | Memoria                   |
    |----------------------|--------------------------------|---------------------------|
    | ``iniciar``          | O(S + N + E)                   | O(S) + O(N + E)           |
    | ``registrar_accion`` | O(1), más O(S + N + E) cada K  | O(1), más O(S) + O(N + E) cada K |
    | ``registrar_retroceso`` | O(V + S + N + E)            | O(S) + O(N + E)           |
    | ``registrar_carga``  | O(S + N + E)                   | O(S) + O(N + E), más la copia privada |
    | ``consultar_instante`` | O(log n + log C + S + K·a)   | O(S + N + E) temporal     |
    | ``consultar_accion`` | O(log C + S + K·a)             | O(S + N + E) temporal     |
    | ``a_registro``       | O(n_guion)                     | O(n_guion)                |
    | ``desde_registro``   | O(n_guion)                     | O(n_guion)                |
    | ``cerrar``           | O(L)                           | O(L)                      |
    | propiedades          | O(1)                           | O(1)                      |

    Memoria total: ``M(n) = n·b_guion + (P + L)·b_guion + C·(S + N + E) + serie``, es decir, O(n) para el guion y la historia
    vigente más O(C·(S + N + E)) para los puntos de control (cada punto: O(S) + O(N + E)), con ``C <= ceil(n / K) + 1 + L + P``. No contiene el término «acciones ×
    tamaño del estado»: para K fijo el segundo sumando crece como n / K, y duplicar n duplica M.
    """

    def __init__(self, k=K_POR_OMISION, gestor_historico=None, abrir_copia=None):
        if not _es_entero(k) or k < 1:
            raise ValueError(f"K debe ser un entero mayor o igual que 1, no {k!r}")
        self._k = k
        self.gestor_historico = gestor_historico  # lo usan las consultas (tareas posteriores)
        self.abrir_copia = abrir_copia

        self.guion_tipo = []
        self.guion_nombre = []
        self.guion_argumento = []
        self.guion_reloj = []
        self.guion_secuencia = []

        self.vig_guion = []
        self.vig_reloj = []
        self.vig_sec = []

        self.pc_accion = []
        self.pc_reloj = []
        self.pc_epoca = []
        self.pc_punto = []

        self.epocas_accion = [0]    # acción en que empezó cada época; la 0 es la partida desde su inicio
        self.epocas_ruta = [None]   # copia privada del archivo cargado de cada época (None en la 0 y sin restaurador)

        self.serie = SeriePergaminos(0)
        self._acciones_motor = 0    # motor.acciones_jugador en el último registro (para calcular V)
        self._epoca = 0
        self._sello_reloj = 0       # sello de la decisión actual: el que tendrá la próxima acción registrada
        self._sello_secuencia = 0
        self._reloj_actual = 0
        self._iniciada = False
        self._rehechas = 0          # acciones que rehízo la última consulta (T096)
        self._clon_vivo = None      # el último clon materializado: su restaurador se cierra al soltarlo (Windows)

    # ───────────── propiedades ─────────────

    @property
    def k(self):
        return self._k

    @property
    def acciones(self):
        """Acciones vigentes `n`. O(1)."""
        return len(self.vig_guion)

    @property
    def reloj_actual(self):
        """Reloj del motor en el último registro. O(1)."""
        return self._reloj_actual

    @property
    def cantidad_puntos(self):
        """Puntos de control guardados `C`. O(1)."""
        return len(self.pc_accion)

    @property
    def acciones_rehechas(self):
        """Acciones que rehízo la última consulta (`consultar_accion`, `consultar_instante` o `clon_antes_de`) para llegar
        a la decisión pedida, contando la acción parcial de un instante intermedio. Solo lectura: no cambia ningún
        comportamiento y sirve para probar que ninguna consulta rehace más de K acciones (FR-019). O(1)."""
        return self._rehechas

    # ───────────── registro ─────────────

    def iniciar(self, motor):
        """Motor recién creado: punto de control en la acción 0 y sello inicial `(motor.reloj, motor.secuencia)`.
        Si la línea ya tenía datos, los descarta. O(S + N + E)."""
        self.guion_tipo = []
        self.guion_nombre = []
        self.guion_argumento = []
        self.guion_reloj = []
        self.guion_secuencia = []
        self.vig_guion = []
        self.vig_reloj = []
        self.vig_sec = []
        self.pc_accion = []
        self.pc_reloj = []
        self.pc_epoca = []
        self.pc_punto = []
        self.epocas_accion = [0]
        self.epocas_ruta = [None]
        self._rehechas = 0
        self._epoca = 0
        cuenta, nombre = leer_pergaminos(motor)
        self.serie = SeriePergaminos(cuenta)
        self.serie.nombre = nombre
        self._acciones_motor = motor.acciones_jugador
        self._agregar_punto(motor, 0)
        self._tomar_sello(motor)
        self._iniciada = True

    def registrar_accion(self, motor, nombre, argumento=""):
        """Registra una acción **aceptada** que cuenta; `motor` ya la ejecutó. Una acción rechazada no llega aquí.

        Agrega al guion y a la historia vigente el sello previo guardado, y si ``n % K == 0`` toma un punto de control del
        motor (ya en la decisión ``n + 1``). Guarda el sello del motor ya avanzado para la acción siguiente.
        O(1), más una copia O(S + N + E) cada K acciones."""
        if not self._iniciada:
            raise RuntimeError("La línea de tiempo no se ha iniciado: falta iniciar(motor)")
        if not isinstance(nombre, str) or nombre == "":
            raise ValueError("El nombre de la acción debe ser texto no vacío")
        if nombre == "retroceder":
            raise ValueError("«retroceder» no es una acción que cuenta: use registrar_retroceso(motor)")

        self.vig_guion.append(len(self.guion_tipo))
        self.vig_reloj.append(self._sello_reloj)
        self.vig_sec.append(self._sello_secuencia)

        self.guion_tipo.append(TIPO_ACCION)
        self.guion_nombre.append(nombre)
        self.guion_argumento.append(argumento if isinstance(argumento, str) else str(argumento))
        self.guion_reloj.append(self._sello_reloj)
        self.guion_secuencia.append(self._sello_secuencia)

        acciones = len(self.vig_guion)
        self._registrar_pergaminos(acciones, motor)
        if acciones % self._k == 0:
            self._agregar_punto(motor, acciones)
        self._tomar_sello(motor)
        self._acciones_motor = motor.acciones_jugador

    def registrar_retroceso(self, motor):
        """Registra un ``retroceder`` **aceptado**; `motor` ya lo ejecutó (el pergamino revirtió el último intervalo).

        ``V = acciones_antes - acciones_después`` con ``motor.acciones_jugador``; saca ``V`` posiciones de la historia
        vigente y los puntos con ``accion > nuevo_n``; agrega ``RETROCESO`` al guion con las acciones vigentes que quedan;
        toma un punto de control del **motor real** en ``nuevo_n`` (si ya había uno, lo reemplaza: el estado real conserva
        efectos irreversibles, R5); pliega la serie de pergaminos; y guarda el sello de la decisión actual.
        O(V) más una copia O(S + N + E); no depende de `n` (FR-027)."""
        if not self._iniciada:
            raise RuntimeError("La línea de tiempo no se ha iniciado: falta iniciar(motor)")
        quitadas = self._acciones_motor - motor.acciones_jugador
        if quitadas < 0 or quitadas > len(self.vig_guion):
            raise ErrorReconstruccion(
                f"el retroceso quitó {quitadas} acciones y la línea tiene {len(self.vig_guion)} vigentes")
        for _ in range(quitadas):
            self.vig_guion.pop()
            self.vig_reloj.pop()
            self.vig_sec.pop()
        nuevo_n = len(self.vig_guion)
        while self.pc_accion and self.pc_accion[-1] > nuevo_n:
            self.pc_accion.pop()
            self.pc_reloj.pop()
            self.pc_epoca.pop()
            self.pc_punto.pop()

        self.guion_tipo.append(TIPO_RETROCESO)
        self.guion_nombre.append("retroceder")
        self.guion_argumento.append("")
        self.guion_reloj.append(nuevo_n)   # para RETROCESO: las acciones vigentes que quedan (data-model.md)
        self.guion_secuencia.append(0)

        if self.pc_accion and self.pc_accion[-1] == nuevo_n:
            self.pc_reloj[-1] = motor.reloj
            self.pc_punto[-1] = copiar(motor, accion=nuevo_n, epoca=self.pc_epoca[-1])
        else:
            self._agregar_punto(motor, nuevo_n)
        cuenta, nombre = leer_pergaminos(motor)
        self._recordar_nombre(nombre)
        self.serie.plegar(nuevo_n, cuenta)
        self._tomar_sello(motor)
        self._acciones_motor = motor.acciones_jugador

    def registrar_carga(self, motor, ruta_copia):
        """Registra la frontera de un ``@cargar``: `motor` es el motor **cargado** (el que devolvió ``cargar_partida``) y
        `ruta_copia` la copia privada del archivo que se cargó (None si el motor no tiene restaurador: no hay salas
        pendientes que restaurar).

        Agrega ``CARGA`` al guion con el reloj cargado; no saca nada de la historia vigente (el pasado anterior sigue
        consultable); abre una época nueva que empieza en la acción actual `n` con su copia privada; toma un punto de
        control del motor cargado en `n` (aunque ya haya uno regular en `n`: quedan los dos y la búsqueda devuelve el
        último); y guarda el sello de la decisión del motor cargado, que es la que tendrá la próxima acción.
        O(S + N + E)."""
        if not self._iniciada:
            raise RuntimeError("La línea de tiempo no se ha iniciado: falta iniciar(motor)")
        n = len(self.vig_guion)
        self.guion_tipo.append(TIPO_CARGA)
        self.guion_nombre.append(NOMBRE_CARGA)
        self.guion_argumento.append("")
        self.guion_reloj.append(motor.reloj)   # para CARGA: el reloj cargado (data-model.md)
        self.guion_secuencia.append(0)

        self._epoca += 1
        self.epocas_accion.append(n)
        self.epocas_ruta.append(ruta_copia)
        self._agregar_punto(motor, n)
        self._registrar_pergaminos(n, motor)
        self._tomar_sello(motor)
        self._acciones_motor = motor.acciones_jugador

    def a_registro(self):
        """El guion completo (acciones, retrocesos y cargas, en orden cronológico) y K, listos para ``guardar_partida``.
        Los puntos de control no se guardan: se reconstruyen al cargar. O(n_guion)."""
        registros = []
        for posicion in range(len(self.guion_tipo)):
            tipo = self.guion_tipo[posicion]
            if tipo == TIPO_ACCION:
                registros.append((ACCION, self.guion_nombre[posicion], self.guion_argumento[posicion],
                                  self.guion_reloj[posicion], self.guion_secuencia[posicion]))
            elif tipo == TIPO_RETROCESO:
                registros.append((RETROCESO, self.guion_reloj[posicion]))
            else:
                registros.append((CARGA, self.guion_reloj[posicion]))
        return RegistroLinea(self._k, registros)

    @classmethod
    def desde_registro(cls, registro, gestor_historico=None, abrir_copia=None):
        """Línea con **solo los datos** del `registro` (``RegistroLinea``): K, el guion y la historia vigente, que se
        deduce del guion. No tiene puntos de control, épocas ni serie de pergaminos y no está iniciada: reconstruir el
        estado es trabajo del controlador (``ReconstructorLinea``), que reproduce el guion. ``ValueError`` si un retroceso
        deja más acciones vigentes de las que había. O(n_guion)."""
        linea = cls(registro.k, gestor_historico, abrir_copia)
        for entrada in registro.registros:
            tipo = entrada[0]
            if tipo == ACCION:
                linea.vig_guion.append(len(linea.guion_tipo))
                linea.vig_reloj.append(entrada[3])
                linea.vig_sec.append(entrada[4])
                linea.guion_tipo.append(TIPO_ACCION)
                linea.guion_nombre.append(entrada[1])
                linea.guion_argumento.append(entrada[2])
                linea.guion_reloj.append(entrada[3])
                linea.guion_secuencia.append(entrada[4])
            elif tipo == RETROCESO:
                quedan = entrada[1]
                if quedan > len(linea.vig_guion):
                    raise ValueError(f"un retroceso deja {quedan} acciones vigentes y solo había {len(linea.vig_guion)}")
                while len(linea.vig_guion) > quedan:
                    linea.vig_guion.pop()
                    linea.vig_reloj.pop()
                    linea.vig_sec.pop()
                linea.guion_tipo.append(TIPO_RETROCESO)
                linea.guion_nombre.append("retroceder")
                linea.guion_argumento.append("")
                linea.guion_reloj.append(quedan)
                linea.guion_secuencia.append(0)
            else:
                linea.guion_tipo.append(TIPO_CARGA)
                linea.guion_nombre.append(NOMBRE_CARGA)
                linea.guion_argumento.append("")
                linea.guion_reloj.append(entrada[1])
                linea.guion_secuencia.append(0)
        return linea

    def cerrar(self):
        """Termina de usar la línea: suelta el clon que pudiera tener el gestor histórico, deja de aceptar registros y
        **devuelve** las rutas de las copias privadas de sus épocas para que el controlador las borre (la línea no toca
        archivos: Principio II). Idempotente: la segunda vez devuelve una lista vacía. O(L)."""
        rutas = []
        for posicion in range(len(self.epocas_ruta)):
            if self.epocas_ruta[posicion] is not None:
                rutas.append(self.epocas_ruta[posicion])
                self.epocas_ruta[posicion] = None
        self._soltar_clon()
        self._iniciada = False
        return rutas

    def _recordar_nombre(self, nombre):
        if nombre is not None and self.serie.nombre is None:
            self.serie.nombre = nombre

    def _registrar_pergaminos(self, clave, motor):
        cuenta, nombre = leer_pergaminos(motor)
        self._recordar_nombre(nombre)
        self.serie.registrar(clave, cuenta)

    @property
    def serie_clave(self):
        return self.serie.serie_clave

    @property
    def serie_cantidad(self):
        return self.serie.serie_cantidad

    def _tomar_sello(self, motor):
        self._sello_reloj = motor.reloj
        self._sello_secuencia = motor.secuencia
        self._reloj_actual = motor.reloj

    def _agregar_punto(self, motor, accion):
        self.pc_accion.append(accion)
        self.pc_reloj.append(motor.reloj)
        self.pc_epoca.append(self._epoca)
        self.pc_punto.append(copiar(motor, accion=accion, epoca=self._epoca))

    # ───────────── sellos ─────────────

    def sincronizada(self, motor):
        """True si `motor` está en la decisión que la línea espera (su ``(reloj, secuencia)`` es el sello guardado). Si el
        motor avanzó sin que la línea se enterara (por ejemplo, una acción que lanzó ``RuntimeError`` a medias), es False.
        O(1)."""
        return (motor.reloj, motor.secuencia) == (self._sello_reloj, self._sello_secuencia)

    def sello_de(self, k):
        """Sello `(reloj, secuencia)` de la decisión previa a la acción `k`, con `1 <= k <= acciones + 1`
        (``k == acciones + 1`` es la decisión actual). O(1)."""
        if not _es_entero(k) or k < 1 or k > self.acciones + 1:
            raise ReferenciaInvalida(f"La acción {k!r} no existe: hay {self.acciones} acciones y la decisión actual")
        if k == self.acciones + 1:
            return (self._sello_reloj, self._sello_secuencia)
        return (self.vig_reloj[k - 1], self.vig_sec[k - 1])

    def comprobar_sello(self, motor, k):
        """Verifica que `motor` (un clon rehaciendo) está en la decisión `k`: su `(reloj, secuencia)` debe ser el guardado.
        Lanza ``ErrorReconstruccion`` si difiere. O(1)."""
        esperado = self.sello_de(k)
        real = (motor.reloj, motor.secuencia)
        if real != esperado:
            raise ErrorReconstruccion(
                f"el sello de la decisión {k} es (reloj {esperado[0]}, secuencia {esperado[1]}) y el clon quedó en "
                f"(reloj {real[0]}, secuencia {real[1]})")

    # ───────────── consultas (solo lectura) ─────────────

    def _ruta_de_epoca(self, epoca):
        """Ruta de la copia privada del archivo de la época (None si no tiene: la época 0 o una carga sin restaurador)."""
        if 0 <= epoca < len(self.epocas_ruta):
            return self.epocas_ruta[epoca]
        return None

    def _rehacer_hasta(self, k):
        """Clon materializado desde el último punto con `accion <= k - 1`, con las acciones vigentes rehechas hasta quedar
        en la decisión `k` (`1 <= k <= acciones + 1`). Compara el sello de cada decisión y lanza ``ErrorReconstruccion``
        si difiere o si el clon rechaza una acción. Rehace a lo sumo K acciones. No toca el motor vivo."""
        indice = ultimo_menor_o_igual(self.pc_accion, k - 1)
        if indice < 0:
            raise ErrorReconstruccion(f"no hay un punto de control anterior a la decisión {k}")
        punto = self.pc_punto[indice]
        self._tomar_falta()  # olvida una falta vieja
        self._cerrar_clon()  # un solo clon vivo a la vez: el anterior suelta su archivo
        clon = materializar(punto, self.gestor_historico, self.abrir_copia, self._ruta_de_epoca(punto.epoca))
        self._clon_vivo = clon
        self.comprobar_sello(clon, punto.accion + 1)
        for j in range(punto.accion + 1, k):
            posicion = self.vig_guion[j - 1]
            nombre = self.guion_nombre[posicion]
            if nombre == "retroceder":
                raise ErrorReconstruccion(f"la acción {j} es «retroceder»: la reconstrucción nunca lo ejecuta")
            aceptada = clon.ejecutar_accion(nombre, self.guion_argumento[posicion])
            self._rehechas += 1
            self._lanzar_si_falta_un_dato()
            if not aceptada:
                raise ErrorReconstruccion(f"el clon rechazó la acción {j} ({nombre} {self.guion_argumento[posicion]})")
            self.comprobar_sello(clon, j + 1)
        return clon

    def _tomar_falta(self):
        tomar = getattr(self.gestor_historico, "tomar_falta", None)
        return None if tomar is None else tomar()

    def _lanzar_si_falta_un_dato(self):
        """Si el gestor histórico no tuvo un dato local (el motor atrapa ese error y rechaza el paso), la causa de un
        rechazo es esa y se re-lanza tal cual (``SinDatosParaHistoria``), no como una divergencia."""
        falta = self._tomar_falta()
        if falta is not None:
            raise falta

    def _validar_accion(self, k):
        if not _es_entero(k) or k < 1:
            raise ReferenciaInvalida("Las acciones se numeran desde 1.")
        if k > self.acciones + 1:
            raise ReferenciaInvalida(f"La acción {k} no existe: la próxima acción es la {self.acciones + 1}.")

    def _cerrar_clon(self):
        """Cierra el restaurador del último clon (abierto sobre la copia privada de una época) para que el controlador pueda
        borrar la copia, también en Windows. O(1)."""
        clon = self._clon_vivo
        self._clon_vivo = None
        if clon is not None and clon.restaurador is not None:
            clon.restaurador.cerrar()
            clon.restaurador = None

    def _soltar_clon(self):
        self._cerrar_clon()
        if self.gestor_historico is not None:
            self.gestor_historico.conectar_estado_juego(None)  # un solo clon vivo por gestor: se descarta

    def clon_antes_de(self, k, motor):
        """Clon desechable del estado justo antes de la acción `k` (`1 <= k <= acciones + 1`), para las pruebas de A.
        La consulta de producción no lo expone. Quien lo pide lo descarta antes de materializar otro. `motor` es el vivo
        y no se toca (se acepta por uniformidad con las consultas). O(log C + S + K·a)."""
        self._rehechas = 0
        self._validar_accion(k)
        return self._rehacer_hasta(k)

    def consultar_accion(self, k, motor):
        """``ResumenHistorico`` del estado justo antes de la acción `k`, con el reloj de esa decisión.
        ``k == acciones + 1`` es el estado actual: se resume el motor vivo, sin ejecutar nada en él.
        ``ReferenciaInvalida`` si `k` está fuera de rango; ``ErrorReconstruccion`` si la re-simulación diverge.
        O(log C + S + K·a). Solo lectura."""
        self._rehechas = 0
        self._validar_accion(k)
        if k == self.acciones + 1:
            return resumir(motor, motor.reloj, (REFERENCIA_ACTUAL, None))
        try:
            clon = self._rehacer_hasta(k)
            return resumir(clon, self.vig_reloj[k - 1], (REFERENCIA_ACCION, k), self.serie.en(k - 1), self.serie.nombre)
        finally:
            self._soltar_clon()

    def consultar_instante(self, t, motor):
        """``ResumenHistorico`` del estado en el instante `t` (``0 <= t <= reloj_actual``), con el reloj `t`.

        ``t == reloj_actual``: el estado actual (motor vivo). Si no, `k` = última acción vigente con
        ``vig_reloj[k - 1] <= t`` (búsqueda binaria); si ``vig_reloj[k - 1] == t`` es el estado justo antes de esa
        decisión; si no, el clon de la decisión `k` ejecuta la acción `k` con una ``AgendaConCorte(corte = t)`` y se
        detiene en `t`. ``ReferenciaInvalida`` si `t` es negativo o mayor que el reloj actual.
        O(log n + log C + S + K·a). Solo lectura."""
        self._rehechas = 0
        if not _es_entero(t) or t < 0:
            raise ReferenciaInvalida("El instante debe ser un entero mayor o igual que 0.")
        if t > self._reloj_actual:
            raise ReferenciaInvalida(f"No hay historia más allá del reloj actual ({self._reloj_actual}).")
        if t == self._reloj_actual:
            return resumir(motor, motor.reloj, (REFERENCIA_ACTUAL, None))

        indice = ultimo_menor_o_igual(self.vig_reloj, t)
        k = 1 if indice < 0 else indice + 1
        try:
            clon = self._rehacer_hasta(k)
            if indice < 0 or self.vig_reloj[indice] == t:
                return resumir(clon, t, (REFERENCIA_INSTANTE, t), self.serie.en(k - 1), self.serie.nombre)
            clon.agenda.__class__ = AgendaConCorte
            clon.agenda.corte = t
            posicion = self.vig_guion[k - 1]
            aceptada = clon.ejecutar_accion(self.guion_nombre[posicion], self.guion_argumento[posicion])
            self._rehechas += 1
            self._lanzar_si_falta_un_dato()
            if not aceptada:
                raise ErrorReconstruccion(f"el clon rechazó la acción {k} ({self.guion_nombre[posicion]})")
            return resumir(clon, t, (REFERENCIA_INSTANTE, t), self.serie.en(k), self.serie.nombre)
        finally:
            self._soltar_clon()
