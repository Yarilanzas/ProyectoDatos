# pruebas de la tabla de puntajes (S2.12) de persona D: archivo de texto, orden con los algoritmos propios
# y registro automatico al terminar una partida detras del controlador

import contextlib
import io
import os
import tempfile
import unittest
import unittest.mock

import main
from Controlador.ControladorPartida import ControladorPartida
from Persistencia.TablaPuntajes import Puntaje, TablaPuntajes
from tests.test_integracion import BaseIntegracion, CRIPTA, VistaFalsa

# recoge la daga y la llave, mata a las dos ratas, abre la puerta de la salida y entra: victoria
COMANDOS_VICTORIA = [
    f"recoger obj-{CRIPTA}-1-itm_daga-0",
    f"equipar obj-{CRIPTA}-1-itm_daga-0",
    "e",
    "atacar e-rata-1",
    f"recoger obj-{CRIPTA}-2-itm_llave_salida-0",
    "e",
    "atacar e-rata-2",
    "abrir E",
    "e",
]


def puntaje(nombre, acciones, derrotados=0, tiempo=100, resultado="victoria"):
    return Puntaje(nombre, "cripta-01", "a3f91c", acciones, derrotados, tiempo, resultado)


class VistaGuionada(VistaFalsa):
    # entrega los comandos uno por uno y contesta el nombre cuando se lo piden; despues simula el fin de la entrada
    def __init__(self, comandos, nombre="Ana"):
        super().__init__()
        self.comandos = list(comandos)
        self.nombre = nombre

    def pedir_texto(self, mensaje):
        return self.nombre

    def pedir_comando(self):
        return self.comandos.pop(0) if self.comandos else None

    def llamadas(self, nombre):
        return [argumentos for llamada, argumentos in self.lineas if llamada == nombre]


class PruebasTablaPuntajes(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "puntajes.txt")
        self.tabla = TablaPuntajes(self.ruta)

    def tearDown(self):
        self.carpeta.cleanup()

    def test_tabla_inexistente_esta_vacia(self):
        self.assertEqual(self.tabla.leer(), [])
        self.assertEqual(self.tabla.ordenados(), [])

    def test_registra_y_lee_todos_los_campos_con_tildes(self):
        self.tabla.registrar(puntaje("Ñoño Pérez", 40, 3, 1234))
        leido = self.tabla.leer()[0]
        self.assertEqual((leido.nombre, leido.cripta_id, leido.version_cripta, leido.acciones,
                          leido.derrotados, leido.tiempo, leido.resultado),
                         ("Ñoño Pérez", "cripta-01", "a3f91c", 40, 3, 1234, "victoria"))

    def test_solo_agrega_al_final(self):
        self.tabla.registrar(puntaje("A", 1))
        self.tabla.registrar(puntaje("B", 2))
        self.assertEqual([p.nombre for p in self.tabla.leer()], ["A", "B"])
        with open(self.ruta, encoding="utf-8") as archivo:
            self.assertEqual(len(archivo.readlines()), 2)

    def test_nombre_con_tabulador_o_vacio(self):
        self.assertEqual(puntaje("A\tB\nC", 1).nombre, "A B C")
        self.assertEqual(puntaje("   ", 1).nombre, "Anónimo")
        self.assertEqual(puntaje(None, 1).nombre, "Anónimo")

    def test_desde_resumen(self):
        resumen = {"resultado": "derrota", "acciones": 7, "enemigos_derrotados": 2, "tiempo_final": 640}
        p = Puntaje.desde_resumen("Ana", "cripta-02", "v9", resumen)
        self.assertEqual((p.acciones, p.derrotados, p.tiempo, p.resultado), (7, 2, 640, "derrota"))

    def test_mejores_pone_primero_las_victorias_y_luego_menos_acciones(self):
        self.tabla.registrar(puntaje("derrota rapida", 2, resultado="derrota"))
        self.tabla.registrar(puntaje("lenta", 30))
        self.tabla.registrar(puntaje("rapida", 10))
        self.assertEqual([p.nombre for p in self.tabla.ordenados("mejores")], ["rapida", "lenta", "derrota rapida"])

    def test_mejores_desempata_por_tiempo(self):
        self.tabla.registrar(puntaje("A", 10, tiempo=900))
        self.tabla.registrar(puntaje("B", 10, tiempo=500))
        self.assertEqual([p.nombre for p in self.tabla.ordenados()], ["B", "A"])

    def test_orden_por_cada_criterio(self):
        for nombre, acciones, derrotados, tiempo in (("c", 30, 1, 300), ("a", 10, 5, 900), ("B", 20, 3, 100)):
            self.tabla.registrar(puntaje(nombre, acciones, derrotados, tiempo))
        nombres = lambda criterio: [p.nombre for p in self.tabla.ordenados(criterio)]
        self.assertEqual(nombres("acciones"), ["a", "B", "c"])
        self.assertEqual(nombres("tiempo"), ["B", "c", "a"])
        self.assertEqual(nombres("derrotados"), ["a", "B", "c"])
        self.assertEqual(nombres("nombre"), ["a", "B", "c"])  # sin distinguir mayusculas

    def test_orden_con_muchos_puntajes_usa_el_algoritmo_grande(self):
        for i in range(100):
            self.tabla.registrar(puntaje(f"j{i:03d}", (i * 37) % 100))
        acciones = [p.acciones for p in self.tabla.ordenados("acciones")]
        self.assertEqual(acciones, list(range(100)))

    def test_ordenar_no_modifica_el_archivo(self):
        self.tabla.registrar(puntaje("A", 30))
        self.tabla.registrar(puntaje("B", 10))
        self.tabla.ordenados("acciones")
        self.assertEqual([p.nombre for p in self.tabla.leer()], ["A", "B"])

    def test_criterio_desconocido(self):
        with self.assertRaises(ValueError):
            self.tabla.ordenados("magia")

    def test_linea_danada_indica_el_numero_de_linea(self):
        self.tabla.registrar(puntaje("A", 1))
        with open(self.ruta, "a", encoding="utf-8") as archivo:
            archivo.write("esto no es un puntaje\n")
        with self.assertRaises(ValueError) as contexto:
            self.tabla.leer()
        self.assertIn("línea 2", str(contexto.exception))


