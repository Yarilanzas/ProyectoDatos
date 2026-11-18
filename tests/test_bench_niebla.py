# Pruebas de la medición de la Fase 6: base (T100) y M1 a M6 (T101 a T106). T108 agrega la prueba rápida de M1 a M6.
# Atiende: SC-006, PR-15, Principio VIII. Sin red y sin vista.

import contextlib
import io
import os
import platform
import re
import sys
import tempfile
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from unittest import mock
import socket

from Modelo.retroceso import Historial
from tests import bench_niebla
from tests.bench_niebla import (VARIANTES_M3, ListaLineal, ListaOrdenada, clave_puerta, encabezado, escribir_resultados,
                                estado_de, lineas_base_m1, mediana, medir_m1, medir_m2, medir_m3, medir_ms,
                                preparar_m1, preparar_m2, preparar_m3, revelar_en_lista,
                                deshacer_en_lista)
from Modelo.Conocimiento import DESCONOCIDA, SIN_OBSERVAR
from tests.mapas_sinteticos import grilla
from Vista.VistaConsola import VistaConsola


def _archivos_py():
    for carpeta, subcarpetas, archivos in os.walk(RAIZ):
        subcarpetas[:] = [s for s in subcarpetas if s not in (".git", ".venv", "venv", "__pycache__", ".idea")]
        for nombre in archivos:
            if nombre.endswith(".py"):
                yield os.path.join(carpeta, nombre)


class RelojFalso:
    # Devuelve en orden los instantes (en ns) que se le dan.
    def __init__(self, instantes):
        self._instantes = list(instantes)
        self._siguiente = 0

    def __call__(self):
        valor = self._instantes[self._siguiente]
        self._siguiente += 1
        return valor


class TestMediana(unittest.TestCase):
    def test_pr15_mediana_impar(self):
        self.assertEqual(mediana([3, 1, 2]), 2)
        self.assertEqual(mediana([5]), 5)
        self.assertEqual(mediana([9, 1, 7, 3, 5]), 5)

    def test_pr15_mediana_par_promedia_los_dos_centrales(self):
        self.assertEqual(mediana([4, 1, 3, 2]), 2.5)
        self.assertEqual(mediana([10.0, 2.0]), 6.0)

    def test_pr15_mediana_con_repetidos_y_no_cambia_la_entrada(self):
        valores = [2, 2, 9, 1, 2]
        self.assertEqual(mediana(valores), 2)
        self.assertEqual(valores, [2, 2, 9, 1, 2])

    def test_pr15_mediana_vacia_es_error(self):
        with self.assertRaises(ValueError):
            mediana([])

    def test_pr15_medir_ms_es_la_mediana_de_las_repeticiones(self):
        # tres repeticiones de 4 ms, 1 ms y 2 ms: la mediana es 2 ms
        reloj = RelojFalso([0, 4_000_000, 10_000_000, 11_000_000, 20_000_000, 22_000_000])
        llamadas = []
        resultado = medir_ms(lambda: llamadas.append(1), repeticiones=3, reloj=reloj)
        self.assertEqual(len(llamadas), 3)
        self.assertEqual(resultado, 2.0)


class TestLimite(unittest.TestCase):
    def test_pr15_limite_paso_ir_a_es_5_ms(self):
        self.assertEqual(bench_niebla.LIMITE_PASO_IR_A_MS, 5)

    def test_pr15_limite_se_escribe_una_sola_vez_y_cita_6_1(self):
        asignacion = re.compile(r"^\s*LIMITE_PASO_IR_A_MS\s*=", re.MULTILINE)
        lugares = []
        for ruta in _archivos_py():
            with open(ruta, encoding="utf-8") as archivo:
                codigo = archivo.read()
            for _ in asignacion.finditer(codigo):
                lugares.append(os.path.relpath(ruta, RAIZ))
        self.assertEqual(lugares, [os.path.join("tests", "bench_niebla.py")])

        with open(bench_niebla.__file__, encoding="utf-8") as archivo:
            codigo = archivo.read()
        linea = codigo[asignacion.search(codigo).start():].split("\n", 1)[0]
        comentario_previo = codigo[:asignacion.search(codigo).start()].rsplit("\n\n", 1)[-1]
        texto = comentario_previo + linea
        self.assertIn("§6.1", texto)
        self.assertIn("enmienda", texto)


class TestResultados(unittest.TestCase):
    def test_pr15_encabezado_tiene_equipo_version_de_python_y_aviso_provisional(self):
        texto = "\n".join(encabezado())
        self.assertIn(platform.python_version(), texto)
        self.assertIn(platform.platform(), texto)
        self.assertIn("provisional", texto)

    def test_pr15_escribe_resultados_con_encabezado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, bench_niebla.ARCHIVO_RESULTADOS)
            with contextlib.redirect_stdout(io.StringIO()):
                escribir_resultados(["M0 fila de prueba"], ruta)
            self.assertTrue(os.path.exists(ruta))
            with open(ruta, encoding="utf-8") as archivo:
                texto = archivo.read()
        self.assertIn(platform.python_version(), texto)
        self.assertIn("M0 fila de prueba", texto)
        self.assertTrue(texto.endswith("\n"))

    def test_pr15_nombre_del_archivo(self):
        self.assertEqual(bench_niebla.ARCHIVO_RESULTADOS, "resultados_bench_niebla.txt")


class TestPrincipioI(unittest.TestCase):
    def test_pr15_sin_ordenamientos_ni_estadisticas_de_biblioteca(self):
        for modulo in ("bench_niebla.py", "mapas_sinteticos.py"):
            with open(os.path.join(RAIZ, "tests", modulo), encoding="utf-8") as archivo:
                codigo = archivo.read()
            with self.subTest(modulo=modulo):
                for marca in ("sorted(", ".sort(", "statistics", "heapq", "bisect", "collections"):
                    self.assertNotIn(marca, codigo)


# M1 a M3 (T101 a T103). Solo forma y corrección: ninguna prueba afirma tiempos (Principio VIII).

def _buscar_fila(prueba, filas, medicion, variante, **parametros):
    halladas = []
    for fila in filas:
        if fila.medicion != medicion or fila.variante != variante:
            continue
        if all(fila.valor(nombre) == valor for nombre, valor in parametros.items()):
            halladas.append(fila)
    prueba.assertEqual(len(halladas), 1, f"{medicion} {variante} {parametros}: {len(halladas)} filas")
    fila = halladas[0]
    prueba.assertIsInstance(fila.ms, float)
    prueba.assertGreaterEqual(fila.ms, 0.0)
    prueba.assertTrue(fila.hipotesis)
    return fila


