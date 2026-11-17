import os
import struct
import tempfile
import unittest

from Controlador.ControladorPartida import guardar_motor
from Gestor.PreparadorPartida import cargar_partida
from Persistencia.ArchivoPartida import (guardar_partida, LectorPartida, TAMANO_ENTRADA, FORMATO_ENTRADA)
from Persistencia.ConversorPartida import RestauradorPartida
from Persistencia.FormatoBinario import VersionIncompatible, VERSION_FORMATO, FORMATO_PREFIJO, TAMANO_ENCABEZADO
from Persistencia.RegistroLinea import ACCION, CARGA, RETROCESO, RegistroLinea
from Persistencia.RegistroSala import RegistroSala
from tests.utiles_linea import SesionLinea, archivo_con_linea, bytes_de_linea, insertar_bloque_linea, resumen_ampliado


def crear_sala_prueba(sala_id):
    return RegistroSala(
        sala_id=sala_id,
        rastro=sala_id * 10,
        enemigos=[("e-201", "ent_rata_gigante", 12, 340), ("e-202", "ent_rata_gigante", 7, -1)],
        objetos=[("obj-1", "itm_daga_oxidada"), ("obj-2", "itm_antorcha")],
        trampas=[("t-17", "trp_dardos", True)],
        puertas=[("E", True), ("N", False)],
    )

def crear_sala_vacia(sala_id):
    return RegistroSala(sala_id, -1, [], [], [], [])

def iguales(a, b):
    for campo in RegistroSala.__slots__:
        if getattr(a, campo) != getattr(b, campo):
            return False
    return True

class PruebasRegistroSala(unittest.TestCase):

    def test_persistencia_datos(self): # testea la serialización y deserialización con información
        original = crear_sala_prueba(7)
        self.assertTrue(iguales(original, RegistroSala.from_bytes(original.to_bytes())))

    def test_persistencia_sala_vacia(self): # evalua el caso extremo de una sala vacía
        original = crear_sala_vacia(3)
        self.assertTrue(iguales(original, RegistroSala.from_bytes(original.to_bytes())))

    def test_tipos_datos(self): # conserva tildes y booleanos
        original = RegistroSala(1, 5, [("e-1", "ent_guardián", 3, -1)], [], [("t-1", "trp_ñu", False)], [("O", True)])
        leido = RegistroSala.from_bytes(original.to_bytes())
        self.assertEqual(leido.enemigos[0][1], "ent_guardián")
        self.assertIs(leido.trampas[0][2], False)
        self.assertIs(leido.puertas[0][1], True)

