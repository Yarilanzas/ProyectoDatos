import time
import random
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modelo.Inventario import Inventario,NodoInventario
from Modelo.ordenamiento import insertion_sort,binary_insertion_sort,merge_sort
from Modelo.retroceso import Historial,Cambio

def bench_ordenamiento():
    print("\n-Ordenamiento-")
    tams = [10, 20, 30, 50, 75, 100]
    algoritmos = {
        "insertion_sort":insertion_sort,
        "binary_insertion_sort":binary_insertion_sort,
        "merge_sort":merge_sort,
    }
    for n in tams:
        datos_base = list(range(n))
        random.shuffle(datos_base)
        for nombre,algoritmo in algoritmos.items():
            datos = list(datos_base)
            inicio = time.perf_counter()
            _, comparaciones = algoritmo(datos, key=lambda x: x)
            duracion = time.perf_counter() - inicio
            print(f"n = {n:5d} {nombre:22s} tiempo = {duracion:.6f}s comparaciones = {comparaciones}")


def bench_inventario():
    print("\n-Inventario-")
    n = 500
    inv = Inventario(cap_max=n)

    inicio = time.perf_counter()
    for i in range(n):
        nodo = NodoInventario(f"i{i}", "tipo", f"Objeto {i}", 1,1,"arma")
        inv.recoge(nodo)
    duracion_recoger = time.perf_counter() - inicio
    print(f"recoger {n} objetos: {duracion_recoger:.6f}s")

    inicio = time.perf_counter()
    for _ in range(n):
        inv.avanza()
    duracion_avanzar = time.perf_counter() - inicio
    print(f"avanza {n} veces: {duracion_avanzar:.6f}s")

    inicio = time.perf_counter()
    while inv.actual() is not None:
        inv.suelta_actual()
    duracion_soltar = time.perf_counter() - inicio
    print(f"soltar {n} objetos: {duracion_soltar:.6f}s")

def bench_retroceso():
    print("\n-Retroceso-")
    historial = Historial()
    n_intervalos = 5
    cambios_por_intervalo = 50

    inicio = time.perf_counter()
    for _ in range(n_intervalos):
        historial.abrir_intervalo()
        for _ in range(cambios_por_intervalo):
            historial.registrar(deshacer=lambda: None, description="cambio de prueba")
    duracion_registrar = time.perf_counter() - inicio
    print(f"registrar {n_intervalos * cambios_por_intervalo} cambios: {duracion_registrar:.6f}s")

    inicio = time.perf_counter()
    while historial.puede_deshacer():
        historial.deshacer_ultimo()
    duracion_deshacer = time.perf_counter() - inicio
    print(f"deshacer {n_intervalos} intervalos: {duracion_deshacer:.6f}s")

def bench_serializacion():
    print("\n-Serialización (binario vs JSON)-")
    n = 200
    inv = Inventario(cap_max=n)
    for i in range(n):
        nodo = NodoInventario(f"i{i}", "tipo", f"Objeto {i}", 1, 1, "arma", ataque_bonus=1)
        inv.recoge(nodo)

    datos_bin = inv.to_bytes()
    datos_json = json.dumps(inv.to_dict()).encode("utf-8")
    print(f"tamaño binario: {len(datos_bin)} bytes")
    print(f"tamaño JSON:    {len(datos_json)} bytes")

    repeticiones = 200

    inicio = time.perf_counter()
    for _ in range(repeticiones):
        Inventario.from_bytes(datos_bin)
    duracion_bin = (time.perf_counter() - inicio) / repeticiones
    print(f"tiempo de carga binario (promedio): {duracion_bin*1e6:.2f} µs")

    inicio = time.perf_counter()
    for _ in range(repeticiones):
        dict_reconstruido = json.loads(datos_json.decode("utf-8"))
        Inventario.from_dict(dict_reconstruido)
    duracion_json = (time.perf_counter() - inicio) / repeticiones
    print(f"tiempo de carga JSON (promedio):    {duracion_json*1e6:.2f} µs")

def correr_bench():
    bench_inventario()
    bench_ordenamiento()
    bench_retroceso()
    bench_serializacion()

if __name__ == "__main__":
    correr_bench()
