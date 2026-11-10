# Lo que el jugador sabe de la cripta (niebla de guerra). FR-001 a FR-011, FR-014, FR-015, PR-01, PR-02, PR-03,
# PR-05, PR-06. Es parte del estado de la partida, separado del mapa real para proteger FR-012.
# No conoce la vista, ni el motor, ni archivos (Principio II).

from Modelo.ordenamiento import elegir_algoritmo

# Estado de una sala.
DESCONOCIDA = 0
AVISTADA = 1
EXPLORADA = 2

# Recuerdo de una puerta, por salida dirigida (H3: A->B y B->A tienen estados distintos).
SIN_OBSERVAR = 0
ABIERTA = 1
CERRADA = 2
TEXTO_RECUERDO = ("sin observar", "abierta", "cerrada")  # por valor del recuerdo

# Cada entrada de un lote es (tipo, ordinal, valor_anterior, valor_nuevo); este es el primer campo (T119).
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
    | aplicar(lote) / invertir(lote) | O(tamaño del lote)                                           |
    | revertir(lote)                 | O(tamaño del lote): es invertir, lo que llama el Historial   |
    | exportar()                     | O(k log k + p log p), con elegir_algoritmo (k <= 32: O(k²))  |
    | restaurar(exploradas, recuerd.)| O(n + e + Σ salidas de las exploradas + (k + p) log n), más  |
    |                                | O(n log n) una sola vez para el índice por id                |
    | copiar()                       | O(n + e)                                                     |

    k salas reveladas, p puertas observadas. Memoria: O(n + e), más los lotes de los últimos 5
    intervalos del Historial.

    Lotes (PR-05, T119): cada cambio guarda el valor anterior y el nuevo, así que un lote se puede
    invertir y volver a aplicar. Una secuencia es válida si se invierte siempre el último lote
    aplicado y se aplica el siguiente al último: `reveladas` y `observadas` se deshacen con `pop`.
    Una secuencia inválida lanza ValueError y deja todo como estaba.

    Serialización (FR-015, T074, T119): `exportar` da las exploradas y los recuerdos en orden canónico
    (por id, y por (sala, dirección)), y `restaurar` reconstruye todo a partir de eso, recalculando las
    avistadas (FR-004). Es lo que guarda `RegistroConocimiento`. El orden de revelación de `reveladas` y
    `observadas` no es parte del estado guardado: tras restaurar queda en orden canónico.

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
        # Por ordinal, para que aplicar un lote y restaurar encuentren el objeto. Solo lectura tras crearse:
        # una copia los comparte.
        self._salas = list(salas)
        self._salidas = []
        self._por_id = None  # salas ordenadas por id; se arma la primera vez que restaurar lo necesita

        for ordinal, sala in enumerate(salas):
            sala._ordinal = ordinal

        for sala in salas:
            for direccion, salida in sala.salidas.items():
                salida._ordinal = len(self.recuerdo_puerta)
                salida._origen = sala
                salida._direccion = direccion
                self.recuerdo_puerta.append(SIN_OBSERVAR)
                self._salidas.append(salida)

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
        return lote

    def observar_puerta(self, salida, historial):
        # Copia el estado real al recuerdo. Es el único lugar, junto con `entrar`, que lee el estado
        # real de una puerta, y solo se llama cuando el jugador la ve (FR-006, FR-008).
        lote = []
        self._observar(salida, lote)
        self._registrar(lote, historial)
        return lote

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
        lote.append((_CAMBIO_PUERTA, salida._ordinal, anterior, valor))

    def _cambiar_sala(self, sala, valor, lote):
        anterior = self.estado_sala[sala._ordinal]

        if anterior == DESCONOCIDA:
            self.reveladas.append(sala)

        self.estado_sala[sala._ordinal] = valor
        lote.append((_CAMBIO_SALA, sala._ordinal, anterior, valor))

    def _registrar(self, lote, historial):
        # Sin cambios no hay Cambio. Antes de la primera acción `registrar` no hace nada: por eso la
        # sala inicial no se puede revertir (FR-002).
        if lote:
            historial.registrar(deshacer=lambda: self.revertir(lote),
                                description="conocimiento del jugador")

    # Lotes reversibles (PR-05, T119).

    def revertir(self, lote):
        # Lo que registra `_registrar` en el Historial. El Historial deshace en orden inverso (LIFO), que es
        # una secuencia válida de `invertir` (FR-014). Modelo/retroceso.py no cambia.
        self.invertir(lote)

    def invertir(self, lote):
        # Deshace el lote recorriéndolo al revés. Si no es el último aplicado, ValueError y nada cambia.
        for indice in range(len(lote) - 1, -1, -1):
            if not self._deshacer_cambio(lote[indice]):
                for hecho in range(indice + 1, len(lote)):
                    self._hacer_cambio(lote[hecho])
                raise ValueError("El lote no es el último aplicado: no se puede invertir")

    def aplicar(self, lote):
        # Vuelve a hacer el lote en su orden. Si el estado no es el de antes del lote, ValueError y nada cambia.
        for indice in range(len(lote)):
            if not self._hacer_cambio(lote[indice]):
                for hecho in range(indice - 1, -1, -1):
                    self._deshacer_cambio(lote[hecho])
                raise ValueError("El estado no es el anterior al lote: no se puede aplicar")

    def _hacer_cambio(self, cambio):
        tipo, ordinal, anterior, nuevo = cambio
        if tipo == _CAMBIO_SALA:
            if self.estado_sala[ordinal] != anterior:
                return False
            self.estado_sala[ordinal] = nuevo
            if anterior == DESCONOCIDA:
                self.reveladas.append(self._salas[ordinal])
        else:
            if self.recuerdo_puerta[ordinal] != anterior:
                return False
            self.recuerdo_puerta[ordinal] = nuevo
            if anterior == SIN_OBSERVAR:
                self.observadas.append(self._salidas[ordinal])
        return True

    def _deshacer_cambio(self, cambio):
        tipo, ordinal, anterior, nuevo = cambio
        if tipo == _CAMBIO_SALA:
            if self.estado_sala[ordinal] != nuevo:
                return False
            if anterior == DESCONOCIDA:
                if not self.reveladas or self.reveladas[-1] is not self._salas[ordinal]:
                    return False
                self.reveladas.pop()
            self.estado_sala[ordinal] = anterior
        else:
            if self.recuerdo_puerta[ordinal] != nuevo:
                return False
            if anterior == SIN_OBSERVAR:
                if not self.observadas or self.observadas[-1] is not self._salidas[ordinal]:
                    return False
                self.observadas.pop()
            self.recuerdo_puerta[ordinal] = anterior
        return True

    # Copia y serialización (FR-015, T074, T119).

    def copiar(self):
        """Copia independiente: cambiar una no cambia la otra. Comparte solo lo que no cambia tras crearse
        (salas, salidas, entrantes, índice por id), así que no reasigna ordinales. O(n + e)."""
        copia = Conocimiento.__new__(Conocimiento)
        copia._destino_de = self._destino_de
        copia.estado_sala = list(self.estado_sala)
        copia.recuerdo_puerta = list(self.recuerdo_puerta)
        copia.reveladas = list(self.reveladas)
        copia.observadas = list(self.observadas)
        copia.entrantes = self.entrantes
        copia._salas = self._salas
        copia._salidas = self._salidas
        copia._por_id = self._por_id
        return copia

    def exportar(self):
        """Exploradas y recuerdos en orden canónico, para el bloque de conocimiento (FR-015).

        Devuelve (exploradas, recuerdos): ids de las salas exploradas, ascendentes (incluye las exploradas
        con antorcha), y (id de la sala de origen, dirección, ABIERTA o CERRADA) de cada puerta observada,
        por (sala, dirección), aunque su sala de origen no esté explorada. Las avistadas no se exportan:
        se recalculan (FR-004). El mismo estado da siempre lo mismo.

        Recorre solo lo revelado. O(k log k + p log p) con `elegir_algoritmo` (no `sorted`).
        """
        exploradas = [sala for sala in self.reveladas if self.estado_sala[sala._ordinal] == EXPLORADA]
        exploradas = _ordenado(exploradas, lambda sala: sala.id)

        recuerdos = [(salida._origen.id, salida._direccion, self.recuerdo_puerta[salida._ordinal])
                     for salida in self.observadas]
        recuerdos = _ordenado(recuerdos, lambda recuerdo: (recuerdo[0], recuerdo[1]))

        return [sala.id for sala in exploradas], recuerdos

    def restaurar(self, exploradas, recuerdos):
        """Reemplaza todo el conocimiento por el exportado, sin historial (FR-015).

        Explora cada sala de `exploradas`, lo que recalcula las avistadas (FR-004), y copia cada recuerdo.
        Primero valida todo: una sala o dirección que no existe, un recuerdo que no es ABIERTA ni CERRADA o
        una puerta repetida lanzan ValueError sin cambiar nada.

        O(n + e + Σ salidas de las exploradas + (k + p) log n), más O(n log n) la primera vez, para el
        índice por id (`elegir_algoritmo` y búsqueda binaria; sin `dict`).
        """
        salas = []
        for id_sala in exploradas:
            salas.append(self._sala_existente(id_sala))

        vista = [False] * len(self.recuerdo_puerta)
        puertas = []
        for id_sala, direccion, valor in recuerdos:
            salida = self._sala_existente(id_sala).salidas.get(direccion)
            if salida is None:
                raise ValueError(f"La sala {id_sala} no tiene salida {direccion}")
            if valor not in (ABIERTA, CERRADA):
                raise ValueError(f"Recuerdo inválido para la salida {direccion} de la sala {id_sala}: {valor}")
            if vista[salida._ordinal]:
                raise ValueError(f"La salida {direccion} de la sala {id_sala} está repetida")
            vista[salida._ordinal] = True
            puertas.append((salida, valor))

        self.estado_sala = [DESCONOCIDA] * len(self.estado_sala)
        self.recuerdo_puerta = [SIN_OBSERVAR] * len(self.recuerdo_puerta)
        self.reveladas = []
        self.observadas = []

        descartado = []  # restaurar no va al Historial
        for sala in salas:
            self._explorar(sala, descartado)
        for salida, valor in puertas:
            self.observadas.append(salida)
            self.recuerdo_puerta[salida._ordinal] = valor

    def _sala_existente(self, id_sala):
        # Búsqueda binaria en las salas ordenadas por id. O(log n); ValueError si no está.
        if self._por_id is None:
            self._por_id = _ordenado(self._salas, lambda sala: sala.id)

        ini, fin = 0, len(self._por_id)
        try:
            while ini < fin:
                medio = (ini + fin) // 2
                if self._por_id[medio].id < id_sala:
                    ini = medio + 1
                else:
                    fin = medio
        except TypeError:
            raise ValueError(f"La sala {id_sala!r} no existe en la cripta") from None

        if ini < len(self._por_id) and self._por_id[ini].id == id_sala:
            return self._por_id[ini]
        raise ValueError(f"La sala {id_sala!r} no existe en la cripta")


def _ordenado(elementos, clave):
    # Ordenamiento propio del proyecto (prohibido sorted()/list.sort()).
    elementos = list(elementos)
    resultado, _ = elegir_algoritmo(len(elementos))(elementos, clave)
    return resultado


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
