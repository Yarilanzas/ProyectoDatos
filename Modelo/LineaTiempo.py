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
#   | consultar_accion   | O(log C + S + K·a)             | O(S) temporal            |
#   | consultar_instante | O(log n + log C + S + K·a)     | O(S) temporal            |
#   | clon_antes_de      | O(log C + S + K·a)             | O(S) (lo descarta quien lo pide) |
#   | comprobar_sello    | O(1)                           | O(1)                     |
#   | propiedades        | O(1)                           | O(1)                     |
#
#   Memoria total: O(n) para el guion y la historia vigente, más O(C·S) para los puntos de control.
#   Cota de puntos de control: C <= ceil(n / K) + 1 + L + P, con L cargas y P usos del pergamino que no coinciden con un
#   punto existente (el +1 es el estado inicial). L y P no existen todavía en este núcleo.

from DTOS.ResumenHistorico import REFERENCIA_ACCION, REFERENCIA_ACTUAL, REFERENCIA_INSTANTE
from Modelo.AgendaConCorte import AgendaConCorte
from Modelo.BusquedaBinaria import ultimo_menor_o_igual
from Modelo.CopiaEstado import copiar, materializar
from Modelo.ResumenHistorico import resumir

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

    # ───────────── consultas (solo lectura) ─────────────

    def _ruta_de_epoca(self, epoca):
        """Ruta de la copia privada del archivo de la época (None si no tiene). Las épocas llegan con `registrar_carga`."""
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
        clon = materializar(punto, self.gestor_historico, self.abrir_copia, self._ruta_de_epoca(punto.epoca))
        self.comprobar_sello(clon, punto.accion + 1)
        for j in range(punto.accion + 1, k):
            posicion = self.vig_guion[j - 1]
            nombre = self.guion_nombre[posicion]
            if nombre == "retroceder":
                raise ErrorReconstruccion(f"la acción {j} es «retroceder»: la reconstrucción nunca lo ejecuta")
            aceptada = clon.ejecutar_accion(nombre, self.guion_argumento[posicion])
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

    def _soltar_clon(self):
        if self.gestor_historico is not None:
            self.gestor_historico.conectar_estado_juego(None)  # un solo clon vivo por gestor: se descarta

    def clon_antes_de(self, k, motor):
        """Clon desechable del estado justo antes de la acción `k` (`1 <= k <= acciones + 1`), para las pruebas de A.
        La consulta de producción no lo expone. Quien lo pide lo descarta antes de materializar otro. `motor` es el vivo
        y no se toca (se acepta por uniformidad con las consultas). O(log C + S + K·a)."""
        self._validar_accion(k)
        return self._rehacer_hasta(k)

    def consultar_accion(self, k, motor):
        """``ResumenHistorico`` del estado justo antes de la acción `k`, con el reloj de esa decisión.
        ``k == acciones + 1`` es el estado actual: se resume el motor vivo, sin ejecutar nada en él.
        ``ReferenciaInvalida`` si `k` está fuera de rango; ``ErrorReconstruccion`` si la re-simulación diverge.
        O(log C + S + K·a). Solo lectura."""
        self._validar_accion(k)
        if k == self.acciones + 1:
            return resumir(motor, motor.reloj, (REFERENCIA_ACTUAL, None))
        try:
            clon = self._rehacer_hasta(k)
            return resumir(clon, self.vig_reloj[k - 1], (REFERENCIA_ACCION, k))
        finally:
            self._soltar_clon()

    def consultar_instante(self, t, motor):
        """``ResumenHistorico`` del estado en el instante `t` (``0 <= t <= reloj_actual``), con el reloj `t`.

        ``t == reloj_actual``: el estado actual (motor vivo). Si no, `k` = última acción vigente con
        ``vig_reloj[k - 1] <= t`` (búsqueda binaria); si ``vig_reloj[k - 1] == t`` es el estado justo antes de esa
        decisión; si no, el clon de la decisión `k` ejecuta la acción `k` con una ``AgendaConCorte(corte = t)`` y se
        detiene en `t`. ``ReferenciaInvalida`` si `t` es negativo o mayor que el reloj actual.
        O(log n + log C + S + K·a). Solo lectura."""
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
                return resumir(clon, t, (REFERENCIA_INSTANTE, t))
            clon.agenda.__class__ = AgendaConCorte
            clon.agenda.corte = t
            posicion = self.vig_guion[k - 1]
            aceptada = clon.ejecutar_accion(self.guion_nombre[posicion], self.guion_argumento[posicion])
            self._lanzar_si_falta_un_dato()
            if not aceptada:
                raise ErrorReconstruccion(f"el clon rechazó la acción {k} ({self.guion_nombre[posicion]})")
            return resumir(clon, t, (REFERENCIA_INSTANTE, t))
        finally:
            self._soltar_clon()