class PruebasRegistroAlTerminar(BaseIntegracion):

    def setUp(self):
        super().setUp()
        self.ruta_puntajes = os.path.join(self.carpeta.name, "puntajes.txt")

    def jugar_hasta_el_final(self, comandos, nombre="Ana", ruta_puntajes="usar"):
        ruta = self.ruta_puntajes if ruta_puntajes == "usar" else ruta_puntajes
        vista = VistaGuionada(comandos, nombre)
        controlador = ControladorPartida(self.nuevo_gestor(), vista, self.ruta_log, ruta)
        controlador.nueva_partida(CRIPTA, 7)
        controlador.jugar()
        return controlador, vista

    def test_una_victoria_queda_registrada(self):
        _, vista = self.jugar_hasta_el_final(COMANDOS_VICTORIA)
        puntajes = TablaPuntajes(self.ruta_puntajes).leer()
        self.assertEqual(len(puntajes), 1)
        p = puntajes[0]
        self.assertEqual((p.nombre, p.cripta_id, p.version_cripta, p.resultado), ("Ana", CRIPTA, "v1", "victoria"))
        self.assertEqual((p.acciones, p.derrotados), (len(COMANDOS_VICTORIA), 2))
        self.assertGreater(p.tiempo, 0)
        self.assertTrue(vista.llamadas("mostrar_puntajes"))

    def test_una_derrota_queda_registrada(self):
        self.jugar_hasta_el_final(["e"] + ["esperar"] * 200)
        p = TablaPuntajes(self.ruta_puntajes).leer()[0]
        self.assertEqual(p.resultado, "derrota")
        self.assertGreater(p.acciones, 1)

    def test_las_partidas_se_acumulan(self):
        self.jugar_hasta_el_final(COMANDOS_VICTORIA, "Ana")
        self.jugar_hasta_el_final(COMANDOS_VICTORIA, "Beto")
        self.assertEqual([p.nombre for p in TablaPuntajes(self.ruta_puntajes).leer()], ["Ana", "Beto"])

    def test_salir_sin_terminar_no_registra(self):
        self.jugar_hasta_el_final(["e", "salir"])
        self.assertEqual(TablaPuntajes(self.ruta_puntajes).leer(), [])

    def test_sin_nombre_se_registra_como_anonimo(self):
        self.jugar_hasta_el_final(COMANDOS_VICTORIA, nombre="")
        self.assertEqual(TablaPuntajes(self.ruta_puntajes).leer()[0].nombre, "Anónimo")

    def test_sin_ruta_de_puntajes_no_se_escribe_nada(self):
        _, vista = self.jugar_hasta_el_final(COMANDOS_VICTORIA, ruta_puntajes=None)
        self.assertFalse(os.path.exists(self.ruta_puntajes))
        self.assertEqual(vista.llamadas("mostrar_puntajes"), [])

    def test_si_no_se_puede_escribir_la_partida_no_se_cae(self):
        _, vista = self.jugar_hasta_el_final(COMANDOS_VICTORIA, ruta_puntajes=self.carpeta.name)  # una carpeta, no un archivo
        self.assertTrue(vista.llamadas("mostrar_error"))

    def test_comando_puntajes_dentro_de_la_partida(self):
        self.jugar_hasta_el_final(COMANDOS_VICTORIA)
        _, vista = self.jugar_hasta_el_final(["puntajes", "puntajes tiempo", "puntajes magia", "salir"])
        mostrados = vista.llamadas("mostrar_puntajes")
        self.assertEqual([argumentos[1] for argumentos in mostrados], ["mejores", "tiempo"])
        self.assertEqual(len(mostrados[0][0]), 1)
        self.assertTrue(vista.llamadas("mostrar_error"))  # criterio desconocido

    def test_la_tabla_muestra_como_maximo_diez(self):
        tabla = TablaPuntajes(self.ruta_puntajes)
        for i in range(15):
            tabla.registrar(puntaje(f"j{i}", i))
        _, vista = self.jugar_hasta_el_final(["puntajes", "salir"])
        self.assertEqual(len(vista.llamadas("mostrar_puntajes")[0][0]), 10)

    def test_replay_no_registra_puntajes(self):
        self.jugar_hasta_el_final(COMANDOS_VICTORIA)
        antes = TablaPuntajes(self.ruta_puntajes).leer()
        main.ejecutar_replay(self.ruta_log, self.nuevo_gestor(), VistaFalsa())
        self.assertEqual(len(TablaPuntajes(self.ruta_puntajes).leer()), len(antes))