def _distintos(valores):
    vistos = []
    for valor in valores:
        if valor not in vistos:
            vistos.append(valor)
    return len(vistos)


class TestFormaDeLasMediciones(unittest.TestCase):
    def test_pr15_tamanos_por_defecto_de_research_r9(self):
        self.assertEqual(bench_niebla.TAMANOS_M1, (20, 200, 2000, 20000))
        self.assertEqual(bench_niebla.TAMANOS_M2, (10, 100, 1000, 10000))
        self.assertGreaterEqual(len(bench_niebla.TAMANOS_M3_N), 3)
        self.assertGreaterEqual(len(bench_niebla.VECINAS_M3), 3)

    def test_fr001_fr005_pr15_m1_una_fila_por_tamano_objeto_y_variante(self):
        filas = medir_m1((20, 40), repeticiones=1, consultas=5)
        self.assertEqual(len(filas), 12)
        for n in (20, 40):
            for objeto in ("sala", "puerta"):
                for variante in ("arreglos", "binaria", "lineal"):
                    _buscar_fila(self, filas, "M1", f"{objeto}/{variante}", n=n)

    def test_fr003_fr009_pr15_m2_una_fila_por_k_y_variante(self):
        filas = medir_m2((10, 20), repeticiones=1)
        self.assertEqual(len(filas), 4)
        for k in (10, 20):
            for variante in ("arreglos", "lista ordenada"):
                fila = _buscar_fila(self, filas, "M2", variante, k=k)
                self.assertGreater(fila.valor("r"), 0)

    def test_fr014_pr15_m3_una_fila_por_variante_n_y_vecinas_y_r_crece_con_las_vecinas(self):
        filas = medir_m3((50, 80), (2, 4), repeticiones=1)
        self.assertEqual(len(filas), 12)
        for variante in ("lote", "cierres", "copia"):
            for n in (50, 80):
                r_por_vecinas = []
                for vecinas in (2, 4):
                    fila = _buscar_fila(self, filas, "M3", variante, n=n, vecinas=vecinas)
                    r_por_vecinas.append(fila.valor("r"))
                self.assertLess(r_por_vecinas[0], r_por_vecinas[1])

    def test_pr15_texto_de_cada_fila_dice_parametros_tiempo_e_hipotesis(self):
        filas = medir_m1((20,), 1, 3) + medir_m2((10,), 1) + medir_m3((50,), (2,), 1)
        self.assertEqual(len(filas), 6 + 2 + 3)
        for fila in filas:
            texto = fila.texto()
            self.assertIn(fila.medicion, texto)
            self.assertIn(fila.variante, texto)
            self.assertIn("ms", texto)
            self.assertIn("hipótesis", texto)
        self.assertIn("n=20", filas[0].texto())

    def test_pr15_m1_a_m3_corren_sin_red_ni_vista(self):
        prohibido = AssertionError("las mediciones no usan red ni vista")
        with mock.patch.object(socket.socket, "connect", side_effect=prohibido), \
                mock.patch.object(VistaConsola, "__init__", side_effect=prohibido):
            filas = medir_m1((20,), 1, 3) + medir_m2((10,), 1) + medir_m3((50,), (2,), 1)
        self.assertEqual(len(filas), 11)


class TestCorreccionDeLineasBase(unittest.TestCase):
    def test_pr15_lista_ordenada_inserta_en_orden_busca_y_quita(self):
        lista = ListaOrdenada()
        for clave in (5, 1, 9, 3, 7):
            lista.insertar(clave, clave * 10)
        self.assertEqual(lista.pares(), [(1, 10), (3, 30), (5, 50), (7, 70), (9, 90)])
        self.assertEqual(lista.buscar(7, -1), 70)
        self.assertEqual(lista.buscar(4, -1), -1)
        lista.insertar(7, 71)  # clave existente: actualiza
        self.assertEqual(lista.buscar(7, -1), 71)
        lista.quitar(1)
        lista.quitar(9)
        self.assertEqual(lista.pares(), [(3, 30), (5, 50), (7, 71)])

    def test_pr15_lista_lineal_busca_y_quita(self):
        lista = ListaLineal()
        for clave in (5, 1, 9):
            lista.insertar(clave, clave * 10)
        self.assertEqual(lista.buscar(1, -1), 10)
        self.assertEqual(lista.buscar(2, -1), -1)
        lista.quitar(1)
        self.assertEqual(lista.buscar(1, -1), -1)
        self.assertEqual(len(lista.pares()), 2)

    def test_fr001_fr005_pr15_m1_binaria_y_lineal_dan_lo_mismo_que_los_arreglos(self):
        conocimiento, salas = preparar_m1(40)
        self.assertIsNotNone(conocimiento)
        self.assertEqual(len(salas), 40)
        ordenada_salas, lineal_salas, ordenada_puertas, lineal_puertas = lineas_base_m1(conocimiento)
        self.assertIsNotNone(ordenada_salas)

        estados, recuerdos = [], []
        for sala in salas:
            esperado = conocimiento.estado(sala)
            estados.append(esperado)
            self.assertEqual(ordenada_salas.buscar(sala.id, DESCONOCIDA), esperado)
            self.assertEqual(lineal_salas.buscar(sala.id, DESCONOCIDA), esperado)
            for salida in sala.salidas.values():
                esperado = conocimiento.recuerdo(salida)
                recuerdos.append(esperado)
                self.assertEqual(ordenada_puertas.buscar(clave_puerta(salida), SIN_OBSERVAR), esperado)
                self.assertEqual(lineal_puertas.buscar(clave_puerta(salida), SIN_OBSERVAR), esperado)
        # el mapa preparado mezcla los tres estados y los tres recuerdos, para que la comparación diga algo
        self.assertEqual(_distintos(estados), 3)
        self.assertEqual(_distintos(recuerdos), 3)

    def test_fr003_fr009_pr15_m2_lista_ordenada_da_lo_mismo_que_los_arreglos(self):
        conocimiento, lote, lista = preparar_m2(10)
        self.assertIsNotNone(conocimiento)
        self.assertTrue(lote)
        self.assertGreaterEqual(len(conocimiento.reveladas), 10)
        self.assertEqual(len(lista.pares()), len(conocimiento.reveladas))

        def comparar():
            for sala in conocimiento._salas:
                self.assertEqual(lista.buscar(sala.id, DESCONOCIDA), conocimiento.estado(sala))

        comparar()
        conocimiento.aplicar(lote)
        revelar_en_lista(lista, lote, conocimiento)
        comparar()
        conocimiento.invertir(lote)
        deshacer_en_lista(lista, lote, conocimiento)
        comparar()

    def test_fr014_pr15_m3_las_tres_variantes_dejan_el_mismo_estado(self):
        self.assertEqual(tuple(nombre for nombre, _, _ in VARIANTES_M3), ("lote", "cierres", "copia"))
        despues = []
        for nombre, crear, registrar in VARIANTES_M3:
            with self.subTest(variante=nombre):
                salas, centro = preparar_m3(60, 4)
                conocimiento = crear(salas)
                inicial = estado_de(conocimiento)
                historial = Historial()
                historial.abrir_intervalo()
                registrar(conocimiento, centro, historial)
                tras_registrar = estado_de(conocimiento)
                self.assertNotEqual(tras_registrar, inicial)
                despues.append(tras_registrar)
                self.assertTrue(historial.deshacer_ultimo())
                self.assertEqual(estado_de(conocimiento), inicial)
        self.assertEqual(despues[0], despues[1])
        self.assertEqual(despues[0], despues[2])


