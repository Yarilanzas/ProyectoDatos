# on^2 en el peor caso, pero casi 0n si ya viene ordenadillo
def insertion_sort(items, key):
    arr = list(items)
    comparacion = 0
    for i in range(1,len(arr)):
        actual = arr[i]
        valor = key(actual)
        j = i-1
        while j >= 0:
            comparacion +=1
            if key(arr[j]) <= valor:
                break
            arr[j+1] = arr[j]
            j -= 1
        arr[j+1] = actual
    return arr,comparacion

#igual pero binario para ubicar la pos, o logn comparaciones por insertion
#sirve cuando comparar es caro
def binary_insertion_sort(items, key):
    arr = list(items)
    comparacion = 0
    for i in range(1,len(arr)):
        actual = arr[i]
        valor = key(actual)

        ini,fin = 0, i
        while ini < fin:
            medio = (ini+fin)//2
            comparacion +=1
            if key(arr[medio]) <= valor:
                ini = medio+1
            else:
                fin = medio
        for j in range(i, ini, -1):
            arr[j] = arr[j-1]
        arr[ini] = actual
    return arr,comparacion

def merge_sort(items, key):
    arr = list(items)
    comparacion = [0]
    resultado = _merge_sort_rec(arr, key, comparacion)
    return resultado, comparacion[0]

def _merge_sort_rec(arr, key, comparacion):
    if len(arr) <= 1:
        return arr
    medio = len(arr)//2
    left = _merge_sort_rec(arr[:medio],key,comparacion)
    right = _merge_sort_rec(arr[medio:],key,comparacion)
    return _merge(left, right,key, comparacion)

def _merge(left, right, key, comparacion):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        comparacion[0] += 1
        if key(left[i]) <= key(right[j]):
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

UMBRAL_TAMANO = 32

def elegir_algoritmo(n,comparacion_costosa=False):
    if n <= UMBRAL_TAMANO:
        return binary_insertion_sort if comparacion_costosa else insertion_sort
    return merge_sort