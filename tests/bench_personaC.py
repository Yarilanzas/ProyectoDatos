import time
import random
import json

import sys
import os
import io
import contextlib

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(RAIZ)

from Modelo.Inventario import Inventario,NodoInventario
from Modelo.ordenamiento import insertion_sort,binary_insertion_sort,merge_sort, casi_ordenado
from Modelo.retroceso import Historial,Cambio

ARCHIVO_RESULTADOS = os.path.join(RAIZ, "resultados_bench_ordenamiento.txt")

def bench_ordenamiento():
    print("\n-Ordenamiento-")
    tams = [10, 32, 100, 1000, 10000]
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

def  bench_ordenamiento_casi_ordenado():
    print("\n-Ordenamiento datos casi ordenados-")
    tams = [100, 1000, 10000]
    proporcion = 0.05
    algoritmos = {
        "insertion_sort": insertion_sort,
        "merge_sort": merge_sort,
    }
    for n in tams:
        datos_base = list(range(n))
        n_swaps = max(1, int(n * proporcion))
        for _ in range(n_swaps):
            i = random.randint(0, n-2)
            datos_base[i], datos_base[i+1] = datos_base[i+1], datos_base[i]
        detectado = casi_ordenado(datos_base, key=lambda x: x)
        print(f"n = {n:6d} casi ordenado detecto = {detectado}")

        for nombre,algoritmo in algoritmos.items():
            datos = list(datos_base)
            inicio = time.perf_counter()
            _, comparaciones = algoritmo(datos, key=lambda x: x)
            duracion = time.perf_counter() - inicio
            print(f"n = {n:6d} {nombre:22s} tiempo = {duracion:.6f}s comparaciones = {comparaciones}")

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
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        bench_inventario()
        bench_ordenamiento()
        bench_ordenamiento_casi_ordenado()
        bench_retroceso()
        bench_serializacion()
    salida = buffer.getvalue()
    print(salida, end="")

    with open(ARCHIVO_RESULTADOS, "w", encoding="utf-8") as archivo:
        archivo.write(salida)

if __name__ == "__main__":
    correr_bench()