class PruebasArchivoPartida(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "partida.bin")

    def tearDown(self):
        self.carpeta.cleanup()

    def guardar(self, registros):
        guardar_partida(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros)

    def test_encabezado_guardado(self):
        self.guardar([crear_sala_prueba(1), crear_sala_prueba(2)])
        with LectorPartida(self.ruta) as lector:
            self.assertEqual(lector.encabezado.cripta_id, "cripta-01")
            self.assertEqual(lector.encabezado.version_cripta, "a3f91c")
            self.assertEqual(lector.encabezado.version_catalogo, "cat-2026-08-01")
            self.assertEqual(lector.encabezado.semilla, 12345)
            self.assertEqual(lector.encabezado.reloj, 250)
            self.assertEqual(lector.encabezado.cantidad_salas, 2)

    def test_busqueda_desordenada(self): # busqueda desordenada de salas
        ids = [5, 1, 9, 3, 7, 2, 8, 4, 6, 10]
        self.guardar([crear_sala_prueba(i) for i in ids])
        with LectorPartida(self.ruta) as lector:
            for i in ids:
                self.assertTrue(iguales(lector.leer_sala(i), crear_sala_prueba(i)))

    def test_sala_inexistente(self):
        self.guardar([crear_sala_prueba(2), crear_sala_prueba(4)])
        with LectorPartida(self.ruta) as lector:
            self.assertIsNone(lector.leer_sala(1))
            self.assertIsNone(lector.leer_sala(3))
            self.assertIsNone(lector.leer_sala(99))

    def test_partida_sin_salas(self): # para archivos de guardado sin registros
        self.guardar([])
        with LectorPartida(self.ruta) as lector:
            self.assertIsNone(lector.leer_sala(1))

    def test_salas_repetidas(self): # llaves/IDs repetidos
        with self.assertRaises(ValueError):
            self.guardar([crear_sala_prueba(1), crear_sala_prueba(1)])

    def test_lectura_parcial(self): # leer una sala no carga el archivo completo
        self.guardar([crear_sala_prueba(i) for i in range(1, 2001)])
        tamano = os.path.getsize(self.ruta)
        with LectorPartida(self.ruta) as lector:
            antes = lector.bytes_leidos
            self.assertTrue(iguales(lector.leer_sala(1500), crear_sala_prueba(1500)))
            leido = lector.bytes_leidos - antes
        self.assertLess(leido, tamano // 100)
        # la busqueda binaria sobre 2000 entradas hace a lo sumo 11 lecturas del indice
        self.assertLessEqual(leido, 11 * TAMANO_ENTRADA + len(crear_sala_prueba(1500).to_bytes()))

    def test_version_incompatible(self):
        self.guardar([crear_sala_prueba(1)])
        with open(self.ruta, "r+b") as archivo:
            archivo.write(struct.pack(FORMATO_PREFIJO, b"CRPT", VERSION_FORMATO + 1))
        with self.assertRaises(VersionIncompatible):
            LectorPartida(self.ruta)

    def test_archivo_invalido(self):
        with open(self.ruta, "wb") as archivo:
            archivo.write(b'{"no": "soy una partida"}' + bytes(200))
        with self.assertRaises(VersionIncompatible):
            LectorPartida(self.ruta)


    def test_indice_truncado(self):
        self.guardar([crear_sala_prueba(1), crear_sala_prueba(2)])

        with open(self.ruta, "r+b") as archivo:
            archivo.seek(0, os.SEEK_END)
            archivo.truncate(
                os.path.getsize(self.ruta) - 1
            )

        with self.assertRaises(VersionIncompatible):
            LectorPartida(self.ruta)


    def test_leer_todas_salas(self):
        esperadas = [crear_sala_prueba(3), crear_sala_prueba(1),crear_sala_prueba(2),]

        self.guardar(esperadas)

        with LectorPartida(self.ruta) as lector:
            registros = lector.leer_todas_salas()

        self.assertEqual([registro.sala_id for registro in registros], [1, 2, 3])

    def test_leer_todas_rechaza_posicion_invalida(self):
        self.guardar([crear_sala_prueba(1),crear_sala_prueba(2),])

        with LectorPartida(self.ruta) as lector:
            offset = lector.encabezado.offset_indice

        # Se crea una entrada que apunta dentro del índice, en vez de apuntar a un bloque de sala
        with open(self.ruta, "r+b") as archivo:
            archivo.seek(offset)
            archivo.write(
                struct.pack(FORMATO_ENTRADA, 1, offset, 1)
            )

        with LectorPartida(self.ruta) as lector:
            with self.assertRaises(VersionIncompatible):
                lector.leer_todas_salas()

    def test_guardado_invalido_conserva_archivo_anterior(self):
        self.guardar([crear_sala_prueba(1)])

        with open(self.ruta, "rb") as archivo:
            contenido_anterior = archivo.read()

        registro_invalido = RegistroSala(2, 0, [], [("o-1", "x" * 65536)], [], [])

        with self.assertRaises(ValueError):
            self.guardar([registro_invalido])

        with open(self.ruta, "rb") as archivo:
            contenido_actual = archivo.read()

        self.assertEqual(contenido_actual, contenido_anterior)

    def test_registro_truncado(self):
        original = crear_sala_prueba(7)
        datos = original.to_bytes()

        with self.assertRaises(ValueError):
            RegistroSala.from_bytes(datos[:-1])

    def test_registro_con_bytes_sobrantes(self):
        original = crear_sala_prueba(7)
        datos = original.to_bytes() + b"\x00"

        with self.assertRaises(ValueError):
            RegistroSala.from_bytes(datos)

    def test_booleano_invalido_en_puerta(self):
        original = crear_sala_prueba(7)
        datos = bytearray(original.to_bytes())

        # El ultimo byte es el booleano de la ultima puerta.
        datos[-1] = 2

        with self.assertRaises(ValueError):
            RegistroSala.from_bytes(datos)

    def test_rechaza_vida_fuera_de_rango(self):
        sala = RegistroSala(
            1, 0,
            [("e-1", "ent_rata", 2147483648, -1)],
            [], [], []
        )

        with self.assertRaises(ValueError):
            sala.to_bytes()

    def test_rechaza_cadena_demasiado_larga(self):
        sala = RegistroSala(1, 0, [], [("o-1", "x" * 65536)], [], [])

        with self.assertRaises(ValueError):
            sala.to_bytes()


# ───────────────────────── Bloque de la línea de tiempo (spec 004, T065; FR-022, FR-023, FR-024) ─────────────────────────
# Solo lo que cambia con un bloque de línea NO vacío. Lo que ya probó 001-T122 (`offset_indice >= TAMANO_ENCABEZADO + 12` y la
# fórmula de `_inicio_salas` con largos de relleno) está en tests/test_persistencia_conocimiento.py (TestDisposicionCrpt3).

def linea_de_prueba(acciones=3):
    """Un RegistroLinea con `acciones` acciones, un retroceso y una carga."""
    registros = [(ACCION, "mover" if numero % 2 == 0 else "esperar", "E" if numero % 2 == 0 else "", numero * 100, numero)
                 for numero in range(acciones)]
    registros.append((RETROCESO, acciones - 1))
    registros.append((CARGA, acciones * 100))
    return RegistroLinea(50, registros)


class PruebasLineaEnElArchivo(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(self.carpeta.cleanup)
        self.ruta = os.path.join(self.carpeta.name, "con_linea.bin")

    def guardar(self, registros, linea=None, **opciones):
        guardar_partida(self.ruta, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, registros, linea=linea, **opciones)

    def posicion_largo_linea(self, datos):
        posicion = TAMANO_ENCABEZADO
        for _ in range(2):
            (largo,) = struct.unpack_from("<I", datos, posicion)
            posicion += 4 + largo
        return posicion

    def test_fr022_leer_linea_devuelve_el_registro_escrito(self):
        linea = linea_de_prueba()
        self.guardar([crear_sala_prueba(1), crear_sala_prueba(2)], linea)
        with LectorPartida(self.ruta) as lector:
            leida = lector.leer_linea()
        self.assertEqual(leida, linea)
        self.assertEqual(leida.k, 50)

    def test_fr022_con_largo_cero_leer_linea_es_none(self):
        self.guardar([crear_sala_prueba(1)])                       # sin `linea`
        with LectorPartida(self.ruta) as lector:
            self.assertIsNone(lector.leer_linea())
            self.assertEqual(lector._largo_linea, 0)
        self.guardar([crear_sala_prueba(1)], linea=None)
        with LectorPartida(self.ruta) as lector:
            self.assertIsNone(lector.leer_linea())

    def test_fr022_sin_linea_los_bytes_son_los_de_antes(self):
        self.guardar([crear_sala_prueba(1), crear_sala_prueba(2)])
        with open(self.ruta, "rb") as archivo:
            sin = archivo.read()
        self.guardar([crear_sala_prueba(1), crear_sala_prueba(2)], linea=None)
        with open(self.ruta, "rb") as archivo:
            self.assertEqual(archivo.read(), sin)
        self.assertEqual(struct.unpack_from("<I", sin, self.posicion_largo_linea(sin))[0], 0)

    def test_fr022_cualquier_objeto_con_to_bytes_sirve_como_linea(self):
        class Bloque:
            def to_bytes(self):
                return b"\x01\x02\x03"

        self.guardar([crear_sala_prueba(1)], Bloque())
        with LectorPartida(self.ruta) as lector:
            self.assertEqual(lector._largo_linea, 3)
            self.assertEqual(lector._leer(lector._inicio_linea, 3), b"\x01\x02\x03")

    def test_fr023_la_formula_de_inicio_salas_vale_con_largo_de_linea_distinto_de_cero(self):
        linea = linea_de_prueba(10)
        largo = len(linea.to_bytes())
        self.assertGreater(largo, 0)
        self.guardar([crear_sala_prueba(1)], linea)
        with LectorPartida(self.ruta) as lector:
            # sin jugador ni conocimiento: sus largos son 0
            self.assertEqual(lector._inicio_salas, TAMANO_ENCABEZADO + (4 + 0) + (4 + 0) + (4 + largo))
            self.assertEqual(lector._inicio_salas - lector._largo_linea, lector._inicio_linea)
            self.assertEqual(lector._largo_linea, largo)

    def test_fr023_la_formula_vale_con_jugador_conocimiento_y_linea_a_la_vez(self):
        class Bloque:
            def __init__(self, datos):
                self.datos = datos

            def to_bytes(self):
                return self.datos

        linea = linea_de_prueba(4)
        largo = len(linea.to_bytes())
        self.guardar([crear_sala_prueba(1), crear_sala_prueba(2)], linea, jugador=Bloque(b"J" * 7),
                     conocimiento=Bloque(b"C" * 11))
        with LectorPartida(self.ruta) as lector:
            self.assertEqual(lector._inicio_salas, TAMANO_ENCABEZADO + (4 + 7) + (4 + 11) + (4 + largo))
            self.assertEqual(lector.leer_linea(), linea)
            self.assertTrue(iguales(lector.leer_sala(2), crear_sala_prueba(2)))

    def test_fr023_las_salas_se_leen_igual_con_y_sin_linea(self):
        salas = [crear_sala_prueba(i) for i in range(1, 40)]
        self.guardar(salas)
        with LectorPartida(self.ruta) as sin:
            esperado = [registro.to_bytes() for registro in sin.leer_todas_salas()]
        self.guardar(salas, linea_de_prueba(200))
        with LectorPartida(self.ruta) as con:
            self.assertEqual([registro.to_bytes() for registro in con.leer_todas_salas()], esperado)
            for numero in (1, 17, 39):
                self.assertTrue(iguales(con.leer_sala(numero), crear_sala_prueba(numero)))
            self.assertIsNone(con.leer_sala(500))
            self.assertEqual(con.ids_salas(), list(range(1, 40)))

    def test_fr023_bytes_leidos_al_abrir_y_leer_una_sala_no_lee_la_linea(self):
        linea = linea_de_prueba(2000)
        largo = len(linea.to_bytes())
        self.assertGreater(largo, 50000)
        self.guardar([crear_sala_prueba(i) for i in range(1, 200)], linea)
        with LectorPartida(self.ruta) as lector:
            self.assertEqual(lector.bytes_leidos, TAMANO_ENCABEZADO + 12)
            self.assertTrue(iguales(lector.leer_sala(150), crear_sala_prueba(150)))
            leido = lector.bytes_leidos - (TAMANO_ENCABEZADO + 12)
            self.assertLess(leido, largo // 10)         # una sala y el índice, no los ~54 KB de la línea
            antes = lector.bytes_leidos
            lector.leer_linea()
            self.assertEqual(lector.bytes_leidos - antes, largo)   # leer la línea es una sola lectura de su bloque

    def test_fr022_leer_linea_dos_veces_da_lo_mismo(self):
        linea = linea_de_prueba(5)
        self.guardar([crear_sala_prueba(1)], linea)
        with LectorPartida(self.ruta) as lector:
            self.assertEqual(lector.leer_linea(), lector.leer_linea())

    # ───────────── un bloque que no cuadra (código 2) ─────────────

    def test_fr024_un_bloque_de_linea_que_invade_las_salas_se_rechaza(self):
        self.guardar([crear_sala_prueba(1), crear_sala_prueba(2)], linea_de_prueba())
        with open(self.ruta, "rb") as archivo:
            datos = bytearray(archivo.read())
        posicion = self.posicion_largo_linea(datos)
        (largo,) = struct.unpack_from("<I", datos, posicion)
        sala = len(crear_sala_prueba(1).to_bytes())
        for exceso in (1, 20, sala - 1):
            # el bloque se mete en la primera sala sin llegar al índice: abrir no lo ve (solo lee los tres largos), pero
            # la primera sala ya no empieza donde dice el índice y cualquier lectura de salas lo rechaza
            with self.subTest(exceso=exceso):
                malo = bytearray(datos)
                struct.pack_into("<I", malo, posicion, largo + exceso)
                with open(self.ruta, "wb") as archivo:
                    archivo.write(bytes(malo))
                with LectorPartida(self.ruta) as lector:
                    with self.assertRaises(VersionIncompatible):
                        lector.leer_sala(1)
                with LectorPartida(self.ruta) as lector:
                    with self.assertRaises(VersionIncompatible):
                        lector.leer_todas_salas()
        # un bloque que pasa del índice se rechaza al abrir
        for exceso in (2 * sala + 100, 10 ** 6):
            with self.subTest(exceso=exceso):
                malo = bytearray(datos)
                struct.pack_into("<I", malo, posicion, largo + exceso)
                with open(self.ruta, "wb") as archivo:
                    archivo.write(bytes(malo))
                with self.assertRaises(VersionIncompatible):
                    LectorPartida(self.ruta)

    def test_fr024_un_largo_de_linea_enorme_se_rechaza_sin_leer_nada_mas(self):
        self.guardar([crear_sala_prueba(1)], linea_de_prueba())
        with open(self.ruta, "rb") as archivo:
            datos = bytearray(archivo.read())
        struct.pack_into("<I", datos, self.posicion_largo_linea(datos), 0xFFFFFFFF)
        with open(self.ruta, "wb") as archivo:
            archivo.write(bytes(datos))
        with self.assertRaises(VersionIncompatible):
            LectorPartida(self.ruta)

    def test_fr024_un_bloque_de_linea_mas_corto_que_su_largo_deja_las_salas_mal_ubicadas(self):
        # el largo dice 4 bytes menos de los que tiene el bloque: la primera sala ya no empieza donde dice el índice
        self.guardar([crear_sala_prueba(1)], linea_de_prueba())
        with open(self.ruta, "rb") as archivo:
            datos = bytearray(archivo.read())
        posicion = self.posicion_largo_linea(datos)
        (largo,) = struct.unpack_from("<I", datos, posicion)
        struct.pack_into("<I", datos, posicion, largo - 4)
        with open(self.ruta, "wb") as archivo:
            archivo.write(bytes(datos))
        with LectorPartida(self.ruta) as lector:
            with self.assertRaises(VersionIncompatible):
                lector.leer_todas_salas()

    def test_fr024_un_bloque_de_linea_danado_se_rechaza_al_leerlo(self):
        linea = linea_de_prueba()
        for modo in ("truncado", "tipo"):
            with self.subTest(modo=modo):
                origen = os.path.join(self.carpeta.name, "origen.bin")
                guardar_partida(origen, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, [crear_sala_prueba(1)])
                insertar_bloque_linea(origen, self.ruta, bytes_de_linea(linea, modo))
                with LectorPartida(self.ruta) as lector:
                    self.assertTrue(iguales(lector.leer_sala(1), crear_sala_prueba(1)))   # las salas siguen bien
                    with self.assertRaises(VersionIncompatible):
                        lector.leer_linea()

    def test_fr024_la_linea_no_se_valida_hasta_que_se_pide(self):
        origen = os.path.join(self.carpeta.name, "origen.bin")
        guardar_partida(origen, "cripta-01", "a3f91c", "cat-2026-08-01", 12345, 250, [crear_sala_prueba(1)])
        insertar_bloque_linea(origen, self.ruta, b"basura que no es una linea")
        with LectorPartida(self.ruta) as lector:               # abrir y leer salas no la mira
            self.assertTrue(iguales(lector.leer_sala(1), crear_sala_prueba(1)))
            with self.assertRaises(VersionIncompatible):
                lector.leer_linea()


class PruebasLineaConUnaPartidaReal(unittest.TestCase):
    """Salas reales de una partida guardada por el motor, con un bloque de línea no vacío insertado en el archivo: el
    lector, `leer_todas_salas`, `buscar_sala` y `cargar_partida` lo atraviesan sin tocarlo (FR-022, FR-023)."""

    def setUp(self):
        self.sesion = SesionLinea(k=3, semilla=3, huellas=False)
        self.addCleanup(self.sesion.cerrar)
        self.sesion.jugar(8)
        base = self.sesion.partida.carpeta.name
        self.sin_linea = os.path.join(base, "sin_linea.cripta")
        self.con_linea = os.path.join(base, "con_linea.cripta")
        guardar_motor(self.sesion.motor, self.sin_linea, self.sesion.partida.gestor)
        self.linea = self.sesion.linea.a_registro()
        archivo_con_linea(self.sin_linea, self.con_linea, self.linea)

    def test_fr023_leer_todas_las_salas_y_buscar_cada_una(self):
        with LectorPartida(self.sin_linea) as sin, LectorPartida(self.con_linea) as con:
            self.assertGreater(len(con.ids_salas()), 1)
            self.assertEqual(con.ids_salas(), sin.ids_salas())
            self.assertEqual([r.to_bytes() for r in con.leer_todas_salas()], [r.to_bytes() for r in sin.leer_todas_salas()])
            for id_sala in con.ids_salas():
                self.assertEqual(con.leer_sala(id_sala).to_bytes(), sin.leer_sala(id_sala).to_bytes())
            self.assertEqual(con.leer_linea(), self.linea)
            self.assertIsNone(sin.leer_linea())

    def test_fr023_cargar_partida_con_linea_da_el_mismo_motor(self):
        motor_sin = cargar_partida(self.sin_linea, self.sesion.partida.nuevo_gestor(iniciado=False))
        motor_con = cargar_partida(self.con_linea, self.sesion.partida.nuevo_gestor(iniciado=False))
        self.addCleanup(motor_sin.restaurador.cerrar)
        self.addCleanup(motor_con.restaurador.cerrar)
        self.assertEqual(resumen_ampliado(motor_con), resumen_ampliado(motor_sin))
        self.assertEqual(motor_con.reloj, self.sesion.motor.reloj)

    def test_fr022_el_restaurador_expone_leer_linea(self):
        restaurador = RestauradorPartida(self.con_linea)
        self.addCleanup(restaurador.cerrar)
        self.assertEqual(restaurador.leer_linea(), self.linea)
        sin = RestauradorPartida(self.sin_linea)
        self.addCleanup(sin.cerrar)
        self.assertIsNone(sin.leer_linea())

    def test_fr024_cargar_un_archivo_cuya_linea_invade_las_salas_es_version_incompatible(self):
        with open(self.con_linea, "rb") as archivo:
            datos = bytearray(archivo.read())
        posicion = TAMANO_ENCABEZADO
        for _ in range(2):
            (largo,) = struct.unpack_from("<I", datos, posicion)
            posicion += 4 + largo
        struct.pack_into("<I", datos, posicion, len(datos))
        invadido = os.path.join(self.sesion.partida.carpeta.name, "invadido.cripta")
        with open(invadido, "wb") as archivo:
            archivo.write(bytes(datos))
        with self.assertRaises(VersionIncompatible):
            cargar_partida(invadido, self.sesion.partida.nuevo_gestor(iniciado=False))


if __name__ == "__main__":
    unittest.main()