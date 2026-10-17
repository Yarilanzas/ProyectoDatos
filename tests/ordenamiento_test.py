import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modelo.ordenamiento import (
    insertion_sort, binary_insertion_sort, merge_sort,
    elegir_algoritmo, casi_ordenado, cuenta_desorden,
    UMBRAL_TAMANO,
)


def verifica_ordenado(nombre, algoritmo, datos):
    resultado, comparaciones = algoritmo(list(datos), key=lambda x: x)
    assert resultado == sorted(datos), f"{nombre} no ordenó bien: {resultado}"
    return comparaciones


print("--- correctitud de los tres algoritmos ---")
casos = {
    "vacío": [],
    "un elemento": [5],
    "dos elementos": [2, 1],
    "ya ordenado": [1, 2, 3, 4, 5],
    "orden inverso": [5, 4, 3, 2, 1],
    "con repetidos": [3, 1, 3, 2, 1],
    "aleatorio": [8, 1, 9, 3, 5, 2, 7, 4, 6],
}
for nombre_caso, datos in casos.items():
    for nombre_algo, algo in [
        ("insertion_sort", insertion_sort),
        ("binary_insertion_sort", binary_insertion_sort),
        ("merge_sort", merge_sort),
    ]:
        verifica_ordenado(f"{nombre_algo} ({nombre_caso})", algo, datos)
print("los tres algoritmos ordenan correctamente en todos los casos, incluyendo listas de 0, 1 y 2 elementos")

print("\n--- elegir_algoritmo: tamaño y comparación costosa ---")
assert elegir_algoritmo(5, comparacion_costosa=False) is insertion_sort
assert elegir_algoritmo(5, comparacion_costosa=True) is binary_insertion_sort
assert elegir_algoritmo(UMBRAL_TAMANO + 1, comparacion_costosa=False) is merge_sort
assert elegir_algoritmo(UMBRAL_TAMANO + 1, comparacion_costosa=True) is merge_sort
print("elige correctamente según tamaño y comparación costosa")

print("\n--- elegir_algoritmo: casi_ordenado tiene prioridad ---")
assert elegir_algoritmo(UMBRAL_TAMANO + 1, comparacion_costosa=False, casi_ordenado=True) is insertion_sort
assert elegir_algoritmo(UMBRAL_TAMANO + 1, comparacion_costosa=True, casi_ordenado=True) is insertion_sort
assert elegir_algoritmo(5, comparacion_costosa=True, casi_ordenado=True) is insertion_sort
print("casi_ordenado=True siempre elige insertion_sort, sin importar tamaño/comparación")

print("\n--- casi_ordenado() (la función de detección) ---")
assert casi_ordenado(list(range(100)), key=lambda x: x) is True
assert casi_ordenado(list(range(100, 0, -1)), key=lambda x: x) is False
assert casi_ordenado([], key=lambda x: x) is True
assert casi_ordenado([1], key=lambda x: x) is True
assert casi_ordenado([2, 1], key=lambda x: x) is False  # 1 de 1 pares fuera de orden = 100%

datos_un_poco_desordenados = list(range(20))
datos_un_poco_desordenados[5], datos_un_poco_desordenados[6] = (
    datos_un_poco_desordenados[6], datos_un_poco_desordenados[5]
)
assert casi_ordenado(datos_un_poco_desordenados, key=lambda x: x) is True
print("detecta correctamente datos ordenados, invertidos, cortos y casi ordenados")

print("\n--- cuenta_desorden ---")
assert cuenta_desorden([], key=lambda x: x) == (0, 0)
assert cuenta_desorden([1], key=lambda x: x) == (0, 0)
fuera, pares = cuenta_desorden([1, 2, 3, 4], key=lambda x: x)
assert fuera == 0 and pares == 3
fuera, pares = cuenta_desorden([4, 3, 2, 1], key=lambda x: x)
assert fuera == 3 and pares == 3
print("cuenta bien los pares fuera de orden, incluyendo listas de 0 y 1 elemento")

print("\nTodos los tests de ordenamiento pasaron.")