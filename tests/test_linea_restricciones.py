# Restricciones de la capacidad 004 (spec 004, T119 y T120; FR-019, FR-020, FR-021, FR-024, SC-009).
#
# T119 (Principio I): lee el código fuente de los archivos nuevos de producción y falla si aparece `bisect`, `heapq`,
#      `collections`, `networkx`, `sorted(`, `.sort(`, o un `dict` o `set` (llamada o literal). La única excepción es el `memo`
#      de `copy.deepcopy` en `Modelo/CopiaEstado.py` (autorizada por el profesor el 2026-11-12, T003), y la representación JSON de
#      `RegistroLinea.to_dict`, que la constitución permite como uso auxiliar. Se lee el árbol sintáctico: un nombre dentro de un
#      comentario o de un texto no cuenta.
# T120: ninguna prueba de la capacidad nombra los archivos de ejemplo de la Parte I, y correr el controlador y `main` con las
#      rutas de `partida_linea` no crea nada de eso en la raíz del repositorio ni en el directorio actual.

import ast
import contextlib
import io
import os
import sys
import unittest
from unittest import mock

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Controlador.ControladorPartida import ruta_bitacora_de
from Vista.VistaConsola import VistaConsola
from tests.utiles_linea import partida_linea

# Los archivos nuevos de producción de la capacidad (plan.md#project-structure).
ARCHIVOS_DE_PRODUCCION = (
    "Modelo/AgendaConCorte.py",
    "Modelo/BusquedaBinaria.py",
    "Modelo/CopiaEstado.py",
    "Modelo/LineaTiempo.py",
    "Modelo/PuntoControl.py",
    "Modelo/ResumenHistorico.py",
    "DTOS/ResumenHistorico.py",
    "Gestor/GestorHistorico.py",
    "Persistencia/RegistroLinea.py",
    "Controlador/ObservadorLinea.py",
    "Controlador/ReconstructorLinea.py",
    "Controlador/ConsultaHistoria.py",
    "Vista/TextoResumen.py",
)

MODULOS_PROHIBIDOS = ("bisect", "heapq", "collections", "networkx")
LLAMADAS_PROHIBIDAS = ("sorted", "dict", "set", "frozenset", "defaultdict", "OrderedDict", "Counter", "deque")

# Excepciones por nombre: (archivo, qué se permite)
ARCHIVO_DEL_MEMO = "Modelo/CopiaEstado.py"
FUNCION_JSON = ("Persistencia/RegistroLinea.py", "to_dict")   # el diccionario del JSON de salida

# Los archivos de la Parte I (partida de ejemplo y bitácoras) que ninguna prueba puede usar. Se arman por partes: este
# archivo también lo lee T120 y no debe nombrarlos.
NOMBRES_PROHIBIDOS = ("partida" + ".cripta.log", "partida" + ".cripta", "partida" + ".log")


def _nodos_permitidos(arbol, archivo):
    """Ids de los nodos que son excepción por nombre en `archivo`."""
    permitidos = []
    for nodo in ast.walk(arbol):
        if archivo == ARCHIVO_DEL_MEMO and isinstance(nodo, ast.Assign):
            if (len(nodo.targets) == 1 and isinstance(nodo.targets[0], ast.Name) and nodo.targets[0].id == "memo"
                    and isinstance(nodo.value, ast.Dict)):
                permitidos.append(id(nodo.value))
        if archivo == FUNCION_JSON[0] and isinstance(nodo, ast.FunctionDef) and nodo.name == FUNCION_JSON[1]:
            for interno in ast.walk(nodo):
                permitidos.append(id(interno))
    return permitidos


def hallazgos(codigo, archivo="<prueba>"):
    """Lista de textos con lo prohibido que hay en `codigo` (vacía si cumple el Principio I)."""
    arbol = ast.parse(codigo)
    permitidos = _nodos_permitidos(arbol, archivo)
    problemas = []
    for nodo in ast.walk(arbol):
        donde = f"{archivo}:{getattr(nodo, 'lineno', '?')}"
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name.split(".")[0] in MODULOS_PROHIBIDOS:
                    problemas.append(f"{donde}: import {alias.name}")
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.module is not None and nodo.module.split(".")[0] in MODULOS_PROHIBIDOS:
                problemas.append(f"{donde}: from {nodo.module} import ...")
        elif isinstance(nodo, ast.Call):
            funcion = nodo.func
            if isinstance(funcion, ast.Name) and funcion.id in LLAMADAS_PROHIBIDAS:
                problemas.append(f"{donde}: {funcion.id}(...)")
            if isinstance(funcion, ast.Attribute) and funcion.attr == "sort":
                problemas.append(f"{donde}: .sort(...)")
        elif isinstance(nodo, (ast.Dict, ast.Set, ast.DictComp, ast.SetComp)):
            if id(nodo) not in permitidos:
                problemas.append(f"{donde}: {type(nodo).__name__} como literal o comprensión")
        elif isinstance(nodo, ast.Name) and nodo.id in MODULOS_PROHIBIDOS:
            problemas.append(f"{donde}: uso de {nodo.id}")
    return problemas


