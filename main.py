import argparse
import os
import shutil
import tempfile

from API.Fuentes import FuenteDatosHTTP, FuenteDatosOffline
from Gestor.GestorDatos import GestorDatos
from Gestor.PreparadorPartida import cargar_partida, preparar_partida, verificar_cripta
from Bitacora.BitacoraPartida import leer_bitacora
from Bitacora.Reproductor import Reproductor
from Controlador.ConsultaHistoria import ConsultaHistoria
from Controlador.ControladorPartida import ControladorPartida, CriptaNoResoluble, guardar_motor
from Gestor.GestorHistorico import SinDatosParaHistoria
from Modelo.LineaTiempo import ErrorReconstruccion, K_POR_OMISION, ReferenciaInvalida
from Persistencia.FormatoBinario import VersionIncompatible
from Persistencia.TablaPuntajes import ARCHIVO_PUNTAJES, CRITERIOS_PUNTAJES, TablaPuntajes
from Vista.VistaConsola import VistaConsola
import logging

def configurar_logging(archivo="cripta.log"):
    logging.basicConfig(
        filename=archivo,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )

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


def _cerrar_restaurador(motor):
    if motor is not None and motor.restaurador is not None:
        motor.restaurador.cerrar()
        motor.restaurador = None


def ejecutar_replay(ruta, gestor, consulta=None):
    """S4.11: reconstruye la partida con la misma cripta y semilla y repite las acciones. Sin vista
    (Principio II, PR-14): quien llama muestra el resultado. Devuelve el motor final.

    `consulta` (una `ConsultaHistoria`, para `--hasta`, spec 004 T063b) es opcional: da el observador del `Reproductor` y
    recibe el motor final con `al_terminar`, **dentro** del `try`, antes del `finally` que cierra los restauradores y borra
    la carpeta temporal (el estado final y los clones de la línea todavía leen archivos abiertos). La recarga de cada
    `@cargar` es la de siempre: el propio `Reproductor` avisa al observador tras cada una.

    Cada `@cargar` repite la carga real (FR-017, PR-12): guarda el motor en un archivo temporal y lo carga
    con `cargar_partida`. La recarga NO ejecuta la verificación de resolubilidad (`--verificar`, FR-022 de
    la spec 002): `cargar_partida` no la llama. El restaurador anterior se cierra tras cada recarga y el
    último antes de borrar el temporal, porque en Windows no se puede borrar un archivo abierto.
    """
    encabezado, _ = leer_bitacora(ruta)

    # versiones ACTUALES: si no coinciden con las de la bitacora el Reproductor lo reporta
    version_cripta = gestor.version_cripta(encabezado.cripta_id)
    version_catalogo = gestor.version_catalogo()

    def fabrica_motor(cripta_id, semilla):
        return preparar_partida(cripta_id, semilla, gestor)

    carpeta = tempfile.mkdtemp(prefix="cripta_replay_")
    abiertos = []  # motores que pueden tener el temporal abierto

    def recargar(motor):
        temporal = os.path.join(carpeta, f"recarga_{len(abiertos)}.cripta")
        guardar_motor(motor, temporal, gestor)
        _cerrar_restaurador(motor)  # el motor anterior ya no se usa
        nuevo = cargar_partida(temporal, gestor)
        abiertos.append(nuevo)
        return nuevo

    try:
        observador = None if consulta is None else consulta.preparar(encabezado.cripta_id)
        reproductor = Reproductor(fabrica_motor, version_cripta, version_catalogo, recargar=recargar,
                                  observador=observador)
        motor_final = reproductor.reproducir(ruta)
        if consulta is not None:
            consulta.al_terminar(motor_final)
        return motor_final
    finally:
        if consulta is not None:
            consulta.cerrar()  # suelta el clon de la línea y borra sus copias antes de cerrar lo demás
        for motor in abiertos:
            _cerrar_restaurador(motor)
        shutil.rmtree(carpeta, ignore_errors=True)


def _mostrar_error(texto):
    # mismo formato que VistaConsola.mostrar_error, sin instanciar la vista (--replay, Principio II)
    print(f"! Error: {texto}")


