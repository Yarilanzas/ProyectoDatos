# Pruebas de RegistroLinea, el bloque de la línea del CRPT 3 (spec 004, T064; FR-022, FR-024, FR-031; PR-10).
# Formato: specs/004-linea-de-tiempo/contracts/formato-partida.md (sección «Bloque de la línea»). Sin red, sin archivos.
#
# Un registro es una tupla: (ACCION, nombre, argumento, reloj, secuencia), (RETROCESO, acciones_vigentes) o
# (CARGA, reloj_cargado). Los bytes que se arman a mano aquí son el contrato: si el formato cambia, estas pruebas fallan.

import json
import os
import struct
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Persistencia.FormatoBinario import VersionIncompatible
from Persistencia.RegistroLinea import ACCION, CARGA, RETROCESO, RegistroLinea


def accion(nombre, argumento, reloj, secuencia):
    """Bytes de un registro ACCION, armados a mano."""
    nombre_b = nombre.encode("utf-8")
    argumento_b = argumento.encode("utf-8")
    return (struct.pack("<BH", ACCION, len(nombre_b)) + nombre_b + struct.pack("<H", len(argumento_b)) + argumento_b
            + struct.pack("<QQ", reloj, secuencia))


def retroceso(quedan):
    return struct.pack("<BI", RETROCESO, quedan)


def carga(reloj):
    return struct.pack("<BQ", CARGA, reloj)


def bloque(k, *registros):
    """Bloque completo: `<I` K, `<I` cantidad y los registros ya serializados."""
    return struct.pack("<II", k, len(registros)) + b"".join(registros)


REGISTROS = [
    (ACCION, "mover", "E", 0, 0),
    (ACCION, "esperar", "", 100, 3),
    (ACCION, "atacar", "e-rata-1", 200, 5),
    (RETROCESO, 1),
    (CARGA, 300),
    (ACCION, "mover", "O", 300, 0),
]