def leer(ruta_relativa):
    with open(os.path.join(RAIZ, ruta_relativa), encoding="utf-8") as archivo:
        return archivo.read()


class PruebasRestriccionesDeProduccion(unittest.TestCase):
    """T119."""

    def test_fr019_fr020_fr021_los_archivos_nuevos_cumplen_el_principio_i(self):
        for ruta in ARCHIVOS_DE_PRODUCCION:
            with self.subTest(archivo=ruta):
                self.assertEqual(hallazgos(leer(ruta), ruta), [])

    def test_fr021_todos_los_archivos_existen(self):
        for ruta in ARCHIVOS_DE_PRODUCCION:
            with self.subTest(archivo=ruta):
                self.assertTrue(os.path.isfile(os.path.join(RAIZ, ruta)))

    def test_fr021_la_prueba_detecta_cada_construccion_prohibida(self):
        prohibidos = [
            "import bisect", "import heapq", "import collections", "from collections import deque", "import networkx",
            "from heapq import heappush", "x = sorted(y)", "y.sort()", "y.sort(key=len)", "d = dict()", "s = set()",
            "d = {}", "d = {1: 2}", "s = {1, 2}", "d = {k: v for k, v in z}", "s = {k for k in z}", "f = frozenset(z)",
            "d = defaultdict(list)", "c = Counter(z)", "q = deque()", "bisect.bisect(a, 1)",
        ]
        for codigo in prohibidos:
            with self.subTest(codigo=codigo):
                self.assertNotEqual(hallazgos(codigo), [], codigo)

    def test_fr021_la_prueba_deja_pasar_lo_permitido(self):
        permitidos = [
            "x = [1, 2, 3]", "t = (1, 2)", "# sorted(x) en un comentario", 'texto = "dict() y set() en un texto"',
            "for clave, valor in sala.salidas.items():\n    pass", "y = sala.salidas['N']", "y = list(range(4))",
            '"""sorted( en un docstring"""',
        ]
        for codigo in permitidos:
            with self.subTest(codigo=codigo):
                self.assertEqual(hallazgos(codigo), [], codigo)

    def test_fr021_la_unica_excepcion_es_el_memo_de_copia_estado(self):
        memo = "def f():\n    memo = {}\n    return memo\n"
        self.assertEqual(hallazgos(memo, ARCHIVO_DEL_MEMO), [])
        self.assertNotEqual(hallazgos(memo, "Modelo/LineaTiempo.py"), [])
        otro = "def f():\n    indice = {}\n    return indice\n"
        self.assertNotEqual(hallazgos(otro, ARCHIVO_DEL_MEMO), [])
        self.assertNotEqual(hallazgos("memo = {}\nsorted(x)\n", ARCHIVO_DEL_MEMO), [])

    def test_fr021_el_memo_de_copia_estado_es_solo_el_de_deepcopy_y_esta_documentado(self):
        codigo = leer(ARCHIVO_DEL_MEMO)
        arbol = ast.parse(codigo)
        asignaciones = [nodo for nodo in ast.walk(arbol) if isinstance(nodo, ast.Assign)
                        and isinstance(nodo.value, ast.Dict) and isinstance(nodo.targets[0], ast.Name)]
        self.assertEqual([nodo.targets[0].id for nodo in asignaciones], ["memo", "memo"])      # copiar y materializar
        self.assertIn("2026-11-12", codigo)                                                      # la autorización
        self.assertIn("`memo`", codigo)

    def test_fr021_el_diccionario_del_json_es_solo_el_de_to_dict_de_registro_linea(self):
        otro = "def a():\n    return {'k': 1}\n"
        self.assertEqual(len(hallazgos(otro, FUNCION_JSON[0])), 1)
        permitido = "class R:\n    def to_dict(self):\n        return {'k': 1}\n"
        self.assertEqual(hallazgos(permitido, FUNCION_JSON[0]), [])
        self.assertNotEqual(hallazgos(permitido, "Modelo/LineaTiempo.py"), [])