# errores de datos y de la línea de tiempo que terminan con `! Error: ...` y código 1. `SinDatosParaHistoria` (falta un dato
# local y no se puede pedir a la red) es un RuntimeError; se nombra aparte para que no dependa de eso. Un guion que no
# coincide con la partida es `VersionIncompatible` (código 2), no está aquí.
ERRORES_DE_DATOS = (ValueError, RuntimeError, OSError, SinDatosParaHistoria, ErrorReconstruccion, ReferenciaInvalida)


def _entero(texto, minimo):
    """El entero que dice `texto` (solo dígitos ASCII, sin signo ni punto ni espacios) si es >= `minimo`; si no, None."""
    if texto is None or not (texto.isascii() and texto.isdigit()):
        return None
    valor = int(texto)
    return valor if valor >= minimo else None


def validar_opciones_de_historia(argumentos):
    """Valida `--hasta` y `--checkpoint-cada` (spec 004, T063a; contracts/comandos-historia.md, «Validación»). Se leen como
    texto y se validan a mano: `argparse` con `type=int` terminaría con código 2, reservado a «versión incompatible» (HL11).
    Es un error de uso (código 1) y se detecta antes de abrir la fuente de datos, de crear el gestor o de leer un archivo.

    Devuelve `(mensaje de error o None, hasta, k)` con `hasta` y `k` ya como enteros (None si no se pasaron). No es un modo
    ni cambia la tabla de prioridad: `--bench` ya terminó antes de llamarla."""
    hasta = k = None
    if argumentos.hasta is not None:
        hasta = _entero(argumentos.hasta, 0)
        if hasta is None:
            return (f"--hasta requiere un entero mayor o igual que 0 (recibido: {argumentos.hasta}).", None, None)
    if argumentos.checkpoint_cada is not None:
        k = _entero(argumentos.checkpoint_cada, 1)
        if k is None:
            return (f"--checkpoint-cada requiere un entero mayor o igual que 1 (recibido: {argumentos.checkpoint_cada}).",
                    None, None)
    if hasta is not None and not argumentos.replay:
        return ("--hasta solo se puede usar junto con --replay.", None, None)
    # con --replay, --mostrar-puntajes o --verificar mandando, --cargar no se ejecuta: K no le toca
    manda_cargar = argumentos.cargar and not (argumentos.replay or argumentos.mostrar_puntajes or argumentos.verificar)
    if k is not None and manda_cargar:
        return ("--checkpoint-cada no se puede usar al cargar una partida: rige el valor guardado en el archivo.",
                None, None)
    return (None, hasta, k)


