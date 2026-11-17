"""M8 «después» con la carga nueva (spec 003, T069): bench_agenda de tests/bench_motor.py con tiempos que siguen el
intervalo del motor por costo, frente a la carga antigua (tiempos consecutivos), las dos en la misma corrida.

    python tests/bench_agenda_costos.py . "Intel(R) Core(TM) i5-7300U CPU @ 2.60GHz" >> resultados_bench_agenda_despues.txt

Agrega con >> al final del «después»; nunca redirigir sobre resultados_bench_agenda_antes.txt.

Carga nueva: ACTORES actores, cada uno con su reloj y una velocidad sorteada en VELOCIDADES; el evento i es la
siguiente acción del actor i % ACTORES, en reloj + max(1, costo * 100 // velocidad) (la fórmula de
MotorSimulacion.calcu_inter), con costo sorteado en COSTOS. Con un solo actor los tiempos saldrían en orden creciente,
igual que la carga antigua; con varios llegan intercalados, como en la agenda del motor. Semilla fija.

Las cuatro operaciones son las de bench_motor.bench_agenda, copiadas sin cambios salvo el tiempo de cada evento: así
la única diferencia entre las dos cargas es la secuencia de tiempos.
"""
import platform
import random
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from tests import bench_motor as bm  # noqa: E402

SIZES = [10, 50, 100, 250]
REPEATS = 5
SEMILLA = 2026
ACTORES = 10
COSTOS = tuple(range(50, 301, 10))
VELOCIDADES = (50, 100, 200)
LIMITE_RAZON = 1.5
CPU = sys.argv[2] if len(sys.argv) > 2 else platform.processor()
OPERACIONES = ("Insertar todos", "Consultar mínimo", "Extraer todos", "Buscar un evento")