# M4 a M6 (T104 a T106). Solo forma y corrección: ninguna prueba afirma tiempos (Principio VIII).

def _filas_m4(**opciones):
    return bench_niebla.medir_m4((25, 100), repeticiones=1, **opciones)


class TestM4(unittest.TestCase):
    def test_fr024_pr15_m4_tamanos_y_topologias_de_research_r9(self):
        self.assertEqual(bench_niebla.TAMANOS_M4, (25, 100, 400, 2500))
        self.assertEqual(tuple(nombre for nombre, _ in bench_niebla.TOPOLOGIAS_M4), ("grilla", "cadena"))

    def test_fr024_fr026_pr15_m4_una_fila_por_tamano_topologia_y_variante(self):
        filas = _filas_m4()
        self.assertEqual(len(filas), 8)
        for topologia in ("grilla", "cadena"):
            for v in (25, 100):
                paso = _buscar_fila(self, filas, "M4", f"{topologia}/paso", V=v)
                viaje = _buscar_fila(self, filas, "M4", f"{topologia}/viaje", V=v)
                self.assertGreater(viaje.valor("pasos"), 0)
                self.assertEqual(paso.valor("pasos"), 1)
        for v in (25, 100):
            fila = _buscar_fila(self, filas, "M4", "cadena/viaje", V=v)
            self.assertEqual(fila.valor("pasos"), v - 1)

    def test_sc007_pr15_m4_provisional_y_veredicto_contra_la_constante(self):
        for fila in _filas_m4():
            with self.subTest(fila=fila.texto()):
                self.assertTrue(fila.provisional)
                self.assertIn("PROVISIONAL", fila.texto())
                self.assertIn("prueba de estrés", fila.texto())
                self.assertNotIn("hasta T110", fila.texto())
                self.assertIn(fila.veredicto, ("cumple", "no cumple"))
                self.assertIn(fila.veredicto, fila.texto())
                por_paso = fila.ms / fila.valor("pasos")
                esperado = "cumple" if por_paso <= bench_niebla.LIMITE_PASO_IR_A_MS else "no cumple"
                self.assertEqual(fila.veredicto, esperado)

    def test_sc007_pr15_m4_veredicto_usa_la_constante(self):
        limite = bench_niebla.LIMITE_PASO_IR_A_MS
        self.assertEqual(bench_niebla.veredicto_paso(limite), "cumple")
        self.assertEqual(bench_niebla.veredicto_paso(limite + 0.001), "no cumple")
        with mock.patch.object(bench_niebla, "LIMITE_PASO_IR_A_MS", 1000):
            self.assertEqual(bench_niebla.veredicto_paso(limite + 0.001), "cumple")

    def test_fr024_pr15_m4_mide_primer_paso_real_y_no_un_buscador_de_prueba(self):
        from Modelo import rutas_ir_a
        self.assertIs(bench_niebla.primer_paso, rutas_ir_a.primer_paso)
        with mock.patch.object(rutas_ir_a, "primer_paso_busqueda",
                               wraps=rutas_ir_a.primer_paso_busqueda) as real:
            bench_niebla.medir_m4((25,), repeticiones=1)
        self.assertGreater(real.call_count, 0)

    def test_fr024_fr026_pr15_m4_el_viaje_llega_al_destino_por_rutas_minimas(self):
        for nombre, generar in bench_niebla.TOPOLOGIAS_M4:
            with self.subTest(topologia=nombre):
                grafo, origen, destino = bench_niebla.preparar_m4(generar, 25)
                self.assertIsNot(origen, destino)
                pasos = bench_niebla.viaje_m4(grafo, origen, destino)
                self.assertIs(pasos[-1].destino, destino)
                # el costo total que anuncia cada paso baja en cada paso del viaje
                for indice in range(len(pasos) - 1):
                    self.assertGreater(pasos[indice].costo_total, pasos[indice + 1].costo_total)
                self.assertEqual(bench_niebla.primer_paso(grafo, origen, destino), pasos[0])

    def test_fr024_pr15_m4_acepta_un_espacio_reutilizado_con_el_mismo_resultado(self):
        from Modelo.BusquedaRuta import EspacioBusqueda
        filas = bench_niebla.medir_m4((25,), repeticiones=1, espacio=EspacioBusqueda)
        self.assertEqual(len(filas), 4)
        for fila in filas:
            self.assertEqual(fila.valor("espacio"), "reutilizado")
        grafo, origen, destino = bench_niebla.preparar_m4(grilla, 25)
        sin = bench_niebla.viaje_m4(grafo, origen, destino)
        con = bench_niebla.viaje_m4(grafo, origen, destino, EspacioBusqueda(grafo.cantidad_salas))
        self.assertTrue(sin)
        self.assertEqual(sin, con)