class PruebasMain(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "puntajes.txt")

    def tearDown(self):
        self.carpeta.cleanup()

    def correr(self, *argumentos):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida), unittest.mock.patch("sys.argv", ["main.py", *argumentos]):
            codigo = main.main()
        return codigo, salida.getvalue()

    def test_mostrar_puntajes_sin_tabla(self):
        codigo, texto = self.correr("--mostrar-puntajes", "--puntajes", self.ruta)
        self.assertEqual(codigo, 0)
        self.assertIn("Todavía no hay partidas registradas", texto)

    def test_mostrar_puntajes_ordenados(self):
        tabla = TablaPuntajes(self.ruta)
        tabla.registrar(puntaje("lenta", 30))
        tabla.registrar(puntaje("rapida", 10))
        codigo, texto = self.correr("--mostrar-puntajes", "acciones", "--puntajes", self.ruta)
        self.assertEqual(codigo, 0)
        self.assertLess(texto.index("rapida"), texto.index("lenta"))

    def test_mostrar_puntajes_con_tabla_danada(self):
        with open(self.ruta, "w", encoding="utf-8") as archivo:
            archivo.write("basura\n")
        codigo, texto = self.correr("--mostrar-puntajes", "--puntajes", self.ruta)
        self.assertEqual(codigo, 1)
        self.assertIn("Error", texto)


if __name__ == "__main__":
    unittest.main()