def intervalo(costo, velocidad):
    """Igual que MotorSimulacion.calcu_inter."""
    return max(1, costo * 100 // velocidad)


def tiempos_por_costo(n, semilla=SEMILLA):
    """n tiempos: el evento i es la siguiente acción del actor i % ACTORES (reloj propio + intervalo por costo)."""
    azar = random.Random(semilla)
    velocidades = [azar.choice(VELOCIDADES) for _ in range(ACTORES)]
    relojes = [0] * ACTORES
    tiempos = []
    for i in range(n):
        actor = i % ACTORES
        relojes[actor] += intervalo(azar.choice(COSTOS), velocidades[actor])
        tiempos.append(relojes[actor])
    return tiempos


def tiempos_consecutivos(n):
    """Carga antigua de bench_agenda: Evento(i, i, ...)."""
    return list(range(n))


def bench_agenda_con(tiempos, repeticiones):
    """bench_motor.bench_agenda con Evento(tiempos[i], i, ...) en lugar de Evento(i, i, ...)."""
    n = len(tiempos)

    def insertar_agenda():
        agenda = bm.AgendaEventos()
        actor = bm.ActorBench("agenda")
        for i in range(n):
            agenda.agregar(bm.Evento(tiempos[i], i, "BENCH", actor))
        return agenda

    def insertar_lista():
        actor = bm.ActorBench("agenda")
        return [bm.Evento(tiempos[i], i, "BENCH", actor) for i in range(n)]

    t_ah = bm.medir_ms(insertar_agenda, repeticiones)
    t_li = bm.medir_ms(insertar_lista, repeticiones)
    agenda, eventos = insertar_agenda(), insertar_lista()
    t_mh = bm.medir_us(agenda.siguiente, repeticiones)
    t_ml = bm.medir_us(lambda: min((e for e in eventos if not e.cancelado), default=None), repeticiones)

    def extraer_agenda():
        a = insertar_agenda()
        while a.extraer() is not None:
            pass

    def extraer_lista():
        l = insertar_lista()
        while l:
            l.remove(min(l))

    t_eh = bm.medir_ms(extraer_agenda, repeticiones)
    t_el = bm.medir_ms(extraer_lista, repeticiones)
    objetivo_a, objetivo_l = agenda.heap[n // 2], eventos[n // 2]
    t_bh = bm.medir_us(lambda: agenda.contiene(objetivo_a), repeticiones)
    t_bl = bm.medir_us(lambda: any(e is objetivo_l for e in eventos), repeticiones)

    return {
        "Insertar todos": (t_ah, t_li),
        "Consultar mínimo": (t_mh / 1000, t_ml / 1000),
        "Extraer todos": (t_eh, t_el),
        "Buscar un evento": (t_bh / 1000, t_bl / 1000),
    }


def tabla_carga(nombre, resultados):
    """Misma tabla que tests/bench_agenda_solo.py."""
    bm.titulo(f"AGENDA DE EVENTOS · {nombre}", "heap propio vs lista · menor es mejor")
    filas = []
    for op in OPERACIONES:
        heap = [bm.fmt_t(r[op][0]) for r in resultados]
        lista = [bm.fmt_t(r[op][1]) for r in resultados]
        razon = resultados[-1][op][1] / resultados[-1][op][0] if resultados[-1][op][0] else 1
        ventaja = f"heap {razon:.1f}×" if razon >= 1 else f"lista {1 / razon:.1f}×"
        filas.append([op, "heap", *heap, ventaja])
        filas.append(["", "lista", *lista, ""])
    bm.tabla(["Operación", "", *[f"N={n}" for n in SIZES], f"ventaja @N={SIZES[-1]}"], filas)


def main():
    antigua, nueva = [], []
    for n in SIZES:  # las dos cargas de cada N una tras otra, en la misma corrida
        antigua.append(bench_agenda_con(tiempos_consecutivos(n), REPEATS))
        nueva.append(bench_agenda_con(tiempos_por_costo(n), REPEATS))

    muestra = tiempos_por_costo(SIZES[-1])
    ordenados = sorted(muestra)
    empates = sum(1 for i in range(1, len(ordenados)) if ordenados[i] == ordenados[i - 1])
    desordenes = sum(1 for i in range(1, len(muestra)) if muestra[i] < muestra[i - 1])

    print()
    print("═" * 74)
    print("M8 «después» con la carga nueva (T069) · tests/bench_agenda_costos.py · misma corrida para las dos cargas")
    print(f"Equipo: {platform.system()} {platform.release()} (build {platform.version()}), {platform.machine()}")
    print(f"CPU: {CPU}")
    print(f"Python: {sys.version.split()[0]} ({platform.python_implementation()})")
    print(f"Parámetros: N = {', '.join(map(str, SIZES))} · {REPEATS} repeticiones · mediana")
    print(f"Carga nueva: {ACTORES} actores con reloj propio; evento i = siguiente acción del actor i % {ACTORES}, en "
          f"reloj + max(1, costo * 100 // velocidad) (MotorSimulacion.calcu_inter); costo en {COSTOS[0]}..{COSTOS[-1]} "
          f"de {COSTOS[1] - COSTOS[0]} en {COSTOS[1] - COSTOS[0]}, velocidad en {VELOCIDADES} por actor; "
          f"random.Random({SEMILLA})")
    print(f"Con N={SIZES[-1]}: tiempos de {ordenados[0]} a {ordenados[-1]}, {empates} tiempos repetidos, "
          f"{desordenes} de {len(muestra) - 1} eventos llegan con tiempo menor que el anterior")
    print("Carga antigua: Evento(i, i, ...), tiempos 0..N-1 consecutivos (la de bench_agenda y de T002)")
    print("Nota: la comparación válida de esta sección es entre las dos cargas, medidas en esta misma corrida y en la "
          "misma máquina; la comparación «antes/después» de arriba (T002 frente a T069, carga antigua en corridas "
          "distintas) solo muestra variación del equipo entre corridas")

    tabla_carga("carga antigua (tiempos consecutivos)", antigua)
    tabla_carga("carga nueva (intervalos por costo)", nueva)

    bm.titulo("COMPARACIÓN carga nueva / carga antigua", "misma corrida · > 1: la carga nueva es más lenta")
    filas, razones = [], []
    for op in OPERACIONES:
        for indice, estructura in ((0, "heap"), (1, "lista")):
            for k in range(len(SIZES)):
                a, b = antigua[k][op][indice], nueva[k][op][indice]
                razon = b / a
                razones.append((razon, op, estructura, SIZES[k]))
                filas.append([op, estructura, f"N={SIZES[k]}", bm.fmt_t(a), bm.fmt_t(b), f"{razon:.2f}"])
    bm.tabla(["Operación", "Estructura", "N", "Antigua", "Nueva", "Nueva/Antigua"], filas)

    mayor = max(razones)
    encima = [r for r in razones if r[0] > LIMITE_RAZON]
    print()
    print(f"razón máxima: {mayor[0]:.2f} ({mayor[1]}, {mayor[2]}, N={mayor[3]})")
    if encima:
        print(f"razones > {LIMITE_RAZON}: {len(encima)} de {len(razones)}: "
              + "; ".join(f"{op} {est} N={n} = {r:.2f}" for r, op, est, n in sorted(encima, reverse=True)))
    else:
        print(f"razones > {LIMITE_RAZON}: ninguna de {len(razones)}")


if __name__ == "__main__":
    main()