class TestM5(unittest.TestCase):
    def test_fr015_pr15_m5_tamanos_de_research_r9(self):
        self.assertEqual(bench_niebla.TAMANOS_M5, (20, 200, 2000))

    def test_fr015_pr15_m5_una_fila_por_k_formato_y_operacion(self):
        filas = bench_niebla.medir_m5((20, 40), repeticiones=1)
        self.assertEqual(len(filas), 8)
        for k in (20, 40):
            for formato in ("binario", "json"):
                guardar = _buscar_fila(self, filas, "M5", f"{formato}/guardar", k=k)
                cargar = _buscar_fila(self, filas, "M5", f"{formato}/cargar", k=k)
                self.assertGreater(guardar.valor("bytes"), 0)
                self.assertEqual(guardar.valor("bytes"), cargar.valor("bytes"))
                self.assertGreaterEqual(cargar.valor("leidos"), cargar.valor("bytes"))

    def test_fr015_pr15_m5_binario_y_json_dan_la_misma_informacion(self):
        motor = bench_niebla.preparar_m5(20)
        self.assertIsNotNone(motor.conocimiento)
        with tempfile.TemporaryDirectory() as carpeta:
            resultado = bench_niebla.ida_y_vuelta_m5(motor, carpeta)
        original, desde_binario, desde_json, leidos_binario, leidos_json = resultado
        self.assertEqual(len(original.exploradas), 20)
        self.assertTrue(original.recuerdos)
        self.assertTrue(original.puertas_reales)
        self.assertEqual(desde_binario.to_dict(), original.to_dict())
        self.assertEqual(desde_json.to_dict(), original.to_dict())
        self.assertGreaterEqual(leidos_binario, len(original.to_bytes()))
        self.assertGreater(leidos_json, 0)

    def test_fr015_pr15_m5_usa_las_funciones_reales_de_persistencia(self):
        from Persistencia import ArchivoPartida, ConversorPartida, ExportadorJSON
        self.assertIs(bench_niebla.registro_conocimiento_desde_motor,
                      ConversorPartida.registro_conocimiento_desde_motor)
        self.assertIs(bench_niebla.guardar_partida, ArchivoPartida.guardar_partida)
        self.assertIs(bench_niebla.LectorPartida, ArchivoPartida.LectorPartida)
        self.assertIs(bench_niebla.guardar_partida_json, ExportadorJSON.guardar_partida_json)
        self.assertIs(bench_niebla.cargar_conocimiento_json, ExportadorJSON.cargar_conocimiento_json)


class TestM6(unittest.TestCase):
    def test_sc006_pr15_percentil_95_con_merge_sort(self):
        self.assertEqual(bench_niebla.percentil([5, 1, 3], 95), 5)
        self.assertEqual(bench_niebla.percentil(list(range(20, 0, -1)), 95), 20)
        self.assertEqual(bench_niebla.percentil([4.0], 95), 4.0)
        valores = [3, 1, 2]
        bench_niebla.percentil(valores, 95)
        self.assertEqual(valores, [3, 1, 2])
        with self.assertRaises(ValueError):
            bench_niebla.percentil([], 95)

    def test_sc006_pr15_m6_reusa_bench_ciclo(self):
        from tests import bench_ciclo
        self.assertEqual(bench_niebla.ENEMIGOS_M6, tuple(bench_ciclo.ENEMIGOS))
        self.assertEqual(bench_niebla.CICLOS_M6, bench_ciclo.CICLOS)
        self.assertEqual(bench_niebla.LIMITE_CICLO_MS, bench_ciclo.LIMITE_MS)
        self.assertEqual(bench_niebla.ENEMIGOS_M6[0], 10)
        self.assertEqual(bench_niebla.ENEMIGOS_M6[-1], 500)

    def test_fr014_sc006_pr15_m6_una_fila_con_y_sin_conocimiento_por_tamano(self):
        filas = bench_niebla.medir_m6((10, 20), ciclos=3)
        self.assertEqual(len(filas), 4)
        for k in (10, 20):
            for variante in ("con conocimiento", "sin conocimiento"):
                fila = _buscar_fila(self, filas, "M6", variante, enemigos=k, ciclos=3)
                self.assertIsInstance(fila.p95, float)
                self.assertGreaterEqual(fila.p95, fila.ms)
                self.assertIn("p95", fila.texto())
                esperado = "cumple" if fila.p95 < bench_niebla.LIMITE_CICLO_MS else "no cumple"
                self.assertEqual(fila.veredicto, esperado)

    def test_fr014_sc006_pr15_m6_con_y_sin_conocimiento_es_el_mismo_ciclo(self):
        con = bench_niebla.preparar_m6(10, True)
        sin = bench_niebla.preparar_m6(10, False)
        self.assertIsNotNone(con.conocimiento)
        self.assertIsNone(sin.conocimiento)

        def foto(motor):
            return (motor.reloj, [(e.id, e.sala.id, e.vida) for e in motor.enemigos],
                    motor.jugador.sala.id, motor.jugador.vida)

        self.assertEqual(foto(con), foto(sin))
        with contextlib.redirect_stdout(io.StringIO()):
            for _ in range(5):
                bench_niebla.ciclo_m6(con)
                bench_niebla.ciclo_m6(sin)
        self.assertEqual(foto(con), foto(sin))
        self.assertGreater(con.reloj, 0)


class TestM4AM6SinRedNiVista(unittest.TestCase):
    def test_sc006_pr15_m4_a_m6_corren_sin_red_ni_vista(self):
        prohibido = AssertionError("las mediciones no usan red ni vista")
        with mock.patch.object(socket.socket, "connect", side_effect=prohibido), \
                mock.patch.object(VistaConsola, "__init__", side_effect=prohibido):
            filas = (bench_niebla.medir_m4((25,), repeticiones=1) + bench_niebla.medir_m5((20,), repeticiones=1)
                     + bench_niebla.medir_m6((10,), ciclos=2))
        self.assertEqual(len(filas), 4 + 4 + 2)
        for fila in filas:
            self.assertIsNotNone(fila.ms, fila.texto())


# T110: M4 con el mapa conocido completo de la cripta de referencia, leído al correr de las copias locales
# (`datos_locales/esqueleto_<id>.json`). Solo forma, corrección y comparación contra la constante: ningún tiempo.
# Atiende: SC-007, PR-15.

DATOS_LOCALES = os.path.join(RAIZ, "datos_locales")
NOTA_REFERENCIA = ("la mayor de las copias locales ({}, {} salas), usada como sustituta de la cripta de referencia "
                   "(HIPÓTESIS: la del enunciado, §6.1, aún no está publicada)")


def _esqueletos_locales(carpeta=DATOS_LOCALES):
    """(id, datos del archivo) de cada `esqueleto_<id>.json` de ``carpeta``, leído aquí y no copiado al código."""
    import json
    resultado = []
    for nombre in os.listdir(carpeta):
        if nombre.startswith("esqueleto_") and nombre.endswith(".json"):
            with open(os.path.join(carpeta, nombre), encoding="utf-8") as archivo:
                resultado.append((nombre[len("esqueleto_"):-len(".json")], json.load(archivo)))
    return resultado