class PruebasRegistroLinea(unittest.TestCase):

    # ───────────── ida y vuelta ─────────────

    def test_fr022_ida_y_vuelta_binaria(self):
        registro = RegistroLinea(50, REGISTROS)
        leido = RegistroLinea.from_bytes(registro.to_bytes())
        self.assertEqual(leido.k, 50)
        self.assertEqual(leido.registros, REGISTROS)
        self.assertEqual(leido, registro)

    def test_fr022_ida_y_vuelta_json(self):
        registro = RegistroLinea(7, REGISTROS)
        texto = json.dumps(registro.to_dict(), ensure_ascii=False)
        leido = RegistroLinea.from_dict(json.loads(texto))
        self.assertEqual(leido, registro)
        self.assertEqual(leido.to_bytes(), registro.to_bytes())

    def test_fr022_json_trae_k_y_la_lista_de_registros(self):
        datos = RegistroLinea(7, REGISTROS).to_dict()
        self.assertEqual(datos["k"], 7)
        self.assertEqual(len(datos["registros"]), len(REGISTROS))

    def test_fr022_la_linea_vacia_es_valida(self):
        registro = RegistroLinea(50, [])
        self.assertEqual(registro.to_bytes(), bloque(50))
        self.assertEqual(RegistroLinea.from_bytes(registro.to_bytes()), registro)

    def test_fr022_conserva_tildes_y_utf8(self):
        registro = RegistroLinea(5, [(ACCION, "usar", "pergamino-ñandú-é", 0, 0)])
        self.assertEqual(RegistroLinea.from_bytes(registro.to_bytes()), registro)

    # ───────────── orden canónico y bytes exactos ─────────────

    def test_fr022_el_mismo_estado_da_los_mismos_bytes(self):
        uno = RegistroLinea(50, list(REGISTROS)).to_bytes()
        otro = RegistroLinea(50, [tuple(registro) for registro in REGISTROS]).to_bytes()
        self.assertEqual(uno, otro)
        self.assertEqual(uno, RegistroLinea.from_bytes(uno).to_bytes())

    def test_fr022_bytes_exactos_del_contrato(self):
        esperado = bloque(50, accion("mover", "E", 0, 0), accion("esperar", "", 100, 3), accion("atacar", "e-rata-1", 200, 5),
                          retroceso(1), carga(300), accion("mover", "O", 300, 0))
        self.assertEqual(RegistroLinea(50, REGISTROS).to_bytes(), esperado)

    def test_fr022_el_orden_es_el_cronologico(self):
        al_reves = RegistroLinea(50, list(reversed(REGISTROS))).to_bytes()
        self.assertNotEqual(al_reves, RegistroLinea(50, REGISTROS).to_bytes())

    # ───────────── tamaños (formato-partida.md#tamaño) ─────────────

    def test_fr022_tamanos_del_contrato(self):
        self.assertEqual(len(RegistroLinea(50, [(ACCION, "mover", "E", 0, 0)]).to_bytes()), 8 + 27)
        self.assertEqual(len(RegistroLinea(50, [(RETROCESO, 0)]).to_bytes()), 8 + 5)
        self.assertEqual(len(RegistroLinea(50, [(CARGA, 0)]).to_bytes()), 8 + 9)

    def test_fr022_largo_linea_es_8_mas_la_suma_de_los_registros(self):
        suma = 27 + len(accion("esperar", "", 100, 3)) + len(accion("atacar", "e-rata-1", 200, 5)) + 5 + 9 + 27
        self.assertEqual(len(RegistroLinea(50, REGISTROS).to_bytes()), 8 + suma)

    # ───────────── rechazos al leer (FR-024): VersionIncompatible ─────────────

    def test_fr024_bloque_truncado_en_cualquier_posicion(self):
        datos = RegistroLinea(50, REGISTROS).to_bytes()
        for corte in range(len(datos)):
            with self.subTest(corte=corte):
                with self.assertRaises(VersionIncompatible):
                    RegistroLinea.from_bytes(datos[:corte])

    def test_fr024_la_cantidad_declarada_no_se_cumple(self):
        # dice 3 registros y trae uno
        datos = struct.pack("<II", 50, 3) + accion("mover", "E", 0, 0)
        with self.assertRaises(VersionIncompatible):
            RegistroLinea.from_bytes(datos)

    def test_fr024_tipo_desconocido(self):
        for tipo in (0, 4, 9, 255):
            with self.subTest(tipo=tipo):
                datos = struct.pack("<II", 50, 1) + struct.pack("<BQ", tipo, 0)
                with self.assertRaises(VersionIncompatible):
                    RegistroLinea.from_bytes(datos)

    def test_fr031_k_menor_que_1_se_rechaza(self):
        with self.assertRaises(VersionIncompatible):
            RegistroLinea.from_bytes(bloque(0))
        with self.assertRaises(VersionIncompatible):
            RegistroLinea.from_bytes(bloque(0, accion("mover", "E", 0, 0)))

    def test_fr024_nombre_invalido(self):
        for nombre in ("", "#mover", "@cargar", "dos palabras", "tab\taqui", "retroceder"):
            with self.subTest(nombre=nombre):
                with self.assertRaises(VersionIncompatible):
                    RegistroLinea.from_bytes(bloque(50, accion(nombre, "", 0, 0)))

    def test_fr024_argumento_con_salto_de_linea(self):
        with self.assertRaises(VersionIncompatible):
            RegistroLinea.from_bytes(bloque(50, accion("mover", "E\nN", 0, 0)))

    def test_fr024_texto_utf8_invalido(self):
        malo = struct.pack("<BH", ACCION, 2) + b"\xff\xfe" + struct.pack("<H", 0) + struct.pack("<QQ", 0, 0)
        with self.assertRaises(VersionIncompatible):
            RegistroLinea.from_bytes(bloque(50, malo))

    def test_fr024_bytes_sobrantes(self):
        datos = RegistroLinea(50, REGISTROS).to_bytes()
        with self.assertRaises(VersionIncompatible):
            RegistroLinea.from_bytes(datos + b"\x00")
        with self.assertRaises(VersionIncompatible):
            RegistroLinea.from_bytes(bloque(50) + b"\x01\x02")

    def test_fr024_retroceso_que_deja_mas_acciones_de_las_que_habia(self):
        # una acción vigente y un retroceso que dice «quedan 2»
        with self.assertRaises(VersionIncompatible):
            RegistroLinea.from_bytes(bloque(50, accion("mover", "E", 0, 0), retroceso(2)))
        # sin ninguna acción, «quedan 1»
        with self.assertRaises(VersionIncompatible):
            RegistroLinea.from_bytes(bloque(50, retroceso(1)))

    def test_fr024_el_retroceso_cuenta_las_vigentes_y_no_las_del_guion(self):
        # 2 acciones, retroceso a 1, otra acción: vigentes = 2; un retroceso a 2 es válido, a 3 no
        base = [accion("mover", "E", 0, 0), accion("esperar", "", 100, 1), retroceso(1), accion("esperar", "", 100, 2)]
        RegistroLinea.from_bytes(bloque(50, *base, retroceso(2)))
        with self.assertRaises(VersionIncompatible):
            RegistroLinea.from_bytes(bloque(50, *base, retroceso(3)))

    def test_fr024_una_carga_no_cambia_las_vigentes(self):
        RegistroLinea.from_bytes(bloque(50, accion("mover", "E", 0, 0), carga(100), retroceso(1)))
        with self.assertRaises(VersionIncompatible):
            RegistroLinea.from_bytes(bloque(50, accion("mover", "E", 0, 0), carga(100), retroceso(2)))

    def test_fr024_from_bytes_acepta_bytearray_y_memoryview(self):
        datos = RegistroLinea(50, REGISTROS).to_bytes()
        self.assertEqual(RegistroLinea.from_bytes(bytearray(datos)), RegistroLinea(50, REGISTROS))
        self.assertEqual(RegistroLinea.from_bytes(memoryview(datos)), RegistroLinea(50, REGISTROS))

    def test_fr024_from_dict_incompleto_o_invalido(self):
        bueno = RegistroLinea(50, REGISTROS).to_dict()
        for malo in ({}, {"k": 50}, {"registros": []}, {"k": 0, "registros": []}, {"k": "50", "registros": []},
                     {"k": 50, "registros": [["DESCONOCIDO", 1]]},
                     {"k": 50, "registros": [["ACCION", "mover"]]},
                     {"k": 50, "registros": [["RETROCESO", 3]]},
                     None, [], "texto"):
            with self.subTest(malo=malo):
                with self.assertRaises(VersionIncompatible):
                    RegistroLinea.from_dict(malo)
        RegistroLinea.from_dict(bueno)  # el bueno sigue valiendo

    # ───────────── al escribir: valores inválidos son ValueError ─────────────

    def test_fr022_to_bytes_rechaza_valores_invalidos(self):
        invalidos = [
            RegistroLinea(0, []),
            RegistroLinea(True, []),
            RegistroLinea(50, [(9, 1)]),
            RegistroLinea(50, [(ACCION, "", "", 0, 0)]),
            RegistroLinea(50, [(ACCION, "#x", "", 0, 0)]),
            RegistroLinea(50, [(ACCION, "@cargar", "", 0, 0)]),
            RegistroLinea(50, [(ACCION, "a b", "", 0, 0)]),
            RegistroLinea(50, [(ACCION, "mover", "E\n", 0, 0)]),
            RegistroLinea(50, [(ACCION, "mover", "E", -1, 0)]),
            RegistroLinea(50, [(ACCION, "mover", "E", 0, 2 ** 64)]),
            RegistroLinea(50, [(RETROCESO, -1)]),
            RegistroLinea(50, [(RETROCESO, 1)]),
            RegistroLinea(50, [(CARGA, -5)]),
            RegistroLinea(50, [(ACCION, "mover", "E")]),
            RegistroLinea(50, [(ACCION, 5, "E", 0, 0)]),
        ]
        for registro in invalidos:
            with self.subTest(k=registro.k, registros=registro.registros):
                with self.assertRaises(ValueError):
                    registro.to_bytes()


if __name__ == "__main__":
    unittest.main()
