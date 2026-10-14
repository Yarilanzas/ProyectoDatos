import os
import tempfile
import time

from Persistencia.ArchivoPartida import guardar_partida, LectorPartida
from Persistencia.ExportadorJSON import guardar_partida_json, cargar_partida_json, leer_sala_json
from Persistencia.RegistroSala import RegistroSala
from Persistencia.RegistroJugador import RegistroJugador
from Modelo.Inventario import Inventario, NodoInventario

REPETICIONES = 5
TAMANOS = [20, 200, 2000]
ARCHIVO_RESULTADOS = "resultados_bench_personaD.txt"

# salas sinteticas, la cantidad de enemigos, objetos y trampas varía según el id
def crear_registros(n):
    registros = []
    for i in range(1, n + 1):
        enemigos = [(f"e-{i}-{k}", "ent_rata_gigante", 12, -1 if k % 2 else i * 10 + 100) for k in range(i % 4)]
        objetos = [(f"obj-{i}-{k}", "itm_daga_oxidada") for k in range(i % 3)]
        trampas = [(f"t-{i}", "trp_dardos", True)] if i % 5 == 0 else []
        puertas = [("N", False), ("E", i % 2 == 0)]
        registros.append(RegistroSala(i, i * 10, enemigos, objetos, trampas, puertas))
    return registros


# jugador con el inventario lleno (10 objetos), igual en los dos formatos
def crear_jugador():
    inventario = Inventario(10)
    for k in range(10):
        inventario.recoge(NodoInventario(f"obj-inv-{k}", "itm_daga_oxidada", "Daga oxidada", 2, 5, "arma", 3, 0))
    return RegistroJugador(1, 30, 120, 4, False, inventario)


# se repite y se toma la mediana (menos sensible a un pico aislado que el mejor tiempo)
def medir(funcion):
    tiempos = []

    for _ in range(REPETICIONES):
        inicio = time.perf_counter()
        funcion()
        tiempos.append(time.perf_counter() - inicio)

    tiempos.sort()
    return tiempos[len(tiempos) // 2]


def bench_formatos(lineas):
    lineas.append("-Guardado binario vs JSON-")
    with tempfile.TemporaryDirectory() as carpeta:
        ruta_bin = os.path.join(carpeta, "partida.bin")
        ruta_json = os.path.join(carpeta, "partida.json")

        for n in TAMANOS:
            registros = crear_registros(n)
            jugador = crear_jugador()
            sala_buscada = n // 2

            def guardar_bin():
                guardar_partida(ruta_bin, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros, jugador)

            def guardar_json():
                guardar_partida_json(ruta_json, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros, jugador)

            def cargar_todo_bin():
                with LectorPartida(ruta_bin) as lector:
                    lector.leer_todas_salas()

            def una_sala_bin():
                with LectorPartida(ruta_bin) as lector:
                    lector.leer_sala(sala_buscada)

            def cargar_todo_json():
                cargar_partida_json(ruta_json)

            def una_sala_json():
                leer_sala_json(ruta_json, sala_buscada)

            guardar_bin()
            guardar_json()
            lineas.append(f"n = {n:5d} tamaño:         binario = {os.path.getsize(ruta_bin):7d} B   json = {os.path.getsize(ruta_json):7d} B")
            lineas.append(f"n = {n:5d} guardar:        binario = {medir(guardar_bin):.6f}s  json = {medir(guardar_json):.6f}s")
            lineas.append(f"n = {n:5d} cargar todo:    binario = {medir(cargar_todo_bin):.6f}s  json = {medir(cargar_todo_json):.6f}s")
            lineas.append(f"n = {n:5d} cargar 1 sala:  binario = {medir(una_sala_bin):.6f}s  json = {medir(una_sala_json):.6f}s")


def correr_bench():
    lineas = []
    bench_formatos(lineas)
    for linea in lineas:
        print(linea)

    with open(ARCHIVO_RESULTADOS, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas) + "\n")


if __name__ == "__main__":
    correr_bench()