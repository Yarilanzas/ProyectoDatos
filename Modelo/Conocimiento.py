# Lo que el jugador sabe de la cripta (niebla de guerra). FR-001 a FR-011, FR-014, PR-01, PR-02, PR-03, PR-05.
# Es parte del estado de la partida, separado del mapa real para proteger FR-012.
# No conoce la vista, ni el motor, ni archivos (Principio II).

# Estado de una sala.
DESCONOCIDA = 0
AVISTADA = 1
EXPLORADA = 2

# Recuerdo de una puerta, por salida dirigida (H3: A->B y B->A tienen estados distintos).
SIN_OBSERVAR = 0
ABIERTA = 1
CERRADA = 2
TEXTO_RECUERDO = ("sin observar", "abierta", "cerrada")  # por valor del recuerdo

# Primer campo de cada entrada de un lote: (tipo, ordinal, valor_anterior).
_CAMBIO_SALA = 0
_CAMBIO_PUERTA = 1


class Conocimiento:
    """Estado de cada sala y recuerdo de cada puerta, en arreglos densos por ordinal.

    Notación: n salas, e salidas, d(s) salidas que salen de s o entran a s.

    Los ordinales son propios y se asignan una sola vez, porque los ids son opacos: pueden no
    ser densos ni numéricos (H7). Cada sala guarda `_ordinal`, y cada salida `_ordinal` y `_origen`,
    igual que el `_destino` del motor. Con la referencia al objeto, consultar es un acceso directo.
    No se usa `dict` ni `set` como índice: `sala.salidas` es el dict del DTO y solo se recorre.

    | Operación                      | Complejidad                                                  |
    |--------------------------------|--------------------------------------------------------------|
    | Conocimiento(salas, destino_de)| O(n + e) más resolver destinos, O(e log n) la primera vez    |
    | estado(sala)                   | O(1)                                                         |
    | recuerdo(salida)               | O(1)                                                         |
    | entrar(sala, False, historial) | O(d(s))                                                      |
    | entrar(sala, True, historial)  | O(d(s) + Σ salidas de cada vecina v nueva). No depende de k  |
    | observar_puerta(salida, hist.) | O(1)                                                         |
    | conecta(salida, sala)          | O(1)                                                         |
    | destino(salida)                | O(1) tras resolverla una vez                                 |
    | explorada_por_texto(texto)     | O(k), k salas reveladas                                      |
    | _explorar(sala, lote) (interna)| O(salidas de la sala)                                        |
    | revertir(lote)                 | O(tamaño del lote)                                           |

    Memoria: O(n + e), más los lotes de los últimos 5 intervalos del Historial.

    Reglas que se mantienen:
    - Una sala es AVISTADA si y solo si no está explorada y es destino de una salida de una sala
      explorada (FR-004). Se guarda en vez de calcularse: explorar solo agrega, y revertir deshace
      cada escritura, así que no hacen falta contadores.
    - Una sala está en `reveladas` si y solo si su estado no es DESCONOCIDA, y aparece una sola vez.
      Igual `observadas` con SIN_OBSERVAR.
    - El recuerdo se guarda aunque la sala de origen no esté explorada (FR-011).
    """

    def __init__(self, salas, destino_de):
        # `destino_de(salida)` devuelve la sala destino, o None si no existe.
        self._destino_de = destino_de
        self.estado_sala = [DESCONOCIDA] * len(salas)
        self.recuerdo_puerta = []
        self.reveladas = []
        self.observadas = []
        self.entrantes = [[] for _ in salas]  # infraestructura: nunca se muestra (FR-013)

        for ordinal, sala in enumerate(salas):
            sala._ordinal = ordinal

        for sala in salas:
            for salida in sala.salidas.values():
                salida._ordinal = len(self.recuerdo_puerta)
                salida._origen = sala
                self.recuerdo_puerta.append(SIN_OBSERVAR)

                destino = destino_de(salida)
                if destino is not None:
                    self.entrantes[destino._ordinal].append(salida)

    def estado(self, sala):
        return self.estado_sala[sala._ordinal]

    def recuerdo(self, salida):
        return self.recuerdo_puerta[salida._ordinal]

    def texto_recuerdo(self, salida):
        return TEXTO_RECUERDO[self.recuerdo(salida)]

    def destino(self, salida):
        # Sala a la que lleva la salida, o None. O(1) tras la primera resolución (la del motor).
        return self._destino_de(salida)

    def explorada_por_texto(self, texto):
        # Sala explorada cuyo id, como texto, es `texto`; None si no hay. Recorre solo las reveladas: O(k).
        # Inexistente, desconocida y avistada dan lo mismo por construcción (FR-022).
        for sala in self.reveladas:
            if self.estado_sala[sala._ordinal] == EXPLORADA and str(sala.id) == texto:
                return sala
        return None

    def conecta(self, salida, sala):
        # Una puerta se observa desde cualquiera de las dos salas que conecta (FR-006, lectura P-05).
        return salida._origen is sala or self._destino_de(salida) is sala

    def entrar(self, sala, antorcha, historial):
        # Explora la sala y observa sus salidas y las que entran a ella (FR-003, FR-006).
        # Con antorcha explora además las vecinas por cualquier salida, abierta o cerrada (FR-009).
        # Solo escribe en el conocimiento: no lee contenido ni llama al gestor (FR-010), y sus
        # puertas siguen sin observar (FR-011). Todo cae en un solo lote: un solo Cambio (FR-014).
        lote = []
        self._explorar(sala, lote)

        for salida in sala.salidas.values():
            self._observar(salida, lote)

        for salida in self.entrantes[sala._ordinal]:
            self._observar(salida, lote)

        if antorcha:
            for salida in sala.salidas.values():
                vecina = self._destino_de(salida)
                if vecina is not None:
                    self._explorar(vecina, lote)

        self._registrar(lote, historial)

    def observar_puerta(self, salida, historial):
        # Copia el estado real al recuerdo. Es el único lugar, junto con `entrar`, que lee el estado
        # real de una puerta, y solo se llama cuando el jugador la ve (FR-006, FR-008).
        lote = []
        self._observar(salida, lote)
        self._registrar(lote, historial)

    def _explorar(self, sala, lote):
        if self.estado_sala[sala._ordinal] == EXPLORADA:
            return

        self._cambiar_sala(sala, EXPLORADA, lote)

        for salida in sala.salidas.values():
            destino = self._destino_de(salida)
            if destino is not None and self.estado_sala[destino._ordinal] == DESCONOCIDA:
                self._cambiar_sala(destino, AVISTADA, lote)

    def _observar(self, salida, lote):
        valor = CERRADA if salida.cerrada else ABIERTA
        anterior = self.recuerdo_puerta[salida._ordinal]

        if anterior == valor:
            return

        if anterior == SIN_OBSERVAR:
            self.observadas.append(salida)

        self.recuerdo_puerta[salida._ordinal] = valor
        lote.append((_CAMBIO_PUERTA, salida._ordinal, anterior))

    def _cambiar_sala(self, sala, valor, lote):
        anterior = self.estado_sala[sala._ordinal]

        if anterior == DESCONOCIDA:
            self.reveladas.append(sala)

        self.estado_sala[sala._ordinal] = valor
        lote.append((_CAMBIO_SALA, sala._ordinal, anterior))

    def _registrar(self, lote, historial):
        # Sin cambios no hay Cambio. Antes de la primera acción `registrar` no hace nada: por eso la
        # sala inicial no se puede revertir (FR-002).
        if lote:
            historial.registrar(deshacer=lambda: self.revertir(lote),
                                description="conocimiento del jugador")

    def revertir(self, lote):
        # Recorre el lote al revés. Los lotes se deshacen en orden inverso (LIFO), así que lo último
        # agregado a `reveladas` y `observadas` es lo primero en salir: basta `pop` (FR-014).
        for indice in range(len(lote) - 1, -1, -1):
            tipo, ordinal, anterior = lote[indice]

            if tipo == _CAMBIO_SALA:
                self.estado_sala[ordinal] = anterior
                if anterior == DESCONOCIDA:
                    self.reveladas.pop()
            else:
                self.recuerdo_puerta[ordinal] = anterior
                if anterior == SIN_OBSERVAR:
                    self.observadas.pop()


