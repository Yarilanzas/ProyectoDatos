"""Corre solo bench_agenda de tests/bench_motor.py (misma tabla que main(), parámetros por defecto)."""
import platform
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from tests import bench_motor as bm  # noqa: E402

SIZES = [10, 50, 100, 250]
REPEATS = 5
CPU = sys.argv[2] if len(sys.argv) > 2 else platform.processor()

print("M8 «antes» (T002) · bench_agenda de tests/bench_motor.py · código sin cambios del motor")
print(f"Equipo: {platform.system()} {platform.release()} (build {platform.version()}), {platform.machine()}")
print(f"CPU: {CPU}")
print(f"Python: {sys.version.split()[0]} ({platform.python_implementation()})")
print(f"Parámetros: N = {', '.join(map(str, SIZES))} · {REPEATS} repeticiones · mediana")

agenda = [bm.bench_agenda(n, REPEATS) for n in SIZES]
columnas = [f"N={n}" for n in SIZES]
bm.titulo("AGENDA DE EVENTOS", "heap propio vs lista · menor es mejor")
filas = []
for op in agenda[0]:
    heap = [bm.fmt_t(r[op][0]) for r in agenda]
    lista = [bm.fmt_t(r[op][1]) for r in agenda]
    razon = agenda[-1][op][1] / agenda[-1][op][0] if agenda[-1][op][0] else 1
    ventaja = f"heap {razon:.1f}×" if razon >= 1 else f"lista {1 / razon:.1f}×"
    filas.append([op, "heap", *heap, ventaja])
    filas.append(["", "lista", *lista, ""])
bm.tabla(["Operación", "", *columnas, f"ventaja @N={SIZES[-1]}"], filas)
