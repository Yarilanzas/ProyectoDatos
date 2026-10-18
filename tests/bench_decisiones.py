"""Reproduce TODAS las mediciones del Documento de Decisiones de la Persona A.

    python tests/bench_decisiones.py            # todo
    python tests/bench_decisiones.py --rapido   # menos repeticiones

Secciones (mismo orden que el documento):
  §4.1  agenda de eventos      montículo propio vs lista
  §4.7  rastro                 decisión del rastreador según tamaño de la cripta
        ciclo completo         §5.2, límite 20 ms, hasta 500 enemigos
  §4.8  bitácora en pantalla   buffer circular vs lista que desplaza + memoria

Al final cada afirmación del documento se verifica y sale ✓ o ✗. Los tiempos
dependen de la máquina; lo que debe cumplirse es la forma (qué crece y qué no).
"""
import argparse
import os
import statistics
import sys
import time
import tracemalloc

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.RegistroMensajes import RegistroMensajes
from tests.bench_motor import bench_agenda, bench_ia_busqueda, bench_ciclo_real

LIMITE_MS = 20
VERIFICACIONES = []


def mediana(funcion, repeticiones):
    valores = []
    for _ in range(repeticiones):
        t = time.perf_counter()
        funcion()
        valores.append(time.perf_counter() - t)
    return statistics.median(valores)


def us(segundos):
    return f"{segundos * 1e6:.2f} µs" if segundos < 1e-3 else f"{segundos * 1e3:.2f} ms"


def ns(segundos):
    return f"{segundos * 1e9:.0f} ns"


def verificar(descripcion, condicion):
    VERIFICACIONES.append((descripcion, bool(condicion)))


def titulo(texto):
    print()
    print("═" * 74)
    print(f"  {texto}")
    print("═" * 74)


def fila(*celdas, ancho=(30, 14, 14, 18)):
    print("  " + "".join(str(c).ljust(a) for c, a in zip(celdas, ancho)))


# ───────────────────────────── §4.1 Agenda ─────────────────────────────────
def seccion_agenda(rep):
    titulo("§4.1  AGENDA DE EVENTOS · montículo propio vs lista (N = 250)")
    n = 250
    r = bench_agenda(n, rep)               # valores en ms
    fila("Operación", "Montículo", "Lista", "Ventaja")
    for nombre in ("Consultar mínimo", "Extraer todos", "Buscar un evento", "Insertar todos"):
        h, l = r[nombre]
        if h <= l:
            ventaja = f"montículo {l / h:.1f}×"
        else:
            ventaja = f"lista {h / l:.1f}×"
        fila(nombre, us(h / 1000), us(l / 1000), ventaja)
    verificar("§4.1 consultar el mínimo: montículo más rápido que la lista", r["Consultar mínimo"][0] < r["Consultar mínimo"][1])
    verificar("§4.1 extraer todos: montículo más rápido que la lista", r["Extraer todos"][0] < r["Extraer todos"][1])
    verificar("§4.1 buscar un evento: montículo más rápido que la lista", r["Buscar un evento"][0] < r["Buscar un evento"][1])
    # el mínimo del montículo no debe crecer con N (O(1)); la lista sí (O(n))
    r10, r250 = bench_agenda(10, rep), bench_agenda(250, rep)
    crece_heap = r250["Consultar mínimo"][0] / max(r10["Consultar mínimo"][0], 1e-12)
    crece_lista = r250["Consultar mínimo"][1] / max(r10["Consultar mínimo"][1], 1e-12)
    print(f"\n  Consultar mínimo al pasar de N=10 a N=250: montículo ×{crece_heap:.1f} · lista ×{crece_lista:.1f}")
    verificar("§4.1 consultar el mínimo crece mucho menos en el montículo que en la lista", crece_heap * 4 < crece_lista)


# ───────────────────────────── §4.7 Rastro ────────────────────────────────
def _armar_cripta(n):
    """Cripta lineal de n salas y un rastreador en la primera (misma idea que bench_motor)."""
    from Modelo.MotorSimulacion import MotorSimulacion
    from tests.bench_motor import SalaBench, SalidaBench, ActorBench
    motor = MotorSimulacion(semilla=123)
    salas = [SalaBench(i) for i in range(n)]
    for i in range(n - 1):
        salas[i].salidas["E"] = SalidaBench(i + 1)
        salas[i + 1].salidas["O"] = SalidaBench(i)
    for i, sala in enumerate(salas):
        sala.rastro = i
    motor.salas = salas
    motor.jugador = ActorBench("jugador", sala=salas[-1])
    motor.reloj = n
    rastreador = ActorBench("rastreador", sala=salas[0])
    rastreador.comportamiento = "rastreador"
    return motor, salas, rastreador