def _mas_grande(carpeta=DATOS_LOCALES):
    elegido = None
    for id_cripta, datos in _esqueletos_locales(carpeta):
        if elegido is None or len(datos["esqueleto"]) > len(elegido[1]["esqueleto"]):
            elegido = (id_cripta, datos)
    return elegido


def _pares_json(esqueleto):
    """[(origen, destino, costo)]: todos los pares distintos con ruta por salidas abiertas, en el orden del
    esqueleto (origen y luego destino), con el costo acumulado mínimo (100 si la salida no trae costo). Cálculo
    independiente del bench: Bellman-Ford sobre el JSON, sin `Conocimiento` ni `GrafoConocido`."""
    ids = [sala["id"] for sala in esqueleto]
    aristas = []
    for sala in esqueleto:
        for salida in sala["salidas"].values():
            if not salida.get("cerrada") and salida["sala"] in ids:
                aristas.append((ids.index(sala["id"]), ids.index(salida["sala"]), salida.get("costo", 100)))
    resultado = []
    for inicio in range(len(ids)):
        dist = [None] * len(ids)
        dist[inicio] = 0
        for _ in range(len(ids) - 1):
            cambio = False
            for a, b, costo in aristas:
                if dist[a] is not None and (dist[b] is None or dist[a] + costo < dist[b]):
                    dist[b] = dist[a] + costo
                    cambio = True
            if not cambio:
                break  # ninguna distancia bajó en esta ronda: ya son las definitivas
        for indice in range(len(ids)):
            if indice != inicio and dist[indice] is not None:
                resultado.append((ids[inicio], ids[indice], dist[indice]))
    return resultado


def _origenes_con_pares(pares):
    origenes = []
    for origen, _, _ in pares:
        if origen not in origenes:
            origenes.append(origen)
    return len(origenes)


def _instantanea(carpeta):
    """Nombre y bytes de cada archivo de ``carpeta``, en el orden de os.listdir."""
    resultado = []
    for nombre in os.listdir(carpeta):
        ruta = os.path.join(carpeta, nombre)
        if os.path.isfile(ruta):
            with open(ruta, "rb") as archivo:
                resultado.append((nombre, archivo.read()))
    return resultado


def _salida_json(destino, cerrada=False, costo=None):
    salida = {"sala": destino, "cerrada": cerrada, "llave": None, "cierre_automatico": None}
    if costo is not None:
        salida["costo"] = costo
    return salida


# Mapa chico con costos variados. 4 -> 5 está cerrada: 5 solo se alcanza desde sí misma, así que ningún otro origen
# la tiene como destino. 6 solo tiene una salida cerrada: no alcanza ninguna sala y no aporta pares.
MAPA_CHICO = [
    {"id": 1, "nombre": "a", "salidas": {"E": _salida_json(2, costo=1), "S": _salida_json(3, costo=10)}},
    {"id": 2, "nombre": "b", "salidas": {"O": _salida_json(1, costo=1), "E": _salida_json(4, costo=2)}},
    {"id": 3, "nombre": "c", "salidas": {"N": _salida_json(1, costo=1)}},
    {"id": 4, "nombre": "d", "salidas": {"O": _salida_json(2, costo=5), "E": _salida_json(5, cerrada=True)}},
    {"id": 5, "nombre": "e", "salidas": {"O": _salida_json(4, costo=1)}},
    {"id": 6, "nombre": "f", "salidas": {"N": _salida_json(5, cerrada=True)}},
]
# Contado a mano: 1 a 4 alcanzan 3 salas cada una (nunca la 5 ni la 6), 5 alcanza 4 y 6 ninguna.
PARES_MAPA_CHICO = 3 * 4 + 4
ORIGENES_MAPA_CHICO = 5


def _guardar_copia(carpeta, id_cripta, salas_json):
    from AlmacenamientoLocalApi.AlmacenamientoLocalApi import AlmacenamientoLocalApi
    from DTOS.SalaEsqueleto import SalaEsqueleto
    AlmacenamientoLocalApi(carpeta).guardar_esqueleto(id_cripta, "v1", [SalaEsqueleto.desde_json(s) for s in salas_json])


