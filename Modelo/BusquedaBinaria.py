# Búsqueda binaria propia de la línea de tiempo (spec 004, T014; FR-019, FR-020, PR-01).
# Principio I: sin librerías de búsqueda ni de orden, sin heap, sin colecciones especiales, y sin tablas hash
# ni conjuntos como índice. Solo listas y enteros.


def ultimo_menor_o_igual(arreglo, valor):
    """Posición del **último** elemento de ``arreglo`` que es menor o igual que ``valor``, o ``-1`` si todos son mayores
    (o el arreglo está vacío).

    ``arreglo`` debe estar ordenado de forma no decreciente; puede tener repetidos y en ese caso se devuelve la posición
    del último de los iguales (por ejemplo, ``pc_accion`` con un punto regular y el de una carga en la misma acción).
    Con ``reloj_dec``, estrictamente creciente, es la acción en curso en el instante ``valor``. No modifica el arreglo.

    Complejidad (n = len(arreglo)):

    | Operación                     | Tiempo    | Memoria |
    |-------------------------------|-----------|---------|
    | ultimo_menor_o_igual          | O(log n)  | O(1)    |
    | caso vacío o valor menor      | O(1)      | O(1)    |
    """
    bajo = 0
    alto = len(arreglo) - 1
    resultado = -1
    while bajo <= alto:
        medio = (bajo + alto) // 2
        if arreglo[medio] <= valor:
            resultado = medio       # candidato; puede haber otro igual más a la derecha
            bajo = medio + 1
        else:
            alto = medio - 1
    return resultado
