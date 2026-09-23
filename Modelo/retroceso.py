#pergamino
MAX_INTERVALOS =5

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