# Memoria acotada de la línea de tiempo (spec 004, Historia 6; T091, T092 y T093; FR-017, FR-019, FR-021, SC-006).
# Partidas reales (sin red, en carpetas temporales), con retrocesos y cargas, sobre `SesionLinea`:
#
#   T091 (US6-2): cuántos puntos de control hay: uno cada K acciones, más el de cada retroceso y el de cada carga.
#   T092 (US6-3): ninguna consulta rehace más de K acciones (contador `acciones_rehechas`, T096).
#   T093 (US6-4): la memoria de la línea (`tracemalloc`) crece con las acciones y con un punto cada K, no con
#                 «acciones × tamaño del estado».

import gc
import os
import sys
import tracemalloc
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Modelo.BusquedaBinaria import ultimo_menor_o_igual
from Modelo.LineaTiempo import K_POR_OMISION
from tests.utiles_linea import GeneradorAcciones, SesionLinea, jugar, partida_linea

ACCIONES = 5000


def techo(numerador, denominador):
    return -(-numerador // denominador)


class Recorrido:
    """Una partida con retrocesos y cargas intercalados, hasta `acciones` vigentes. `especiales` son las posiciones (acción
    `n` en ese momento) de cada retroceso y de cada carga; `retrocesos` y `cargas` cuentan P y L."""

    def __init__(self, test, k, acciones, retrocesos=2, cargas=2):
        self.sesion = SesionLinea(k=k, semilla=5, pergaminos=retrocesos, huellas=False)
        test.addCleanup(self.sesion.cerrar)
        self.test = test
        self.k = k
        self.especiales = []
        self.retrocesos = 0
        self.cargas = 0
        tramo = acciones // (retrocesos + cargas + 1)
        for vuelta in range(max(retrocesos, cargas)):
            if vuelta < retrocesos:
                self.sesion.jugar(tramo)
                test.assertTrue(self.sesion.retroceder())
                self.retrocesos += 1
                self.especiales.append(self.sesion.linea.acciones)
            if vuelta < cargas:
                self.sesion.jugar(tramo)
                self.sesion.guardar_y_cargar()
                self.cargas += 1
                self.especiales.append(self.sesion.linea.acciones)
        self.sesion.jugar(acciones - self.sesion.linea.acciones)

    @property
    def linea(self):
        return self.sesion.linea


class PruebasPuntosDeControl(unittest.TestCase):

    def comprobar(self, recorrido):
        linea, k = recorrido.linea, recorrido.k
        n = linea.acciones
        cota = techo(n, k) + 1 + recorrido.cargas + recorrido.retrocesos
        self.assertLessEqual(linea.cantidad_puntos, cota,
                             f"K={k}: {linea.cantidad_puntos} puntos con n={n}, L={recorrido.cargas}, P={recorrido.retrocesos}")
        # no decrecientes y todos dentro de la historia
        for anterior, siguiente in zip(linea.pc_accion, linea.pc_accion[1:]):
            self.assertLessEqual(anterior, siguiente)
        self.assertLessEqual(linea.pc_accion[-1], n)
        # quitando un punto por cada retroceso y cada carga, lo que queda es uno por múltiplo de K, sin repetir
        regulares = list(linea.pc_accion)
        for posicion in recorrido.especiales:
            if posicion in regulares:
                regulares.remove(posicion)
        for accion in regulares:
            self.assertEqual(accion % k, 0, f"K={k}: un punto en la acción {accion} que no es de un retroceso ni de una carga")
        for anterior, siguiente in zip(regulares, regulares[1:]):
            self.assertLess(anterior, siguiente, f"K={k}: dos puntos regulares en la acción {anterior}")

    def test_fr017_sc006_cinco_mil_acciones_con_varias_k_retrocesos_y_cargas(self):
        for k in (10, 50, 500):
            with self.subTest(k=k):
                recorrido = Recorrido(self, k, ACCIONES)
                self.assertEqual(recorrido.linea.acciones, ACCIONES)
                self.assertEqual((recorrido.retrocesos, recorrido.cargas), (2, 2))
                self.comprobar(recorrido)

    def test_fr017_k_por_omision(self):
        recorrido = Recorrido(self, K_POR_OMISION, 1500, retrocesos=1, cargas=1)
        self.comprobar(recorrido)

    def test_fr017_sin_retrocesos_ni_cargas_es_un_punto_cada_k_mas_el_inicial(self):
        sesion = SesionLinea(k=25, semilla=2, huellas=False)
        self.addCleanup(sesion.cerrar)
        sesion.jugar(1000)
        self.assertEqual(sesion.linea.cantidad_puntos, 1000 // 25 + 1)
        self.assertEqual(sesion.linea.pc_accion, [accion for accion in range(0, 1001, 25)])

    def test_fr017_el_punto_de_un_retroceso_reemplaza_al_regular_de_su_accion(self):
        sesion = SesionLinea(k=10, semilla=2, pergaminos=1, huellas=False)
        self.addCleanup(sesion.cerrar)
        base = sesion.linea.acciones
        sesion.jugar(30 - base + 1)                      # 30 acciones y una más: el punto regular de 30 ya existe
        self.assertEqual(sesion.linea.acciones, 31)
        puntos = sesion.linea.cantidad_puntos
        self.assertTrue(sesion.retroceder())             # vuelve a 30
        self.assertEqual(sesion.linea.acciones, 30)
        self.assertEqual(sesion.linea.cantidad_puntos, puntos)
        self.assertEqual(sesion.linea.pc_accion.count(30), 1)


class PruebasAccionesRehechas(unittest.TestCase):
    """T092 y T096: el contador de lo que rehízo la última consulta."""

    def recorrido(self, k):
        return Recorrido(self, k, 100, retrocesos=2, cargas=2)

    def test_fr019_ninguna_consulta_rehace_mas_de_k_acciones(self):
        for k in (1, 3, 7):
            with self.subTest(k=k):
                recorrido = self.recorrido(k)
                linea, motor = recorrido.linea, recorrido.sesion.motor
                for numero in range(1, linea.acciones + 2):
                    linea.consultar_accion(numero, motor)
                    self.assertLessEqual(linea.acciones_rehechas, k, f"#{numero}")
                    if numero <= linea.acciones:
                        punto = linea.pc_accion[ultimo_menor_o_igual(linea.pc_accion, numero - 1)]
                        self.assertEqual(linea.acciones_rehechas, numero - 1 - punto, f"#{numero}")
                    else:
                        self.assertEqual(linea.acciones_rehechas, 0)       # la decisión actual es el motor vivo
                instantes = []
                for t in range(0, linea.reloj_actual + 1, 53):
                    instantes.append(t)
                for reloj in linea.vig_reloj:
                    instantes.append(reloj)
                    instantes.append(reloj + 1)   # entre dos decisiones: la acción parcial también cuenta
                for t in instantes:
                    if t > linea.reloj_actual:
                        continue
                    linea.consultar_instante(t, motor)
                    self.assertLessEqual(linea.acciones_rehechas, k, f"t={t}")

    def test_fr019_clon_antes_de_cuenta_igual(self):
        recorrido = self.recorrido(7)
        linea = recorrido.linea
        for numero in (1, 2, 50, 77, linea.acciones):
            linea.clon_antes_de(numero, recorrido.sesion.motor)
            self.assertLessEqual(linea.acciones_rehechas, 7)

    def test_fr019_t_igual_al_reloj_actual_no_rehace_nada(self):
        recorrido = self.recorrido(7)
        linea = recorrido.linea
        linea.consultar_accion(40, recorrido.sesion.motor)
        self.assertGreater(linea.acciones_rehechas, -1)
        linea.consultar_instante(linea.reloj_actual, recorrido.sesion.motor)
        self.assertEqual(linea.acciones_rehechas, 0)

    def test_fr019_el_contador_no_cambia_el_resultado_de_las_consultas(self):
        recorrido = self.recorrido(3)
        linea, motor = recorrido.linea, recorrido.sesion.motor
        primero = [linea.consultar_accion(numero, motor).sala for numero in range(1, linea.acciones + 1)]
        segundo = [linea.consultar_accion(numero, motor).sala for numero in range(1, linea.acciones + 1)]
        self.assertEqual(primero, segundo)


def memoria_con_linea(acciones, k):
    """Bytes que retiene una partida de `acciones` acciones **con** línea, justo después de jugarla."""
    gc.collect()
    tracemalloc.start()
    try:
        sesion = SesionLinea(k=k, semilla=3, huellas=False)
        sesion.jugar(acciones)
        gc.collect()
        actual = tracemalloc.get_traced_memory()[0]
        puntos = sesion.linea.cantidad_puntos
        sesion.cerrar()
    finally:
        tracemalloc.stop()
    return actual, puntos


def memoria_sin_linea(acciones):
    """Lo mismo, pero la partida solo se juega (sin registrar nada en la línea)."""
    gc.collect()
    tracemalloc.start()
    try:
        partida = partida_linea(semilla=3)
        jugar(partida.motor, GeneradorAcciones(3), acciones)
        gc.collect()
        actual = tracemalloc.get_traced_memory()[0]
        partida.cerrar()
    finally:
        tracemalloc.stop()
    return actual


SIN_PUNTOS = 10 ** 6   # un K tan grande que solo existe el punto inicial
_MEDIDAS = []          # (acciones, k, bytes de la línea, puntos): `tracemalloc` es lento, cada medida se hace una vez
_BASES = []            # (acciones, bytes de la partida sin línea)


def memoria_de_la_linea(acciones, k):
    """(bytes de la línea, puntos): la partida con línea menos la misma partida sin línea. La parte fija (el gestor
    histórico, el motor y su estado inicial) se resta; el motor juega las mismas acciones (misma semilla)."""
    for medida in _MEDIDAS:
        if medida[0] == acciones and medida[1] == k:
            return medida[2], medida[3]
    base = None
    for conocida in _BASES:
        if conocida[0] == acciones:
            base = conocida[1]
    if base is None:
        base = memoria_sin_linea(acciones)
        _BASES.append((acciones, base))
    con, puntos = memoria_con_linea(acciones, k)
    _MEDIDAS.append((acciones, k, con - base, puntos))
    return con - base, puntos


class PruebasMemoria(unittest.TestCase):
    """T093. Se compara con un margen amplio: `tracemalloc` mide también la basura del intérprete."""

    def test_fr021_sc006_duplicar_las_acciones_duplica_aproximadamente_la_memoria(self):
        m1, _ = memoria_de_la_linea(200, 10)
        m2, _ = memoria_de_la_linea(400, 10)
        m3, _ = memoria_de_la_linea(800, 10)
        primero = m2 - m1       # de 200 a 400 acciones
        segundo = m3 - m2       # de 400 a 800: el doble de acciones nuevas
        self.assertGreater(primero, 0)
        razon = segundo / primero
        self.assertGreater(razon, 1.3, f"la memoria no crece con las acciones (razón {razon:.2f})")
        self.assertLess(razon, 3.0, f"la memoria crece más rápido que las acciones (razón {razon:.2f})")

    def test_fr021_sc006_un_punto_cada_k_cuesta_lo_mismo_sin_importar_cuantas_acciones_hay(self):
        # bytes por punto de control extra = (K chico - sin puntos) / (puntos extra); no debe crecer con las acciones
        por_punto = []
        for acciones in (400, 800):
            con_k, puntos_k = memoria_de_la_linea(acciones, 10)
            sin_k, puntos_sin = memoria_de_la_linea(acciones, SIN_PUNTOS)
            self.assertEqual(puntos_sin, 1)
            self.assertEqual(puntos_k, acciones // 10 + 1)
            por_punto.append((con_k - sin_k) / (puntos_k - puntos_sin))
        self.assertGreater(por_punto[0], 0)
        razon = por_punto[1] / por_punto[0]
        self.assertGreater(razon, 0.6, f"bytes por punto: {por_punto}")
        self.assertLess(razon, 1.7, f"el punto de control pesa más cuantas más acciones hay: {por_punto}")

    def test_fr021_sc006_mas_k_menos_memoria(self):
        chica, _ = memoria_de_la_linea(800, 10)
        grande, _ = memoria_de_la_linea(800, SIN_PUNTOS)
        self.assertLess(grande, chica)

    def test_fr021_sin_puntos_extra_el_guion_crece_linealmente(self):
        # con un solo punto (K enorme) lo único que crece es el guion: O(n), no O(n·S)
        m1, _ = memoria_de_la_linea(200, SIN_PUNTOS)
        m2, _ = memoria_de_la_linea(400, SIN_PUNTOS)
        m3, _ = memoria_de_la_linea(800, SIN_PUNTOS)
        primero, segundo = m2 - m1, m3 - m2
        self.assertGreater(primero, 0)
        self.assertLess(segundo / primero, 3.0)
        self.assertGreater(segundo / primero, 1.2)


if __name__ == "__main__":
    unittest.main()
