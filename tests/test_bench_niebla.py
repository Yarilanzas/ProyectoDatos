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
                self.assertIn("T110", fila.texto())
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

    def _correr_minimo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, bench_niebla.ARCHIVO_RESULTADOS)
            with _sin_red_ni_vista(), contextlib.redirect_stdout(io.StringIO()):
                filas = bench_niebla.correr_bench(ruta, bench_niebla.TAMANOS_MINIMOS)
            with open(ruta, encoding="utf-8") as archivo:
                texto = archivo.read()
        return filas, texto

    def test_sc006_pr15_t108_m1_a_m6_con_tamanos_minimos_sin_red_ni_vista(self):
        filas, texto = self._correr_minimo()
        for medicion in ("M1", "M2", "M3", "M4", "M5", "M6"):
            with self.subTest(medicion=medicion):
                propias = [fila for fila in filas if fila.medicion == medicion]
                self.assertTrue(propias)
                for fila in propias:
                    self.assertIsNotNone(fila.ms, fila.texto())
                    self.assertIn(fila.texto(), texto)
        self.assertEqual(len(filas), 6 + 2 + 3 + 8 + 4 + 2)
        self.assertIn(platform.python_version(), texto)
        self.assertIn("PROVISIONAL", texto)
        self.assertNotIn("pendiente", texto)

    def test_sc007_pr15_t108_m4_con_y_sin_espacio_compara_contra_la_constante(self):
        filas, _ = self._correr_minimo()
        m4 = [fila for fila in filas if fila.medicion == "M4"]
        self.assertEqual(len(m4), 8)
        for modo in ("por llamada", "reutilizado"):
            self.assertEqual(len([fila for fila in m4 if fila.valor("espacio") == modo]), 4)
        for fila in m4:
            with self.subTest(fila=fila.texto()):
                self.assertTrue(fila.provisional)
                por_paso = fila.ms / fila.valor("pasos")
                esperado = "cumple" if por_paso <= bench_niebla.LIMITE_PASO_IR_A_MS else "no cumple"
                self.assertEqual(fila.veredicto, esperado)

    def test_pr15_t107_main_bench_llama_a_la_medicion_de_niebla_sin_red_ni_vista(self):
        import main
        from tests import bench_cazador, bench_ciclo, bench_personaD, bench_resolubilidad
        with mock.patch.object(bench_personaD, "correr_bench") as persistencia, \
                mock.patch.object(bench_ciclo, "correr_bench") as ciclo, \
                mock.patch.object(bench_cazador, "correr_bench") as cazador, \
                mock.patch.object(bench_resolubilidad, "correr_bench") as resolubilidad, \
                mock.patch.object(bench_niebla, "correr_bench") as niebla, \
                mock.patch("sys.argv", ["main.py", "--bench"]), \
                _sin_red_ni_vista(), contextlib.redirect_stdout(io.StringIO()):
            codigo = main.main()
        self.assertEqual(codigo, 0)
        for medicion in (persistencia, ciclo, cazador, resolubilidad):
            medicion.assert_called_once_with()
        niebla.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
