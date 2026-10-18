import argparse

from API.Fuentes import FuenteDatosHTTP, FuenteDatosOffline
from Gestor.GestorDatos import GestorDatos
from Gestor.PreparadorPartida import preparar_partida
from Bitacora.BitacoraPartida import leer_bitacora
from Bitacora.Reproductor import Reproductor
from Controlador.ControladorPartida import ControladorPartida
from Persistencia.FormatoBinario import VersionIncompatible
from Persistencia.TablaPuntajes import ARCHIVO_PUNTAJES, CRITERIOS_PUNTAJES, TablaPuntajes
from Vista.VistaConsola import VistaConsola


def crear_gestor(argumentos):
    if argumentos.offline:
        fuente = FuenteDatosOffline(argumentos.offline)
    else:
        fuente = FuenteDatosHTTP()

    return GestorDatos(
        fuente,
        ruta_base=argumentos.datos_locales,
        cache_size=argumentos.cache_size,
    )


def ejecutar_replay(ruta, gestor, vista):
    # S4.11: se reconstruye la partida con la misma cripta y semilla y se repiten las acciones
    encabezado, _ = leer_bitacora(ruta)

    # versiones ACTUALES: si no coinciden con las de la bitacora el Reproductor lo reporta
    version_cripta = gestor.version_cripta(encabezado.cripta_id)
    version_catalogo = gestor.version_catalogo()

    def fabrica_motor(cripta_id, semilla):
        return preparar_partida(cripta_id, semilla, gestor)

    reproductor = Reproductor(fabrica_motor, version_cripta, version_catalogo)
    motor = reproductor.reproducir(ruta)

    vista.mostrar("Reproducción finalizada.")
    vista.mostrar_estado(motor)
    vista.mostrar(f"Resumen: {motor.resumen_puntaje()}")
    return motor


def main():
    parser = argparse.ArgumentParser(description="Cliente del proyecto Cripta")

    parser.add_argument(
        "--bench",
        action="store_true",
        help="Ejecuta el benchmark de persistencia",
    )
    parser.add_argument(
        "--replay",
        metavar="ARCHIVO",
        help="Reproduce una partida desde una bitácora",
    )
    parser.add_argument(
        "--cripta",
        metavar="ID",
        help="Empieza una partida nueva en esa cripta (sin esto se muestra la lista)",
    )
    parser.add_argument(
        "--semilla",
        type=int,
        help="Semilla de la partida nueva (por defecto una al azar)",
    )
    parser.add_argument(
        "--cargar",
        metavar="ARCHIVO",
        help="Continúa una partida guardada",
    )
    parser.add_argument(
        "--puntajes",
        default=ARCHIVO_PUNTAJES,
        metavar="ARCHIVO",
        help="Tabla de puntajes donde se registra cada partida terminada",
    )
    parser.add_argument(
        "--mostrar-puntajes",
        nargs="?",
        const="mejores",
        choices=CRITERIOS_PUNTAJES,
        metavar="CRITERIO",
        help="Muestra la tabla de puntajes (mejores, acciones, tiempo, derrotados o nombre) y termina",
    )
    parser.add_argument(
        "--bitacora",
        default="partida.log",
        help="Archivo donde se anotan las acciones de la partida",
    )
    parser.add_argument(
        "--offline",
        metavar="CARPETA",
        help="Utiliza una fuente de datos offline",
    )
    parser.add_argument(
        "--datos-locales",
        default="datos_locales",
        help="Carpeta de persistencia local",
    )
    parser.add_argument(
        "--cache-size",
        type=int,
        default=25,
        help="Cantidad máxima de fichas en caché",
    )

    argumentos = parser.parse_args()

    if argumentos.bench:
        from tests.bench_personaD import correr_bench as bench_persistencia
        from tests.bench_ciclo import correr_bench as bench_ciclo

        bench_persistencia()
        print()
        bench_ciclo()
        return 0

    vista = VistaConsola()

    if argumentos.mostrar_puntajes:
        try:
            puntajes = TablaPuntajes(argumentos.puntajes).ordenados(argumentos.mostrar_puntajes)
        except (ValueError, OSError) as error:
            vista.mostrar_error(str(error))
            return 1
        vista.mostrar_puntajes(puntajes, argumentos.mostrar_puntajes)
        return 0

    gestor = crear_gestor(argumentos)

    if argumentos.replay:
        try:
            ejecutar_replay(argumentos.replay, gestor, vista)
        except VersionIncompatible as error:
            vista.mostrar_error(f"Versión incompatible: {error}")
            return 2
        except (ValueError, RuntimeError, OSError) as error:
            vista.mostrar_error(str(error))
            return 1
        return 0

    controlador = ControladorPartida(gestor, vista, argumentos.bitacora, argumentos.puntajes)

    try:
        if argumentos.cargar:
            controlador.cargar(argumentos.cargar)
        else:
            cripta_id = argumentos.cripta or controlador.elegir_cripta()
            if not cripta_id:
                return 0
            controlador.nueva_partida(cripta_id, argumentos.semilla)
    except VersionIncompatible as error:
        vista.mostrar_error(f"Versión incompatible: {error}")
        return 2
    except (ValueError, RuntimeError, OSError) as error:
        vista.mostrar_error(str(error))
        return 1

    controlador.jugar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
