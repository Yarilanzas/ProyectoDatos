# evidencia de rendimiento S5.2: ciclo completo de eventos entre dos decisiones del jugador < 20 ms
# reutiliza la medicion de persona A (bench_motor.bench_ciclo_real): motor real, sin red ni vista,
# con todos los enemigos activos actuando. Guarda el resultado en un archivo, igual que los otros bench.

import platform

from tests.bench_motor import bench_ciclo_real

LIMITE_MS = 20
ENEMIGOS = [10, 50, 100, 300, 500]  # 10-100: tamaño normal de una cripta; 300-500: prueba de estres
CICLOS = 100                        # decisiones del jugador medidas por tamaño
ARCHIVO_RESULTADOS = "resultados_bench_ciclo.txt"


def correr_bench():
    filas = bench_ciclo_real(ENEMIGOS, CICLOS)

    lineas = [
        f"-Ciclo completo entre dos decisiones del jugador (S5.2, limite {LIMITE_MS} ms)-",
        f"equipo: {platform.platform()} | {platform.processor() or platform.machine()} | Python {platform.python_version()}",
        f"{CICLOS} ciclos por tamaño, sin red ni renderizado, todos los enemigos activos",
    ]

    if not filas:
        lineas.append("No se pudieron importar las clases del motor")
    for enemigos, mediana, p95, _ in filas:
        cumple = "cumple" if p95 < LIMITE_MS else "NO cumple"
        lineas.append(f"enemigos = {enemigos:4d}   mediana = {mediana:7.2f} ms   p95 = {p95:7.2f} ms   {cumple}")

    for linea in lineas:
        print(linea)

    with open(ARCHIVO_RESULTADOS, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas) + "\n")


if __name__ == "__main__":
    correr_bench()