# Bitácora en pantalla (§4.8): solo se conservan los últimos N mensajes.
#
# Buffer circular sobre una lista de tamaño fijo: agregar es O(1) y la memoria
# es constante durante toda la partida. Nunca se desplazan los mensajes
# anteriores; al llenarse, el mensaje nuevo sobrescribe al más antiguo.

CAPACIDAD_PANTALLA = 20


class RegistroMensajes:
    __slots__ = ("_datos", "_inicio", "_cantidad")

    def __init__(self, capacidad=CAPACIDAD_PANTALLA):
        if capacidad < 1:
            raise ValueError("La capacidad debe ser al menos 1")

        self._datos = [None] * capacidad
        self._inicio = 0      # posición del mensaje más antiguo
        self._cantidad = 0

    def agregar(self, texto):
        capacidad = len(self._datos)
        sobreescribio = self._cantidad == capacidad
        anterior = self._datos[self._inicio] if sobreescribio else None

        if not sobreescribio:
            self._datos[(self._inicio + self._cantidad) % capacidad] = texto
            self._cantidad += 1
        else:
            self._datos[self._inicio] = texto
            self._inicio = (self._inicio + 1) % capacidad
        return sobreescribio,anterior

    def deshacer_ultimo(self, sobreescribio, anterior):
        if sobreescribio:
            self._inicio = (self._inicio - 1) % len(self._datos)
            self._datos[self._inicio] = anterior
        else:
            self._cantidad -= 1

    def ultimos(self):
        # De más antiguo a más reciente, listo para mostrar en pantalla.
        capacidad = len(self._datos)
        return [self._datos[(self._inicio + i) % capacidad]
                for i in range(self._cantidad)]

    def __len__(self):
        return self._cantidad