class TestM4Referencia(unittest.TestCase):
    def _medir(self, carpeta=DATOS_LOCALES, **opciones):
        medir = getattr(bench_niebla, "medir_m4_referencia", None)
        self.assertIsNotNone(medir, "M4 no mide la cripta de referencia (T110)")
        return medir(repeticiones=1, carpeta=carpeta, **opciones)

    def _fila_unica(self, filas):
        self.assertEqual(len(filas), 1, [fila.texto() for fila in filas])
        fila = filas[0]
        self.assertEqual(fila.medicion, "M4")
        self.assertEqual(fila.variante, "referencia/paso")
        return fila

    @unittest.skipUnless(os.path.isdir(DATOS_LOCALES) and _mas_grande() is not None,
                         "sin copias locales de esqueletos en datos_locales/")
    def test_sc007_pr15_t110_fila_de_la_cripta_real_con_veredicto_contra_la_constante(self):
        # La ÚNICA prueba que mide la carpeta real: forma y conteos, con K = 1 y 1 repetición para que sea rápida, y
        # comprobando que solo lee datos_locales/ (la instantánea de antes y después es la misma).
        id_cripta, datos = _mas_grande()
        esqueleto = datos["esqueleto"]
        pares = _pares_json(esqueleto)
        antes = _instantanea(DATOS_LOCALES)
        self.assertIn("catalogo.json", [nombre for nombre, _ in antes])
        for modo, espacio in (("por llamada", None), ("reutilizado", bench_niebla.EspacioBusqueda)):
            with self.subTest(espacio=modo), mock.patch.object(bench_niebla, "CONFIRMADOS_M4_REFERENCIA", 1):
                fila = self._fila_unica(self._medir(espacio=espacio))
                self.assertIsInstance(fila.ms, float, fila.texto())
                self.assertGreaterEqual(fila.ms, 0.0)
                self.assertEqual(fila.valor("cripta"), id_cripta)
                self.assertEqual(fila.valor("V"), len(esqueleto))
                self.assertEqual(fila.valor("pasos"), 1)
                self.assertEqual(fila.valor("espacio"), modo)
                # Todos los pares alcanzables, contados aparte sobre el JSON; se confirman min(K, pares) = 1. El
                # peor par es uno de ellos y la fila trae su costo acumulado.
                self._comprobar_cribado(fila, pares)
                self.assertEqual(fila.valor("confirmados"), 1)
                # Veredicto con la única constante y la fila no es provisional.
                self.assertEqual(fila.veredicto, bench_niebla.veredicto_paso(fila.ms))
                with mock.patch.object(bench_niebla, "LIMITE_PASO_IR_A_MS", -1):
                    self.assertEqual(bench_niebla.veredicto_paso(fila.ms), "no cumple")
                self.assertFalse(fila.provisional)
                self.assertNotIn("PROVISIONAL", fila.texto())
                self.assertEqual(fila.nota, NOTA_REFERENCIA.format(id_cripta, len(esqueleto)))
                self.assertIn(fila.veredicto, fila.texto())
        self.assertEqual(_instantanea(DATOS_LOCALES), antes)

    def test_sc007_pr15_t110_elige_la_mas_grande_y_mide_solo_pares_alcanzables(self):
        # Copias locales sintéticas: una cadena de 3 y un mapa de 4 con una puerta cerrada de un solo sentido.
        from AlmacenamientoLocalApi.AlmacenamientoLocalApi import AlmacenamientoLocalApi
        from DTOS.SalaEsqueleto import SalaEsqueleto
        chica = [{"id": 1, "nombre": "a", "salidas": {"E": _salida_json(2)}},
                 {"id": 2, "nombre": "b", "salidas": {"O": _salida_json(1), "E": _salida_json(3)}},
                 {"id": 3, "nombre": "c", "salidas": {"O": _salida_json(2)}}]
        # Ids desordenados a propósito: 7 -> 3 cerrada, así que 3 es alcanzable desde 7 solo por 9.
        grande = [{"id": 7, "nombre": "w", "salidas": {"E": _salida_json(3, cerrada=True), "S": _salida_json(9)}},
                  {"id": 3, "nombre": "x", "salidas": {"O": _salida_json(7), "S": _salida_json(4)}},
                  {"id": 9, "nombre": "y", "salidas": {"N": _salida_json(7), "E": _salida_json(4)}},
                  {"id": 4, "nombre": "z", "salidas": {"N": _salida_json(3), "O": _salida_json(9)}}]
        with tempfile.TemporaryDirectory() as carpeta:
            almacen = AlmacenamientoLocalApi(carpeta)
            almacen.guardar_esqueleto("cripta-chica", "v-chica", [SalaEsqueleto.desde_json(s) for s in chica])
            almacen.guardar_esqueleto("cripta-grande", "v-grande", [SalaEsqueleto.desde_json(s) for s in grande])
            antes = _instantanea(carpeta)
            fila = self._fila_unica(self._medir(carpeta))
            self.assertEqual(_instantanea(carpeta), antes)
        self.assertEqual(fila.valor("cripta"), "cripta-grande")
        self.assertEqual(fila.valor("V"), 4)
        # El grafo es fuertemente conexo salvo por la puerta cerrada: los 4·3 pares siguen alcanzables.
        self.assertEqual(fila.valor("origenes"), 4)
        self.assertEqual(fila.valor("pares"), 12)
        self._comprobar_cribado(fila, _pares_json(grande))
        self.assertEqual(fila.nota, NOTA_REFERENCIA.format("cripta-grande", 4))

    def test_sc007_pr15_t110_grafo_dirigido_excluye_la_puerta_cerrada(self):
        # 1 -> 2 cerrada y 2 -> 1 abierta: desde 1 no se llega a 2, desde 2 sí a 1. Un solo par alcanzable.
        from AlmacenamientoLocalApi.AlmacenamientoLocalApi import AlmacenamientoLocalApi
        from DTOS.SalaEsqueleto import SalaEsqueleto
        salas = [{"id": 1, "nombre": "a", "salidas": {"E": _salida_json(2, cerrada=True)}},
                 {"id": 2, "nombre": "b", "salidas": {"O": _salida_json(1)}}]
        with tempfile.TemporaryDirectory() as carpeta:
            AlmacenamientoLocalApi(carpeta).guardar_esqueleto("cripta-par", "v1",
                                                              [SalaEsqueleto.desde_json(s) for s in salas])
            fila = self._fila_unica(self._medir(carpeta))
        self.assertEqual(fila.valor("origenes"), 1)
        self.assertEqual(fila.valor("pares"), 1)
        self.assertEqual(fila.valor("confirmados"), 1)
        self.assertEqual(fila.valor("peor"), "2->1")
        self.assertEqual(fila.valor("costo"), 100)

    def _comprobar_cribado(self, fila, pares):
        """La fila del cribado y confirmación frente a los pares ``[(origen, destino, costo)]`` contados aparte."""
        k = getattr(bench_niebla, "CONFIRMADOS_M4_REFERENCIA", None)
        self.assertIsNotNone(k, "falta la constante K de pares confirmados")
        self.assertEqual(fila.valor("pares"), len(pares))
        self.assertEqual(fila.valor("origenes"), _origenes_con_pares(pares))
        self.assertEqual(fila.valor("confirmados"), min(k, len(pares)))
        origen, destino = (int(parte) for parte in fila.valor("peor").split("->"))
        self.assertIn((origen, destino, fila.valor("costo")), pares)
        self.assertIsInstance(fila.ms, float, fila.texto())
        self.assertEqual(fila.veredicto, bench_niebla.veredicto_paso(fila.ms))
        self.assertIn("confirmados={}".format(fila.valor("confirmados")), fila.texto())

    def test_sc007_pr15_t110_enumera_todos_los_pares_alcanzables(self):
        # (a) Mapa chico con costos variados y puertas cerradas: los pares que enumera el bench (con las distancias
        # de un Dijkstra completo por origen) son los del Bellman-Ford sobre el JSON, con el mismo costo. La sala 6
        # no alcanza ninguna otra: no aporta pares y no falla.
        enumerar = getattr(bench_niebla, "pares_alcanzables", None)
        self.assertIsNotNone(enumerar, "el bench no enumera los pares alcanzables")
        esperados = _pares_json(MAPA_CHICO)
        self.assertEqual(len(esperados), PARES_MAPA_CHICO)
        self.assertEqual(_origenes_con_pares(esperados), ORIGENES_MAPA_CHICO)
        with tempfile.TemporaryDirectory() as carpeta:
            _guardar_copia(carpeta, "cripta-chica", MAPA_CHICO)
            _, grafo, salas = bench_niebla.preparar_m4_referencia(carpeta)
        for modo, espacio in (("por llamada", None), ("reutilizado", bench_niebla.EspacioBusqueda)):
            with self.subTest(espacio=modo):
                reutilizado = None if espacio is None else espacio(grafo.cantidad_salas)
                pares = enumerar(grafo, salas, reutilizado)
                self.assertEqual([(o.id, d.id, costo) for o, d, costo in pares], esperados)
                self.assertNotIn(6, [o.id for o, _, _ in pares])
                # El costo acumulado es el de la ruta que encuentra `primer_paso`.
                for origen, destino, costo in pares:
                    self.assertEqual(bench_niebla.primer_paso(grafo, origen, destino).costo_total, costo)

    def test_sc007_pr15_t110_la_fila_dice_pares_confirmados_peor_y_su_costo(self):
        # (b) «pares» = todos los alcanzables, «confirmados» = min(K, pares), y el peor par con su costo es uno de
        # los alcanzables. En las dos variantes de espacio.
        with tempfile.TemporaryDirectory() as carpeta:
            _guardar_copia(carpeta, "cripta-chica", MAPA_CHICO)
            for modo, espacio in (("por llamada", None), ("reutilizado", bench_niebla.EspacioBusqueda)):
                with self.subTest(espacio=modo):
                    fila = self._fila_unica(self._medir(carpeta, espacio=espacio))
                    self.assertEqual(fila.valor("espacio"), modo)
                    self._comprobar_cribado(fila, _pares_json(MAPA_CHICO))
                    self.assertFalse(fila.provisional)
                    self.assertEqual(fila.nota, NOTA_REFERENCIA.format("cripta-chica", len(MAPA_CHICO)))

    def test_sc007_pr15_t110_con_k_menor_o_mayor_que_los_pares_la_fila_es_valida(self):
        # (c) K = 1 confirma un solo par; K mayor que los pares confirma todos.
        self.assertIsNotNone(getattr(bench_niebla, "CONFIRMADOS_M4_REFERENCIA", None), "falta la constante K")
        with tempfile.TemporaryDirectory() as carpeta:
            _guardar_copia(carpeta, "cripta-chica", MAPA_CHICO)
            for k, confirmados in ((1, 1), (PARES_MAPA_CHICO + 10, PARES_MAPA_CHICO)):
                with mock.patch.object(bench_niebla, "CONFIRMADOS_M4_REFERENCIA", k):
                    for modo, espacio in (("por llamada", None), ("reutilizado", bench_niebla.EspacioBusqueda)):
                        with self.subTest(k=k, espacio=modo):
                            fila = self._fila_unica(self._medir(carpeta, espacio=espacio))
                            self.assertEqual(fila.valor("confirmados"), confirmados)
                            self._comprobar_cribado(fila, _pares_json(MAPA_CHICO))

    def test_sc007_pr15_t110_sin_esqueleto_la_fila_dice_no_medido_y_no_falla(self):
        with tempfile.TemporaryDirectory() as raiz:
            vacia = os.path.join(raiz, "vacia")
            os.mkdir(vacia)
            inexistente = os.path.join(raiz, "no_existe")
            for carpeta in (vacia, inexistente):
                with self.subTest(carpeta=os.path.basename(carpeta)):
                    fila = self._fila_unica(self._medir(carpeta))
                    self.assertIsNone(fila.ms)
                    self.assertIn("no medido", fila.texto())
                    self.assertIn("Motivo:", fila.texto())
                    self.assertEqual(fila.veredicto, "")
            # Leer no crea la carpeta que falta ni escribe en la vacía.
            self.assertFalse(os.path.exists(inexistente))
            self.assertEqual(os.listdir(vacia), [])

    def test_sc007_pr15_t110_el_bench_no_contiene_datos_de_la_cripta(self):
        # Principio IV: el id, la versión, los nombres de sala y las llaves se leen del archivo al correr. Necesita
        # la copia real para saber qué buscar, pero solo la lee: no mide (que el bench lee el id de la copia real lo
        # comprueba la prueba de la cripta real, y con una copia chica, la que elige la más grande).
        if not (os.path.isdir(DATOS_LOCALES) and _mas_grande() is not None):
            self.skipTest("sin copias locales de esqueletos en datos_locales/")
        id_cripta, datos = _mas_grande()
        with open(bench_niebla.__file__, encoding="utf-8") as archivo:
            codigo = archivo.read()
        self.assertNotIn(id_cripta, codigo)
        self.assertNotIn(str(datos["version"]), codigo)
        self.assertNotIn(f"{len(datos['esqueleto'])} salas", codigo)
        for sala in datos["esqueleto"]:
            self.assertNotIn(f'"{sala["nombre"]}"', codigo)
            for salida in sala["salidas"].values():
                if salida.get("llave"):
                    self.assertNotIn(salida["llave"], codigo)

    def test_sc007_pr15_t110_solo_lee_datos_locales(self):
        # Una carpeta como datos_locales/ (copia chica más un catalogo.json) no cambia al medir con las dos
        # variantes. La misma comprobación sobre la carpeta real la hace la prueba de la cripta real.
        with tempfile.TemporaryDirectory() as carpeta:
            _guardar_copia(carpeta, "cripta-chica", MAPA_CHICO)
            with open(os.path.join(carpeta, "catalogo.json"), "w", encoding="utf-8") as archivo:
                archivo.write("{}")
            antes = _instantanea(carpeta)
            self.assertIn("catalogo.json", [nombre for nombre, _ in antes])
            self._medir(carpeta)
            self._medir(carpeta, espacio=bench_niebla.EspacioBusqueda)
            self.assertEqual(_instantanea(carpeta), antes)

    def test_sc007_pr15_t110_corre_sin_red_ni_vista(self):
        with tempfile.TemporaryDirectory() as carpeta:
            _guardar_copia(carpeta, "cripta-chica", MAPA_CHICO)
            with _sin_red_ni_vista():
                filas = self._medir(carpeta)
        self._fila_unica(filas)


