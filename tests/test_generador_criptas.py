# Pruebas del generador de criptas sintéticas (spec 002, T003).
# Cada prueba cita el FR que respalda: FR-013 (mismos datos, mismo resultado) o FR-029 (criptas del bench).

import json
import random
import unittest

from tests.generador_criptas import SIN_LLAVE, generar_cripta


def _salidas(cripta):
    # (origen, dirección, datos de la salida) de toda la cripta
    for sala in cripta.salas_json:
        for direccion, datos in sala["salidas"].items():
            yield sala["id"], direccion, datos


class PruebasGeneradorCriptas(unittest.TestCase):

    def test_fr013_misma_semilla_mismos_datos(self):
        """FR-013: misma semilla → salas_json y llaves_json idénticos."""
        for opciones in ({}, {"resoluble": False}, {"resoluble": False, "con_ciclo": True},
                         {"llave_de_enemigo": True}):
            a = generar_cripta(42, 120, 6, **opciones)
            b = generar_cripta(42, 120, 6, **opciones)
            self.assertEqual(json.dumps(a.salas_json, sort_keys=True), json.dumps(b.salas_json, sort_keys=True))
            self.assertEqual(json.dumps(a.llaves_json, sort_keys=True), json.dumps(b.llaves_json, sort_keys=True))
            self.assertEqual(json.dumps(a.detalles_json, sort_keys=True),
                             json.dumps(b.detalles_json, sort_keys=True))

    def test_fr013_semillas_distintas_criptas_distintas(self):
        """FR-013: semillas distintas → criptas distintas."""
        a = generar_cripta(1, 300, 4)
        b = generar_cripta(2, 300, 4)
        self.assertNotEqual(json.dumps([a.salas_json, a.llaves_json], sort_keys=True),
                            json.dumps([b.salas_json, b.llaves_json], sort_keys=True))

    def test_fr029_300_salas_entre_700_y_820_salidas(self):
        """FR-029: 300 salas → entre 700 y 820 salidas, en N, S, E, O e ids contiguos desde 1."""
        for semilla in range(5):
            cripta = generar_cripta(semilla, 300, 4)
            salidas = list(_salidas(cripta))
            self.assertGreaterEqual(len(salidas), 700)
            self.assertLessEqual(len(salidas), 820)
            self.assertEqual([sala["id"] for sala in cripta.salas_json], list(range(1, 301)))
            for _, direccion, datos in salidas:
                self.assertIn(direccion, ("N", "S", "E", "O"))
                self.assertTrue(1 <= datos["sala"] <= 300)

    def test_fr029_salidas_dirigidas_con_costo_por_sentido(self):
        """FR-029: A→B y B→A son salidas propias, con el costo de su sentido."""
        cripta = generar_cripta(3, 50, 3, costo_ida=2, costo_vuelta=7)
        for origen, _, datos in _salidas(cripta):
            esperado = 2 if datos["sala"] > origen else 7
            self.assertEqual(datos["costo"], esperado)
            vuelta = [d for o, _, d in _salidas(cripta) if o == datos["sala"] and d["sala"] == origen]
            self.assertEqual(len(vuelta), 1)

    def test_fr029_resoluble_cada_puerta_de_la_region_pide_la_llave_anterior(self):
        """FR-029: en la variante resoluble, cada puerta que entra a la región de k(i+1) pide k(i)."""
        cripta = generar_cripta(5, 300, 4)
        llaves = cripta.llaves
        for j in range(len(llaves)):
            # k(j+1) está en la región R(j)
            ubicacion = cripta.llaves_json[j]
            self.assertEqual(ubicacion["id"], llaves[j])
            self.assertEqual(cripta.region_de(ubicacion["sala"]), j)
        entran = 0
        for origen, _, datos in _salidas(cripta):
            r_origen = cripta.region_de(origen)
            r_destino = cripta.region_de(datos["sala"])
            if 1 <= r_destino < len(llaves) and r_origen < r_destino:
                entran += 1
                self.assertTrue(datos["cerrada"])
                self.assertEqual(datos["llave"], llaves[r_destino - 1])
            elif r_origen == r_destino:
                self.assertFalse(datos["cerrada"])
        self.assertGreaterEqual(entran, len(llaves) - 1)
        # k1 en la región de la sala inicial, que se recorre sin abrir puertas
        self.assertEqual(cripta.region_de(cripta.detalles.sala_inicial), 0)

    def test_fr029_existe_salida_hacia_sala_salida_con_llave_salida(self):
        """FR-029: existe una salida hacia sala_salida que pide llave_salida (la última de la cadena)."""
        for opciones in ({}, {"resoluble": False}, {"resoluble": False, "con_ciclo": True}):
            cripta = generar_cripta(8, 300, 4, **opciones)
            self.assertEqual(cripta.detalles.llave_salida, cripta.llaves[-1])
            hacia_salida = [d for _, _, d in _salidas(cripta) if d["sala"] == cripta.detalles.sala_salida]
            self.assertTrue(any(d["cerrada"] and d.get("llave") == cripta.detalles.llave_salida
                                for d in hacia_salida))

    def test_fr029_no_resoluble_con_ciclo_tiene_puerta_k_k(self):
        """FR-029: la variante no resoluble con con_ciclo=True contiene la puerta K→K y el ciclo K1 ↔ K2."""
        cripta = generar_cripta(9, 300, 4, resoluble=False, con_ciclo=True)
        k = len(cripta.llaves)
        ultima = cripta.llaves[-1]
        r_ultima = cripta.region_de(cripta.llaves_json[-1]["sala"])
        puertas = [d for o, _, d in _salidas(cripta)
                   if cripta.region_de(d["sala"]) == r_ultima and cripta.region_de(o) != r_ultima]
        self.assertTrue(puertas)
        for datos in puertas:
            self.assertTrue(datos["cerrada"])
            self.assertEqual(datos["llave"], ultima)
        # ciclo por cadena: R(K-3) pide k(K-1) y guarda k(K-2); R(K-2) pide k(K-2) y guarda k(K-1)
        self.assertEqual(cripta.entrada[k - 3], cripta.llaves[k - 2])
        self.assertEqual(cripta.entrada[k - 2], cripta.llaves[k - 3])
        self.assertEqual(cripta.region_de(cripta.llaves_json[k - 3]["sala"]), k - 3)
        self.assertEqual(cripta.region_de(cripta.llaves_json[k - 2]["sala"]), k - 2)
        # y una puerta cerrada sin llave
        self.assertTrue(any(d["cerrada"] and "llave" not in d for _, _, d in _salidas(cripta)))

    def test_fr029_no_resoluble_sin_ciclo_tiene_puertas_sin_llave(self):
        """FR-029: la variante no resoluble sin ciclo cierra sin llave la región de llave_salida."""
        cripta = generar_cripta(10, 300, 4, resoluble=False)
        self.assertEqual(cripta.entrada[len(cripta.llaves) - 1], SIN_LLAVE)
        r = cripta.region_de(cripta.llaves_json[-1]["sala"])
        puertas = [d for o, _, d in _salidas(cripta)
                   if cripta.region_de(d["sala"]) == r and cripta.region_de(o) != r]
        self.assertTrue(puertas)
        for datos in puertas:
            self.assertTrue(datos["cerrada"])
            self.assertNotIn("llave", datos)

    def test_fr029_llave_de_enemigo(self):
        """FR-029: llave_de_enemigo=True ubica una llave con enemigo en la sala donde inicia."""
        cripta = generar_cripta(11, 40, 3, llave_de_enemigo=True)
        con_enemigo = [u for u in cripta.llaves_json if u.get("enemigo")]
        self.assertEqual(len(con_enemigo), 1)
        ubicaciones = cripta.ubicaciones()
        self.assertEqual(ubicaciones[0].enemigo, con_enemigo[0]["enemigo"])
        self.assertEqual(ubicaciones[0].sala, con_enemigo[0]["sala"])

    def test_fr013_no_cambia_el_random_global(self):
        """FR-013: el generador no toca el estado del random global."""
        random.seed(1234)
        antes = random.getstate()
        generar_cripta(12, 300, 4, resoluble=False, con_ciclo=True, llave_de_enemigo=True)
        self.assertEqual(random.getstate(), antes)

    def test_fr029_esqueleto_y_ubicaciones_son_dtos(self):
        """FR-029: esqueleto() y ubicaciones() devuelven los DTO del servicio."""
        cripta = generar_cripta(13, 30, 3)
        esqueleto = cripta.esqueleto()
        self.assertEqual(len(esqueleto), 30)
        self.assertEqual(esqueleto[0].id, 1)
        self.assertEqual([u.id_llave for u in cripta.ubicaciones()], cripta.llaves)


if __name__ == "__main__":
    unittest.main()
