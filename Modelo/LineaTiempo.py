# Núcleo de la línea de tiempo (spec 004, T017; data-model.md#lineatiempo; FR-016, FR-017, FR-018, FR-021, PR-03).
#
# Solo el núcleo: guion, historia vigente, puntos de control y sellos. Las consultas, el retroceso, la carga, la serie de
# pergaminos y la persistencia llegan en tareas posteriores. Principio I: todo son listas paralelas; sin dict ni set como
# índice, sin bisect, sorted, sort, heapq ni collections. Principio II: no importa red, archivos ni consola; lo externo
# (gestor histórico, apertura de copias privadas) se inyecta.
#
# Complejidad (n acciones vigentes, K acciones entre puntos, S tamaño del estado vivo, N/E salas y salidas,
# C puntos de control):
#
#   | Operación          | Tiempo                         | Memoria                  |
#   |--------------------|--------------------------------|--------------------------|
#   | iniciar            | O(S + N + E)                   | O(S)                     |
#   | registrar_accion   | O(1), más O(S + N + E) cada K  | O(1), más O(S) cada K    |
#   | sello_de           | O(1)                           | O(1)                     |
#   | comprobar_sello    | O(1)                           | O(1)                     |
#   | propiedades        | O(1)                           | O(1)                     |
#
#   Memoria total: O(n) para el guion y la historia vigente, más O(C·S) para los puntos de control.
#   Cota de puntos de control: C <= ceil(n / K) + 1 + L + P, con L cargas y P usos del pergamino que no coinciden con un
#   punto existente (el +1 es el estado inicial). L y P no existen todavía en este núcleo.

from Modelo.CopiaEstado import copiar

TIPO_ACCION = "ACCION"
TIPO_RETROCESO = "RETROCESO"
TIPO_CARGA = "CARGA"

K_POR_OMISION = 50


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

        self._epoca = 0
        self._sello_reloj = 0       # sello de la decisión actual: el que tendrá la próxima acción registrada
        self._sello_secuencia = 0
        self._reloj_actual = 0
        self._iniciada = False

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
        self._epoca = 0
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

        self.vig_guion.append(len(self.guion_tipo))
        self.vig_reloj.append(self._sello_reloj)
        self.vig_sec.append(self._sello_secuencia)

        self.guion_tipo.append(TIPO_ACCION)
        self.guion_nombre.append(nombre)
        self.guion_argumento.append(argumento if isinstance(argumento, str) else str(argumento))
        self.guion_reloj.append(self._sello_reloj)
        self.guion_secuencia.append(self._sello_secuencia)

        acciones = len(self.vig_guion)
        if acciones % self._k == 0:
            self._agregar_punto(motor, acciones)
        self._tomar_sello(motor)

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