class GrafoConocido:
    """Grafo de lo que el jugador sabe, con la interfaz de contracts/interfaz-ruta.md. PR-10.

    Adaptador de solo lectura sobre `Conocimiento`: no guarda estado propio ni conoce el motor.
    Una arista existe si y solo si la sala de origen y la de destino están exploradas y el recuerdo de la
    salida es ABIERTA (FR-011, FR-023, FR-029): una puerta cerrada o sin observar no existe para la
    búsqueda, y nunca se abre. El costo lo resuelve `costo_de`, que en el juego es `motor.costo_salida`
    (FR-005); `Conocimiento` no guarda ningún costo.

    | Operación         | Complejidad              |
    |-------------------|--------------------------|
    | ordinal(sala)     | O(1)                     |
    | cantidad_salas    | O(1)                     |
    | aristas(sala)     | O(salidas de la sala)    |

    `aristas` entrega en el orden de `sala.salidas` (determinista, no ordenado por id): el desempate es
    de la búsqueda.
    """

    def __init__(self, conocimiento, costo_de):
        self._conocimiento = conocimiento
        self._costo_de = costo_de

    @property
    def cantidad_salas(self):
        return len(self._conocimiento.estado_sala)

    def ordinal(self, sala):
        return sala._ordinal

    def aristas(self, sala):
        conocimiento = self._conocimiento
        resultado = []

        if conocimiento.estado_sala[sala._ordinal] != EXPLORADA:
            return resultado

        for direccion, salida in sala.salidas.items():
            if conocimiento.recuerdo_puerta[salida._ordinal] != ABIERTA:
                continue
            vecina = conocimiento.destino(salida)
            if vecina is None or conocimiento.estado_sala[vecina._ordinal] != EXPLORADA:
                continue
            resultado.append((direccion, vecina, self._costo_de(salida)))

        return resultado
