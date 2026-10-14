import shutil
import tempfile
import time
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Cache.CacheCatalogo import CacheCatalogo
from Cache.Estructuras import Queue
from AlmacenamientoLocalApi.AlmacenamientoLocalApi import AlmacenamientoLocalApi
from DTOS.FichaCatalogo import FichaCatalogo
from DTOS.SalaEsqueleto import SalaEsqueleto
from Gestor.PlanificadorPreCarga import PlanificadorPrecarga


class FichaFalsa:
    def __init__(self, id):
        self.id = id


def _id_ficha(i):
    return f"ficha_{i:05d}"          # con ceros, para que el orden alfabético sea el numérico


def _medir(funcion, repeticiones):
    inicio = time.perf_counter()
    for _ in range(repeticiones):
        funcion()
    return (time.perf_counter() - inicio) / repeticiones


def _crear_cache_llena(n):
    cache = CacheCatalogo(tamanio_maximo=n)
    for i in range(n):
        cache.agregar(FichaFalsa(_id_ficha(i)))
    return cache


def _buscar_lineal(fichas, id_buscado):
    for i in range(len(fichas)):
        if fichas[i].id == id_buscado:
            return (True, i)
    return (False, len(fichas))


def bench_busqueda_cache():
    print("\n1. Búsqueda en caché: binaria vs lineal (microsegundos por búsqueda)")
    print(f"{'fichas':>8} {'binaria':>10} {'lineal':>10}")
    for n in (25, 100, 1000):
        cache = _crear_cache_llena(n)
        ids = [_id_ficha(i) for i in range(n)]
        pasadas = max(1, 20000 // n)

        def binaria():
            for id_ficha in ids:
                cache._buscar_posicion(id_ficha)

        def lineal():
            for id_ficha in ids:
                _buscar_lineal(cache.fichas, id_ficha)

        t_bin = _medir(binaria, pasadas) / n
        t_lin = _medir(lineal, pasadas) / n
        print(f"{n:>8} {t_bin * 1e6:>10.2f} {t_lin * 1e6:>10.2f}")


# ---------- 2. disco vs memoria ----------
def bench_disco_vs_memoria():
    print("\n2. Recuperar una ficha: disco vs memoria (microsegundos)")
    carpeta = tempfile.mkdtemp()
    try:
        n = 25
        fichas = [FichaCatalogo.desde_json({
            "id": _id_ficha(i), "clase": "enemigo", "nombre": f"Enemigo {i}",
            "vida_max": 12, "ataque": 5, "defensa": 1, "velocidad": 100,
            "comportamiento": "guardian", "suelta": []}) for i in range(n)]

        almacen = AlmacenamientoLocalApi(carpeta)
        almacen.guardar_catalogo("bench-v1", fichas)

        cache = CacheCatalogo(tamanio_maximo=n)
        for ficha in fichas:
            cache.agregar(ficha)

        t_disco = _medir(lambda: almacen.cargar_catalogo("bench-v1"), 200)
        t_memoria = _medir(lambda: cache.obtener(_id_ficha(n - 1)), 20000)
        print(f"  disco (cargar_catalogo, archivo de {n} fichas): {t_disco * 1e6:.2f}")
        print(f"  memoria (cache.obtener):                       {t_memoria * 1e6:.2f}")
        print(f"  el disco es ~{t_disco / t_memoria:.0f} veces más lento")
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


# ---------- 3. cola de uso ----------
def bench_cola_de_uso():
    print("\n3. Cola de uso: reacomodar (tu actualizar_orden) vs solo encolar")
    print(f"{'fichas':>8} {'reacomodar us':>14} {'encolar us':>12} {'tam. reacomodar':>16} {'tam. encolar':>13}")
    repeticiones = 500
    for n in (25, 100, 1000):
        cache = _crear_cache_llena(n)
        ids = [_id_ficha(i) for i in range(n)]

        c1 = [0]
        def reacomodar():
            cache.actualizar_orden(ids[c1[0] % n])
            c1[0] += 1
        t_reac = _medir(reacomodar, repeticiones)
        tam_reac = cache.orden_uso.size()

        cola = Queue()
        for id_ficha in ids:
            cola.enqueue(id_ficha)
        c2 = [0]
        def solo_encolar():
            cola.enqueue(ids[c2[0] % n])
            c2[0] += 1
        t_enc = _medir(solo_encolar, repeticiones)
        tam_enc = cola.size()

        print(f"{n:>8} {t_reac * 1e6:>14.2f} {t_enc * 1e6:>12.2f} {tam_reac:>16} {tam_enc:>13}")


# ---------- 4. solicitudes por estrategia de precarga ----------
def _crear_esqueleto_grid(ancho, alto):
    salas = []
    for fila in range(alto):
        for col in range(ancho):
            id_sala = fila * ancho + col + 1
            salidas = {}
            if fila > 0:
                salidas["N"] = {"sala": id_sala - ancho}
            if fila < alto - 1:
                salidas["S"] = {"sala": id_sala + ancho}
            if col < ancho - 1:
                salidas["E"] = {"sala": id_sala + 1}
            if col > 0:
                salidas["O"] = {"sala": id_sala - 1}
            salas.append(SalaEsqueleto.desde_json(
                {"id": id_sala, "nombre": f"Sala {id_sala}", "salidas": salidas}))
    return salas


def _buscar(esqueleto, id_sala):
    for sala in esqueleto:
        if sala.id == id_sala:
            return sala
    return None


def _orden_de_visita(esqueleto, inicio):
    visitadas = []
    pila = [inicio]
    while pila:
        actual = pila.pop()
        if actual in visitadas:
            continue
        visitadas.append(actual)
        sala = _buscar(esqueleto, actual)
        for direccion in ("O", "E", "S", "N"):     # al revés, para que N salga primero
            if direccion in sala.salidas:
                destino = sala.salidas[direccion].sala_destino
                if destino not in visitadas:
                    pila.append(destino)
    return visitadas


def _contar_solicitudes(esqueleto, orden, limite):
    planificador = PlanificadorPrecarga(esqueleto, limite)
    cargadas = []
    solicitudes = 0
    for id_sala in orden:
        if id_sala not in cargadas:
            cargadas.extend(planificador.planificar(id_sala, cargadas))
            solicitudes += 1
    return solicitudes


def bench_precarga():
    print("\n4. Solicitudes de contenido para recorrer toda la cripta")
    estrategias = ((1, "sala por sala"), (5, "sala + vecinas (lote 5)"), (10, "lote de 10"))
    for ancho, alto in ((4, 5), (10, 10)):
        esqueleto = _crear_esqueleto_grid(ancho, alto)
        orden = _orden_de_visita(esqueleto, 1)
        print(f"  Mapa de {ancho * alto} salas:")
        for limite, nombre in estrategias:
            print(f"    {nombre:<26} {_contar_solicitudes(esqueleto, orden, limite):>4} solicitudes")


def ejecutar_bench():
    print("=== BENCH módulo B ===")
    for prueba in (bench_busqueda_cache, bench_disco_vs_memoria, bench_cola_de_uso, bench_precarga):
        try:
            prueba()
        except Exception as e:
            print(f"  [{prueba.__name__}] falló: {e}")


if __name__ == "__main__":
    ejecutar_bench()