def main():

    parser = argparse.ArgumentParser(description="Cliente del proyecto Cripta")

    parser.add_argument(
        "--bench",
        action="store_true",
        help="Ejecuta las mediciones de persistencia, ciclo de eventos, cazador, resolubilidad y niebla de guerra / «ir a»",
    )
    parser.add_argument(
        "--verificar",
        metavar="ID",
        help="Solo verifica si la cripta es resoluble y muestra el resultado; no inicia partida",
    )
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="Inicia la partida nueva aunque la cripta no sea resoluble, sin mostrar el orden ni el reporte",
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
        "--hasta",
        metavar="T",
        help="Con --replay: muestra el estado en el instante T (entero >= 0) en vez de reproducir la bitácora entera",
    )
    parser.add_argument(
        "--checkpoint-cada",
        metavar="K",
        help="Máximo de acciones entre puntos de control de la línea de tiempo (entero >= 1; por defecto 50). Solo cambia el costo",
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
        from tests.bench_cazador import correr_bench as bench_cazador
        from tests.bench_resolubilidad import correr_bench as bench_resolubilidad
        from tests.bench_niebla import correr_bench as bench_niebla

        bench_persistencia()
        print()
        bench_ciclo()
        print()
        bench_cazador()
        print()
        bench_resolubilidad()
        print()
        bench_niebla()
        return 0

    # --hasta y --checkpoint-cada son modificadores, no modos: se validan (código 1) después de --bench, que los ignora, y
    # antes de abrir la fuente o leer cualquier archivo (spec 004, contracts/comandos-historia.md)
    error, hasta, k_linea = validar_opciones_de_historia(argumentos)
    if error is not None:
        _mostrar_error(error)
        return 1

    # la prioridad de opciones es contrato publico: --bench, --mostrar-puntajes, --verificar (spec 002,
    # FR-017), --replay y luego la partida. --replay se atiende antes de crear la vista porque no debe
    # instanciarla (Principio II, PR-14); por eso cede explicitamente ante --mostrar-puntajes y --verificar
    if argumentos.replay and not argumentos.mostrar_puntajes and not argumentos.verificar:
        configurar_logging()
        gestor = crear_gestor(argumentos)
        consulta = None if hasta is None else ConsultaHistoria(gestor, hasta, k_linea or K_POR_OMISION)
        try:
            motor = ejecutar_replay(argumentos.replay, gestor, consulta)
        except VersionIncompatible as error:
            _mostrar_error(f"Versión incompatible: {error}")
            return 2
        except ERRORES_DE_DATOS as error:
            _mostrar_error(str(error))
            return 1
        if consulta is not None:
            # --replay --hasta: solo el resumen (el mismo texto que `historia`), sin «Reproducción finalizada.» ni puntaje
            for linea in consulta.lineas:
                print(linea)
            return 0
        print("Reproducción finalizada.")
        print(f"Reloj: {motor.reloj}  Sala: {motor.jugador.sala.id}  Vida: {motor.jugador.vida}")
        print(f"Resumen: {motor.resumen_puntaje()}")
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

    if argumentos.verificar:
        # spec 002 (FR-015, FR-016, FR-025): solo verifica. Sin controlador, bitácora, partida ni puntajes;
        # código 0 sea cual sea el veredicto y 1 si no se pudieron obtener los datos
        configurar_logging()
        gestor = crear_gestor(argumentos)
        try:
            resultado = verificar_cripta(argumentos.verificar, gestor)
        # ErrorCliente y sus subclases (presupuesto, 429/5xx, respuesta inválida) heredan de RuntimeError, igual que
        # la falta de un archivo offline: sin veredicto y código 1 (FR-024, FR-025)
        except (ValueError, RuntimeError, OSError) as error:
            vista.mostrar_error(str(error))
            return 1
        vista.mostrar_verificacion(resultado)
        return 0

    configurar_logging()
    gestor = crear_gestor(argumentos)

    controlador = ControladorPartida(gestor, vista, argumentos.bitacora, argumentos.puntajes)
    if k_linea is not None:
        controlador.k_linea = k_linea  # la partida nueva arma su línea con este K; --cargar ya lo rechazó arriba

    try:
        if argumentos.cargar:
            controlador.cargar(argumentos.cargar)
        else:
            cripta_id = argumentos.cripta or controlador.elegir_cripta()
            if not cripta_id:
                return 0
            # --forzar solo se lee aquí (spec 002, FR-021): --cargar y --replay lo ignoran y no verifican (FR-022), y
            # con --verificar no tiene efecto (FR-017)
            controlador.nueva_partida(cripta_id, argumentos.semilla, forzar=argumentos.forzar)
    except CriptaNoResoluble as error:
        # spec 002 (FR-018, FR-020): antes que los errores de datos. nueva_partida la lanza antes de crear motor y
        # bitácora, así que no queda bitácora ni se toca la tabla de puntajes
        vista.mostrar_error(str(error))
        vista.mostrar_verificacion(error.resultado)
        return 1
    except VersionIncompatible as error:
        vista.mostrar_error(f"Versión incompatible: {error}")
        return 2
    # errores de datos de la verificación o de la partida (ErrorCliente hereda de RuntimeError): sin veredicto y
    # código 1, también con --forzar, que no los silencia (FR-024, FR-025)
    except ERRORES_DE_DATOS as error:
        vista.mostrar_error(str(error))
        return 1

    controlador.jugar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
