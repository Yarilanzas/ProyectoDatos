# tabla de puntajes local (S2.12): una linea de texto por partida terminada, siempre se agrega al final
# campos: nombre del jugador, id y version de la cripta, acciones, enemigos derrotados, reloj final y resultado
# no se reescribe nunca: ordenar es una vista que se arma en memoria con los algoritmos propios (S4.9)

from Modelo.ordenamiento import elegir_algoritmo

ARCHIVO_PUNTAJES = "puntajes.txt"
SEPARADOR_CAMPOS = "\t"
NOMBRE_POR_DEFECTO = "Anónimo"

# mejores: primero las victorias y luego menos acciones y menos tiempo; los demas ordenan por un solo campo
CRITERIOS_PUNTAJES = ("mejores", "acciones", "tiempo", "derrotados", "nombre")


def _limpiar_nombre(nombre):
    # tabuladores y saltos de linea romperian el formato: se reemplazan por un espacio
    limpio = " ".join((nombre or "").split())
    return limpio if limpio else NOMBRE_POR_DEFECTO


class Puntaje:
    __slots__ = ("nombre", "cripta_id", "version_cripta", "acciones", "derrotados", "tiempo", "resultado")

    def __init__(self, nombre, cripta_id, version_cripta, acciones, derrotados, tiempo, resultado):
        self.nombre = _limpiar_nombre(nombre)
        self.cripta_id = cripta_id
        self.version_cripta = version_cripta
        self.acciones = acciones
        self.derrotados = derrotados
        self.tiempo = tiempo
        self.resultado = resultado

    # resumen es lo que devuelve motor.resumen_puntaje()
    @classmethod
    def desde_resumen(cls, nombre, cripta_id, version_cripta, resumen):
        return cls(nombre, cripta_id, version_cripta, resumen["acciones"],
                   resumen["enemigos_derrotados"], resumen["tiempo_final"], resumen["resultado"])

    def a_linea(self):
        return SEPARADOR_CAMPOS.join((self.nombre, self.cripta_id, self.version_cripta, str(self.acciones),
                                      str(self.derrotados), str(self.tiempo), self.resultado))

    @classmethod
    def desde_linea(cls, linea):
        campos = linea.rstrip("\r\n").split(SEPARADOR_CAMPOS)
        if len(campos) != 7:
            raise ValueError("la línea no tiene los 7 campos de un puntaje")
        return cls(campos[0], campos[1], campos[2], int(campos[3]), int(campos[4]), int(campos[5]), campos[6])


class TablaPuntajes:
    def __init__(self, ruta=ARCHIVO_PUNTAJES):
        self.ruta = ruta

    def registrar(self, puntaje):
        with open(self.ruta, "a", encoding="utf-8") as archivo:
            archivo.write(puntaje.a_linea() + "\n")

    # puntajes en el orden en que se registraron; una tabla que todavia no existe esta vacia
    def leer(self):
        puntajes = []
        try:
            with open(self.ruta, "r", encoding="utf-8") as archivo:
                for numero, linea in enumerate(archivo, start=1):
                    if linea.strip() == "":
                        continue
                    try:
                        puntajes.append(Puntaje.desde_linea(linea))
                    except ValueError as error:
                        raise ValueError(f"{self.ruta}, línea {numero}: {error}") from error
        except FileNotFoundError:
            pass
        return puntajes

    def ordenados(self, criterio="mejores"):
        if criterio == "mejores":
            def clave(puntaje):
                return (0 if puntaje.resultado == "victoria" else 1, puntaje.acciones, puntaje.tiempo)
        elif criterio == "acciones":
            def clave(puntaje):
                return puntaje.acciones
        elif criterio == "tiempo":
            def clave(puntaje):
                return puntaje.tiempo
        elif criterio == "derrotados":
            def clave(puntaje):
                return -puntaje.derrotados  # el que mas enemigos derroto va primero
        elif criterio == "nombre":
            def clave(puntaje):
                return puntaje.nombre.casefold()
        else:
            raise ValueError(f"El criterio debe ser uno de: {', '.join(CRITERIOS_PUNTAJES)}.")

        puntajes = self.leer()
        algoritmo = elegir_algoritmo(len(puntajes), criterio == "nombre")  # comparar textos es mas caro
        ordenados, _ = algoritmo(puntajes, clave)
        return ordenados