def estado_de(ruta):
    """(existe, tamaño, instante de modificación) de un archivo; (False, 0, 0) si no existe."""
    if not os.path.exists(ruta):
        return (False, 0, 0)
    datos = os.stat(ruta)
    return (True, datos.st_size, datos.st_mtime_ns)


class PruebasSinArchivosDeLaParteI(unittest.TestCase):
    """T120."""

    def archivos_de_prueba(self):
        carpeta = os.path.join(RAIZ, "tests")
        rutas = []
        for nombre in os.listdir(carpeta):
            if (nombre.startswith("test_linea_") and nombre.endswith(".py")) or nombre in ("test_cli_historia.py",
                                                                                          "utiles_linea.py"):
                rutas.append(os.path.join(carpeta, nombre))
        return rutas

    def test_fr024_sc009_ninguna_prueba_de_la_capacidad_nombra_los_archivos_de_la_parte_i(self):
        rutas = self.archivos_de_prueba()
        self.assertGreater(len(rutas), 10)
        self.assertIn(os.path.join(RAIZ, "tests", "utiles_linea.py"), rutas)
        self.assertIn(os.path.join(RAIZ, "tests", "test_linea_restricciones.py"), rutas)
        for ruta in rutas:
            with open(ruta, encoding="utf-8") as archivo:
                texto = archivo.read()
            for nombre in NOMBRES_PROHIBIDOS:
                with self.subTest(archivo=os.path.basename(ruta), nombre=nombre):
                    self.assertNotIn(nombre, texto)

    def test_fr024_la_busqueda_encuentra_un_nombre_prohibido(self):
        self.assertIn(NOMBRES_PROHIBIDOS[2], f"abrir {NOMBRES_PROHIBIDOS[2]} aquí")
        self.assertEqual(len(NOMBRES_PROHIBIDOS), 3)

    def sitios(self):
        """Dónde no puede aparecer nada: la raíz del repositorio y el directorio actual."""
        directorios = [RAIZ]
        if os.path.abspath(os.getcwd()) != RAIZ:
            directorios.append(os.path.abspath(os.getcwd()))
        return [os.path.join(directorio, nombre) for directorio in directorios for nombre in NOMBRES_PROHIBIDOS]

    def test_fr024_sc009_el_controlador_y_main_con_las_rutas_de_partida_linea_no_crean_nada_en_la_raiz(self):
        import main
        antes = [(ruta, estado_de(ruta)) for ruta in self.sitios()]

        partida = partida_linea()
        self.addCleanup(partida.cerrar)
        controlador = partida.controlador
        for comando in ("esperar", "mover E", "esperar"):
            controlador.ejecutar(comando)
        guardado = os.path.join(partida.carpeta.name, "guardado.cripta")
        self.assertTrue(controlador.guardar(guardado))
        controlador._cerrar()
        copia = ruta_bitacora_de(guardado)
        self.assertTrue(os.path.isfile(copia))

        def sin_entrada(_mensaje):
            raise EOFError

        base = ["main.py", "--offline", partida.paquete, "--datos-locales", partida.ruta_datos]
        corridas = (
            base + ["--replay", partida.ruta_bitacora],
            base + ["--puntajes", os.path.join(partida.carpeta.name, "puntajes.txt"),
                    "--cargar", guardado, "--bitacora", os.path.join(partida.carpeta.name, "continuacion.log")],
        )
        for argumentos in corridas:
            with self.subTest(argumentos=argumentos[5:]):
                salida = io.StringIO()
                with mock.patch.object(main, "VistaConsola", lambda: VistaConsola(entrada=sin_entrada)), \
                        mock.patch.object(main, "configurar_logging", lambda *a, **k: None), \
                        mock.patch.object(sys, "argv", argumentos), contextlib.redirect_stdout(salida):
                    codigo = main.main()
                self.assertEqual(codigo, 0, salida.getvalue())

        despues = [(ruta, estado_de(ruta)) for ruta in self.sitios()]
        self.assertEqual(despues, antes, "algo creó o modificó un archivo de la Parte I en la raíz o en el directorio actual")


if __name__ == "__main__":
    unittest.main()