# T107 y T108: `--bench` corre M1 a M6 y la prueba rápida con tamaños mínimos. Sin afirmar tiempos.

def _sin_red_ni_vista():
    prohibido = AssertionError("las mediciones no usan red ni vista")
    pila = contextlib.ExitStack()
    pila.enter_context(mock.patch.object(socket.socket, "connect", side_effect=prohibido))
    pila.enter_context(mock.patch.object(VistaConsola, "__init__", side_effect=prohibido))
    return pila


class TestCorrerBench(unittest.TestCase):
    def test_pr15_por_omision_usa_los_tamanos_de_research_r9(self):
        tamanos = bench_niebla.TamanosBench()
        self.assertEqual(tamanos.m1, bench_niebla.TAMANOS_M1)
        self.assertEqual(tamanos.m2, bench_niebla.TAMANOS_M2)
        self.assertEqual(tamanos.m3_n, bench_niebla.TAMANOS_M3_N)
        self.assertEqual(tamanos.m3_vecinas, bench_niebla.VECINAS_M3)
        self.assertEqual(tamanos.m4, bench_niebla.TAMANOS_M4)
        self.assertEqual(tamanos.m5, bench_niebla.TAMANOS_M5)
        self.assertEqual(tamanos.m6_enemigos, bench_niebla.ENEMIGOS_M6)
        self.assertEqual(tamanos.m6_ciclos, bench_niebla.CICLOS_M6)
        self.assertEqual(tamanos.repeticiones, bench_niebla.REPETICIONES)

    def _correr_minimo(self, datos_locales=bench_niebla.CARPETA_DATOS_LOCALES):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, bench_niebla.ARCHIVO_RESULTADOS)
            with _sin_red_ni_vista(), contextlib.redirect_stdout(io.StringIO()):
                filas = bench_niebla.correr_bench(ruta, bench_niebla.TAMANOS_MINIMOS, datos_locales)
            with open(ruta, encoding="utf-8") as archivo:
                texto = archivo.read()
        return filas, texto

    def _con_cada_carpeta_de_datos(self, prueba):
        """(a) Una carpeta temporal con una copia chica armada a mano (`MAPA_CHICO`), en lugar de la carpeta real,
        para no medir la cripta grande en cada prueba; (b) siempre, una carpeta temporal vacía, como una copia limpia
        sin datos_locales/. ``prueba(filas, texto, con_datos)``: con_datos dice si la cripta de referencia se pudo
        medir."""
        with tempfile.TemporaryDirectory() as chica:
            _guardar_copia(chica, "cripta-chica", MAPA_CHICO)
            with self.subTest(datos_locales="copia chica"):
                prueba(*self._correr_minimo(chica), True)
        with tempfile.TemporaryDirectory() as vacia:
            with self.subTest(datos_locales="vacia"):
                prueba(*self._correr_minimo(vacia), False)

    def _comprobar_referencia_no_medida(self, fila):
        # Sin copias locales: una fila por modo de espacio, sin tiempo ni veredicto, no provisional y con el motivo.
        self.assertIsNone(fila.ms)
        self.assertEqual(fila.veredicto, "")
        self.assertFalse(fila.provisional)
        self.assertIn("no medido", fila.texto())
        self.assertIn("Motivo:", fila.texto())

    def test_sc006_pr15_t108_m1_a_m6_con_tamanos_minimos_sin_red_ni_vista(self):
        def comprobar(filas, texto, con_datos):
            for medicion in ("M1", "M2", "M3", "M4", "M5", "M6"):
                with self.subTest(medicion=medicion):
                    propias = [fila for fila in filas if fila.medicion == medicion]
                    self.assertTrue(propias)
                    for fila in propias:
                        self.assertIn(fila.texto(), texto)
                        if fila.variante.startswith("referencia") and not con_datos:
                            self._comprobar_referencia_no_medida(fila)
                        else:
                            self.assertIsNotNone(fila.ms, fila.texto())
            # M4: 8 filas sintéticas más una de la cripta de referencia por modo de espacio (T110).
            self.assertEqual(len(filas), 6 + 2 + 3 + 10 + 4 + 2)
            self.assertIn(platform.python_version(), texto)
            self.assertIn("PROVISIONAL", texto)
            self.assertNotIn("pendiente", texto)
            self.assertNotIn("no se da por cumplido hasta T110", texto)
        self._con_cada_carpeta_de_datos(comprobar)

    def test_sc007_pr15_t108_m4_con_y_sin_espacio_compara_contra_la_constante(self):
        def comprobar(filas, _, con_datos):
            m4 = [fila for fila in filas if fila.medicion == "M4"]
            self.assertEqual(len(m4), 10)
            for modo in ("por llamada", "reutilizado"):
                self.assertEqual(len([fila for fila in m4 if fila.valor("espacio") == modo]), 5)
            for fila in m4:
                with self.subTest(fila=fila.texto()):
                    # Las sintéticas son pruebas de estrés (PROVISIONAL); la de la cripta de referencia no (T110).
                    self.assertEqual(fila.provisional, not fila.variante.startswith("referencia"))
                    if fila.variante.startswith("referencia") and not con_datos:
                        self._comprobar_referencia_no_medida(fila)
                        continue
                    por_paso = fila.ms / fila.valor("pasos")
                    esperado = "cumple" if por_paso <= bench_niebla.LIMITE_PASO_IR_A_MS else "no cumple"
                    self.assertEqual(fila.veredicto, esperado)
        self._con_cada_carpeta_de_datos(comprobar)

    def test_sc007_pr15_t110_las_filas_de_referencia_van_despues_de_todas_las_sinteticas(self):
        # Medir la cripta de referencia entre los dos bloques sintéticos alteraba las filas que venían después.
        # Orden: sintéticas por llamada, sintéticas reutilizado, referencia por llamada, referencia reutilizado.
        with tempfile.TemporaryDirectory() as chica:
            _guardar_copia(chica, "cripta-chica", MAPA_CHICO)
            filas, _ = self._correr_minimo(chica)
        m4 = [(fila.variante.startswith("referencia"), fila.valor("espacio"))
              for fila in filas if fila.medicion == "M4"]
        self.assertEqual(m4, [(False, "por llamada")] * 4 + [(False, "reutilizado")] * 4
                         + [(True, "por llamada"), (True, "reutilizado")])

    def test_pr15_t107_main_bench_llama_a_la_medicion_de_niebla_sin_red_ni_vista(self):
        import main
        from tests import bench_cazador, bench_ciclo, bench_linea, bench_personaD, bench_resolubilidad
        with mock.patch.object(bench_personaD, "correr_bench") as persistencia, \
                mock.patch.object(bench_ciclo, "correr_bench") as ciclo, \
                mock.patch.object(bench_cazador, "correr_bench") as cazador, \
                mock.patch.object(bench_resolubilidad, "correr_bench") as resolubilidad, \
                mock.patch.object(bench_niebla, "correr_bench") as niebla,                 mock.patch.object(bench_linea, "correr_bench") as linea, \
                mock.patch("sys.argv", ["main.py", "--bench"]), \
                _sin_red_ni_vista(), contextlib.redirect_stdout(io.StringIO()):
            codigo = main.main()
        self.assertEqual(codigo, 0)
        for medicion in (persistencia, ciclo, cazador, resolubilidad):
            medicion.assert_called_once_with()
        niebla.assert_called_once_with()
        linea.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