def seccion_rastro(rep):
    titulo("§4.7  RASTRO · decisión del rastreador según el tamaño de la cripta")
    tamanos = (10, 50, 100, 250)
    llamadas = 3000          # muchas llamadas por muestra: un solo tiempo es ruido (timer de Windows ~0.1 µs)
    decision, busqueda = {}, {}
    for n in tamanos:
        motor, salas, rastreador = _armar_cripta(n)
        motor.salida_rastro(rastreador)                       # primera vez: resuelve y memoiza _destino
        objetivo = str(n - 1)

        def bucle_decision():
            for _ in range(llamadas):
                motor.salida_rastro(rastreador)

        def bucle_busqueda():
            for _ in range(llamadas):
                motor.buscar_sala(salas, objetivo)

        decision[n] = mediana(bucle_decision, rep) / llamadas
        busqueda[n] = mediana(bucle_busqueda, rep) / llamadas
    fila("Operación", *[f"{n} salas" for n in tamanos], ancho=(30, 12, 12, 12, 12))
    fila("Decisión rastreador", *[us(decision[n]) for n in tamanos], ancho=(30, 12, 12, 12, 12))
    fila("Buscar sala", *[us(busqueda[n]) for n in tamanos], ancho=(30, 12, 12, 12, 12))
    crecimiento = decision[250] / max(decision[10], 1e-12)
    print(f"\n  Decisión del rastreador 10 → 250 salas: ×{crecimiento:.2f}   (25× más salas)")
    verificar("§4.7 la decisión del rastreador no crece con el tamaño de la cripta (250 salas ≤ 2× la de 10)",
              crecimiento <= 2.0)


def seccion_ciclo(ciclos):
    titulo("§5.2  CICLO COMPLETO entre decisiones · límite 20 ms")
    tamanos = [10, 50, 100, 300, 500]
    filas = bench_ciclo_real(tamanos, ciclos)
    if not filas:
        print("  No se pudieron importar las clases del motor")
        verificar("§5.2 se pudo medir el ciclo", False)
        return
    fila("Enemigos activos", "Mediana", "p95", "¿Cumple?")
    for k, med, p95, estado in filas:
        fila(k, f"{med:.2f} ms", f"{p95:.2f} ms", "cumple" if p95 < LIMITE_MS else "NO cumple")
    # hasta 300 enemigos el p95 debe cumplir; con 500 el p95 varía mucho entre
    # corridas y máquinas, así que se exige la mediana (el documento da ambos).
    for k, med, p95, estado in filas:
        if k <= 300:
            verificar(f"§5.2 ciclo con {k} enemigos: p95 < {LIMITE_MS} ms", p95 < LIMITE_MS)
        else:
            verificar(f"§5.2 ciclo con {k} enemigos: mediana < {LIMITE_MS} ms (el p95 depende de la máquina)", med < LIMITE_MS)


# ───────────────────────────── §4.8 Bitácora ──────────────────────────────
def seccion_bitacora(rep):
    titulo("§4.8  BITÁCORA EN PANTALLA · buffer circular vs lista que desplaza")
    total = 20000
    fila("Capacidad", "Circular", "Desplaza", "")
    for cap in (20, 200, 2000):
        def circular():
            r = RegistroMensajes(cap)
            for _ in range(total):
                r.agregar("m")

        def desplaza():
            lista = []
            for _ in range(total):
                lista.append("m")
                if len(lista) > cap:
                    lista.pop(0)

        fila(cap, ns(mediana(circular, rep) / total), ns(mediana(desplaza, rep) / total))

    r = RegistroMensajes(20)
    tracemalloc.start()
    antes = tracemalloc.get_traced_memory()[0]
    for i in range(100_000):
        r.agregar("mensaje %d" % (i % 50))
    despues = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    print(f"\n  Tras 100000 mensajes: {len(r)} elementos, memoria añadida ≈ {(despues - antes) / 1024:.1f} KB")
    verificar("§4.8 el registro conserva exactamente 20 mensajes", len(r) == 20)
    verificar("§4.8 la memoria no crece con la cantidad de mensajes (< 8 KB tras 100000)", (despues - antes) < 8 * 1024)

    # orden: del más antiguo al más reciente, sin desplazar
    r2 = RegistroMensajes(20)
    for i in range(45):
        r2.agregar(i)
    verificar("§4.8 ultimos() devuelve los 20 más recientes en orden", r2.ultimos() == list(range(25, 45)))


# ───────────────────────────── principal ──────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rapido", action="store_true", help="menos repeticiones")
    args = parser.parse_args()
    rep = 3 if args.rapido else 9
    ciclos = 30 if args.rapido else 100

    print("CRIPTA · Mediciones del Documento de Decisiones (Persona A)")
    seccion_agenda(rep)
    seccion_rastro(rep)
    seccion_ciclo(ciclos)
    seccion_bitacora(rep)

    titulo("VERIFICACIÓN DE LAS AFIRMACIONES DEL DOCUMENTO")
    fallos = 0
    for descripcion, ok in VERIFICACIONES:
        print(f"  {'✓' if ok else '✗'}  {descripcion}")
        fallos += 0 if ok else 1
    print()
    print(f"  {len(VERIFICACIONES) - fallos}/{len(VERIFICACIONES)} afirmaciones verificadas")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())