# arma un motor listo para jugar a partir de los datos del gestor (persona B)
# - preparar_partida: partida nueva. Es tambien la "fabrica" que usa el --replay, por eso con la misma cripta y la misma semilla siempre deja el mismo estado inicial.
# - cargar_partida: partida guardada en el archivo binario (S4.10)

from Modelo.Jugador import Jugador
from Modelo.MotorSimulacion import MotorSimulacion
from Persistencia.ConversorPartida import RestauradorPartida, restaurar_jugador
from Persistencia.FormatoBinario import VersionIncompatible

ID_JUGADOR = "jugador"


def _buscar_sala(esqueleto, id_sala):
    for sala in esqueleto:
        if sala.id == id_sala:
            return sala
    return None


def _crear_motor(cripta_id, semilla, gestor):
    detalles = gestor.obtener_detalles(cripta_id)

    # S3.3: el presupuesto de solicitudes se conoce recien con los detalles de la cripta
    if hasattr(gestor.fuente, "fijar_presupuesto"):
        gestor.fuente.fijar_presupuesto(detalles.presupuesto_solicitudes)

    esqueleto = gestor.iniciar_cripta(cripta_id)
    sala_inicial = _buscar_sala(esqueleto, detalles.sala_inicial)

    if sala_inicial is None:
        raise RuntimeError(f"La sala inicial {detalles.sala_inicial} no está en el esqueleto")

    estadisticas = detalles.jugador
    jugador = Jugador(
        ID_JUGADOR,
        vida=estadisticas.vida,
        vida_max=estadisticas.vida,
        ataque=estadisticas.ataque,
        defensa=estadisticas.defensa,
        velocidad=estadisticas.velocidad,
        sala=sala_inicial,
        capacidad_inventario=detalles.inventario_max,
    )

    motor = MotorSimulacion(semilla=semilla, gestor_datos=gestor)
    motor.iniciar_partida(
        jugador, esqueleto, [],
        sala_salida=detalles.sala_salida,
        llave_salida=detalles.llave_salida,
        cripta_id=cripta_id,
    )
    return motor


def preparar_partida(cripta_id, semilla, gestor):
    motor = _crear_motor(cripta_id, semilla, gestor)

    # contenido de la sala inicial: se carga antes de la primera decision del jugador
    sala = motor.jugador.sala
    motor.preparar_sala(sala)
    motor.activar_enemigos_de_sala(sala)
    return motor


def cargar_partida(ruta, gestor):
    restaurador = RestauradorPartida(ruta)

    try:
        encabezado = restaurador.encabezado

        # S4.10: si la cripta o el catalogo cambiaron, la partida no es compatible
        version_cripta = gestor.version_cripta(encabezado.cripta_id)
        if encabezado.version_cripta != version_cripta:
            raise VersionIncompatible(
                f"La partida se guardó con la versión {encabezado.version_cripta} de la cripta "
                f"y la actual es {version_cripta}")

        version_catalogo = gestor.version_catalogo()
        if encabezado.version_catalogo != version_catalogo:
            raise VersionIncompatible(
                f"La partida se guardó con el catálogo {encabezado.version_catalogo} "
                f"y el actual es {version_catalogo}")

        registro_jugador = restaurador.leer_jugador()
        if registro_jugador is None:
            raise VersionIncompatible("El archivo no tiene los datos del jugador")

        motor = _crear_motor(encabezado.cripta_id, encabezado.semilla, gestor)

        # iniciar_partida marco el rastro de la sala inicial con 0; el valor real viene del archivo
        motor.jugador.sala.rastro = None
        restaurar_jugador(motor, registro_jugador)

        # el jugador retoma en su punto de decision, en el instante guardado
        motor.reloj = encabezado.reloj
        motor.jugador.tiempo_siguiente = encabezado.reloj

        # desde aqui cada sala se lee del archivo solo cuando hace falta
        motor.restaurador = restaurador
        sala = motor.jugador.sala
        motor.preparar_sala(sala)
        motor.activar_enemigos_de_sala(sala)
        return motor

    except Exception:
        restaurador.cerrar()
        raise