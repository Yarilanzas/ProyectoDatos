#pergamino
MAX_INTERVALOS = 5

class Cambio:
    __slots__ = ("deshacer", "description")

    def __init__(self,deshacer,description=""):
        self.deshacer = deshacer
        self.description = description

class Historial:
    def __init__(self):
        self._intervalos = []
        self._intervalos_actual = None

   #se llama cuando el jugador ejecuta accion que consume tiempo
    def abrir_intervalo(self):
        self._intervalos_actual = []
        self._intervalos.append(self._intervalos_actual)
        if len(self._intervalos) > MAX_INTERVALOS:
            self._intervalos.pop(0)

    #llama motor A cada q muta algo reversible, si hay intervalo abierto, no hace nada
    # evita registrar los cambios que pasan antes de la primera accion del jugador
    def registrar(self, deshacer,description=""):
        if self._intervalos_actual is not None:
            self._intervalos_actual.append(Cambio(deshacer,description))

    def puede_deshacer(self):
        return len(self._intervalos) > 0

    def deshacer_ultimo(self):
        if not self.puede_deshacer():
            return False
        intervalo = self._intervalos.pop()
        for cambio in reversed(intervalo):
            cambio.deshacer()
        self._intervalos_actual = self._intervalos[-1] if self._intervalos else None
        return True

def usar_pergamino(inventario, historial, nodo_pergamino):
    if not historial.puede_deshacer():
        return False

    inventario.suelta_nodo(nodo_pergamino)
    historial.deshacer_ultimo()
    return True

def recoger_reversible(inventario, nodo, historial):
    exito = inventario.recoge(nodo)
    if exito and nodo.clase != "pergamino_retroceso":
        historial.registrar(deshacer = lambda: inventario.suelta_nodo(nodo),
                        description =f"recoger {nodo.nombre}")
    return exito

def soltar_reversible(inventario, nodo, historial):
    anterior_guardado = nodo.anterior
    siguiente_guardado = nodo.siguiente

    resultado = inventario.suelta_nodo(nodo)
    if resultado is None:
        return None

    if nodo.clase != "pergamino_retroceso":
        historial.registrar(deshacer=lambda: inventario._reinsertar(nodo,anterior_guardado, siguiente_guardado),
                        description=f"soltar {nodo.nombre}")
    return resultado

def equipar_reversible(inventario, historial):
    nodo = inventario.actual()
    if nodo is None:
        return None

    anterior_guardado = nodo.anterior
    siguiente_guardado = nodo.siguiente
    era_cabeza = nodo is inventario._cabeza

    if nodo.clase == "arma":
        equipado_anterior = inventario._arma_equipada
    elif nodo.clase == "armadura":
        equipado_anterior = inventario._armadura_equipada
    else:
        equipado_anterior = None

    resultado  = inventario.equipar_actual()

    if nodo.clase != "pergamino_retroceso":
        def deshacer():
            if not era_cabeza:
                inventario.suelta_nodo(nodo)
                inventario._reinsertar(nodo, anterior_guardado, siguiente_guardado)
            if nodo.clase == "arma":
                inventario._arma_equipada = equipado_anterior
            elif nodo.clase == "armadura":
                inventario._armadura_equipada = equipado_anterior

        historial.registrar(deshacer=deshacer,description=f"equipar {nodo.nombre}")
    return resultado