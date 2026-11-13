# Pruebas de invalidación por puertas y ciclos del motor (spec 003, T015; T016 y T017 las hacen pasar).
#
# Contadores del motor (enteros que empiezan en 0 al construir el MotorSimulacion y solo crecen):
#   motor.version_puertas   crece cada vez que cambia Salida.cerrada: cierre automático, abrir, y el deshacer de
#                           cada uno. Nunca decrece, ni al deshacer (FR-016, FR-031).
#   motor.ciclo             crece en 1 al empezar cada ciclo de eventos (avanzar_hasta_jugador). No se guarda, no entra
#                           en la bitácora y el deshacer no lo cambia (FR-016, FR-024).
#
# Método único de escritura de puertas (T016):
#   MotorSimulacion._escribir_cerrada(salida, cerrada, descripcion="puerta", registrar=True)
# Es el único lugar de Modelo/ que escribe Salida.cerrada; su deshacer se llama a sí mismo, así que deshacer también
# incrementa version_puertas. La prueba de código fuente (TestFuenteUnicoEscritor) lo comprueba.

import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import ast
import unittest

from Modelo.MotorSimulacion import MotorSimulacion
from tests.utiles_terreno import mapa_a_mano

DIR_MODELO = os.path.join(RAIZ, "Modelo")
METODO_UNICO = "_escribir_cerrada"
ARCHIVO_MOTOR = "MotorSimulacion.py"
CLASE_MOTOR = "MotorSimulacion"

# Archivos de Modelo/ excluidos por nombre de la prueba de código fuente, con su motivo:
EXCLUIDOS = (
    # Pruebas manuales de la Parte I que arman salas a mano: no son código del juego y no corren dentro de un motor.
    "prueba_actores.py",
    # Capacidad 004 (contracts/interfaz-cazador-linea.md §5): Modelo/CopiaEstado.py escribe Salida.cerrada solo sobre
    # las salidas de la COPIA del esqueleto que arma `materializar`, nunca sobre las del motor en juego, y fuera de un
    # ciclo de eventos: no puede dejar desactualizado el version_puertas de la partida real. Es la restauración de una
    # foto, no una escritura de juego. Usar el método único ahí incrementaría el version_puertas del clon sin que haya
    # pasado nada y registraría deshacer que nadie usará. La exclusión es por nombre: cualquier otro archivo nuevo de
    # Modelo/ que escriba `cerrada` sigue haciendo fallar la prueba.
    "CopiaEstado.py",
)

# Sala 1: E→2 cerrada sin llave (se abre con «abrir E»), N→3 abierta (se cierra con un evento CERRAR_PUERTA).
# No hay salida S ni O: «mover S» choca contra una pared.
MAPA = [
    (1, [("E", 2, None, True), ("N", 3, None, False)]),
    (2, [("O", 1, None, False)]),
    (3, [("S", 1, None, False)]),
]


def motor_de_prueba():
    return mapa_a_mano(MAPA, sala_jugador=1)


def salida_de(motor, id_sala, direccion):
    for sala in motor.salas:
        if sala.id == id_sala:
            return sala.salidas[direccion]
    raise ValueError(f"La sala {id_sala!r} no existe")


def cerrar_con_evento(motor, salida):
    """Agenda un cierre automático a 100 ticks y espera: el cierre (secuencia menor) corre antes del turno del
    jugador, que vuelve en reloj + 100 (velocidad 100, costo 100)."""
    motor.programar_evento(motor.reloj + 100, "CERRAR_PUERTA", salida)
    return motor.ejecutar_accion("esperar", None)


class TestContadoresIniciales(unittest.TestCase):
    def test_fr016_contadores_empiezan_en_cero(self):
        """FR-016: version_puertas y ciclo son enteros que valen 0 al construir el MotorSimulacion."""
        motor = MotorSimulacion(semilla=1)
        self.assertEqual(motor.version_puertas, 0)
        self.assertEqual(motor.ciclo, 0)
        self.assertIsInstance(motor.version_puertas, int)
        self.assertIsInstance(motor.ciclo, int)


class TestVersionPuertas(unittest.TestCase):
    def test_fr016_fr031_abrir_incrementa_version_puertas(self):
        """FR-016, FR-031: abrir una puerta cerrada (abrir E) la deja abierta y sube version_puertas en 1."""
        motor = motor_de_prueba()
        este = salida_de(motor, 1, "E")
        antes = motor.version_puertas

        self.assertTrue(motor.ejecutar_accion("abrir", "E"))
        self.assertFalse(este.cerrada)
        self.assertEqual(motor.version_puertas, antes + 1)

    def test_fr016_fr031_cierre_automatico_incrementa_version_puertas(self):
        """FR-016, FR-031: el evento CERRAR_PUERTA sobre una puerta abierta la cierra y sube version_puertas en 1."""
        motor = motor_de_prueba()
        norte = salida_de(motor, 1, "N")
        antes = motor.version_puertas

        self.assertTrue(cerrar_con_evento(motor, norte))
        self.assertTrue(norte.cerrada)
        self.assertEqual(motor.version_puertas, antes + 1)

    def test_fr016_cierre_de_puerta_ya_cerrada_no_cambia_version(self):
        """FR-016: CERRAR_PUERTA sobre una puerta que ya estaba cerrada no la cambia ni sube version_puertas."""
        motor = motor_de_prueba()
        este = salida_de(motor, 1, "E")
        antes = motor.version_puertas

        self.assertTrue(cerrar_con_evento(motor, este))
        self.assertTrue(este.cerrada)
        self.assertEqual(motor.version_puertas, antes)

    def test_fr016_fr031_deshacer_restaura_puerta_y_version_nunca_baja(self):
        """FR-016, FR-031: deshacer el cierre automático y la apertura restaura cada puerta y sube version_puertas en
        1 cada vez; en toda la secuencia el contador nunca baja."""
        motor = motor_de_prueba()
        este = salida_de(motor, 1, "E")
        norte = salida_de(motor, 1, "N")
        valores = [motor.version_puertas]

        def paso(esperado_delta, mensaje):
            actual = motor.version_puertas
            self.assertGreaterEqual(actual, valores[-1], f"version_puertas bajó: {mensaje}")
            self.assertEqual(actual, valores[-1] + esperado_delta, mensaje)
            valores.append(actual)

        self.assertTrue(motor.ejecutar_accion("abrir", "E"))
        self.assertFalse(este.cerrada)
        paso(1, "abrir E")

        self.assertTrue(cerrar_con_evento(motor, norte))
        self.assertTrue(norte.cerrada)
        paso(1, "cierre automático de N")

        self.assertTrue(motor.historial.deshacer_ultimo())
        self.assertFalse(norte.cerrada, "deshacer no reabrió N")
        self.assertFalse(este.cerrada, "deshacer el cierre de N tocó E")
        paso(1, "deshacer el cierre de N")

        self.assertTrue(motor.historial.deshacer_ultimo())
        self.assertTrue(este.cerrada, "deshacer no volvió a cerrar E")
        self.assertFalse(norte.cerrada)
        paso(1, "deshacer la apertura de E")

        for anterior, siguiente in zip(valores, valores[1:]):
            self.assertLess(anterior, siguiente)


class TestCiclo(unittest.TestCase):
    def test_fr016_fr024_ciclo_crece_con_cada_accion_y_no_con_deshacer(self):
        """FR-016, FR-024: ciclo crece en 1 con cada acción del jugador que avanza el reloj; deshacer no lo cambia."""
        motor = motor_de_prueba()

        for nombre, argumento in (("esperar", None), ("mover", "N"), ("esperar", None), ("mover", "S")):
            antes_ciclo, antes_reloj = motor.ciclo, motor.reloj
            self.assertTrue(motor.ejecutar_accion(nombre, argumento), f"{nombre} {argumento} fue rechazada")
            self.assertGreater(motor.reloj, antes_reloj)
            self.assertEqual(motor.ciclo, antes_ciclo + 1, f"{nombre} {argumento}")

        antes = motor.ciclo
        self.assertTrue(motor.historial.deshacer_ultimo())
        self.assertEqual(motor.ciclo, antes, "deshacer cambió ciclo")
        self.assertTrue(motor.historial.deshacer_ultimo())
        self.assertEqual(motor.ciclo, antes, "deshacer cambió ciclo")

    def test_fr016_fr024_comando_rechazado_no_cambia_contadores(self):
        """FR-016, FR-024: un comando rechazado (mover contra una pared o por una puerta cerrada) no cambia ciclo
        ni version_puertas."""
        motor = motor_de_prueba()
        for direccion in ("S", "O", "E"):
            antes = (motor.ciclo, motor.version_puertas, motor.reloj)
            self.assertFalse(motor.ejecutar_accion("mover", direccion))
            self.assertEqual((motor.ciclo, motor.version_puertas, motor.reloj), antes, f"mover {direccion}")

    def test_fr031_abrir_tambien_es_un_ciclo(self):
        """FR-016, FR-031: abrir avanza el reloj, así que empieza un ciclo (ciclo + 1) además de subir
        version_puertas."""
        motor = motor_de_prueba()
        antes = motor.ciclo
        self.assertTrue(motor.ejecutar_accion("abrir", "E"))
        self.assertEqual(motor.ciclo, antes + 1)


class _BuscadorEscrituras(ast.NodeVisitor):
    """Recorre un archivo y anota cada escritura de `cerrada` fuera de MotorSimulacion._escribir_cerrada."""

    def __init__(self, es_motor):
        self.es_motor = es_motor
        self.pila = []  # nombres de clases y funciones que encierran al nodo actual
        self.hallazgos = []

    def _dentro_del_metodo_unico(self):
        if not self.es_motor:
            return False
        for i in range(len(self.pila) - 1):
            if self.pila[i] == ("clase", CLASE_MOTOR) and self.pila[i + 1] == ("funcion", METODO_UNICO):
                return True
        return False

    def _anotar(self, nodo, que):
        if not self._dentro_del_metodo_unico():
            self.hallazgos.append(f"línea {nodo.lineno}: {que}")

    def visit_ClassDef(self, nodo):
        self.pila.append(("clase", nodo.name))
        self.generic_visit(nodo)
        self.pila.pop()

    def _visitar_funcion(self, nodo):
        self.pila.append(("funcion", nodo.name))
        self.generic_visit(nodo)
        self.pila.pop()

    visit_FunctionDef = _visitar_funcion
    visit_AsyncFunctionDef = _visitar_funcion

    def _revisar_destino(self, destino):
        if isinstance(destino, (ast.Tuple, ast.List)):
            for elemento in destino.elts:
                self._revisar_destino(elemento)
            return
        if isinstance(destino, ast.Starred):
            self._revisar_destino(destino.value)
            return
        # `self.cerrada = ...` está permitido: es el atributo propio de otras clases (por ejemplo SalidaVerif en
        # Modelo/Resolubilidad.py, que copia el estado para la verificación), no el de una Salida del motor.
        if (isinstance(destino, ast.Attribute) and destino.attr == "cerrada"
                and not (isinstance(destino.value, ast.Name) and destino.value.id == "self")):
            self._anotar(destino, f"asignación a {ast.unparse(destino)}")

    def visit_Assign(self, nodo):
        for destino in nodo.targets:
            self._revisar_destino(destino)
        self.generic_visit(nodo)

    def visit_AugAssign(self, nodo):
        self._revisar_destino(nodo.target)
        self.generic_visit(nodo)

    def visit_AnnAssign(self, nodo):
        self._revisar_destino(nodo.target)
        self.generic_visit(nodo)

    def visit_Call(self, nodo):
        funcion = nodo.func
        nombre = funcion.id if isinstance(funcion, ast.Name) else funcion.attr if isinstance(funcion, ast.Attribute) else None
        if nombre in ("setattr", "_asignar_reversible") and len(nodo.args) >= 2:
            atributo = nodo.args[1]
            if isinstance(atributo, ast.Constant) and atributo.value == "cerrada":
                self._anotar(nodo, f"{nombre}(..., \"cerrada\", ...)")
        self.generic_visit(nodo)


class TestFuenteUnicoEscritor(unittest.TestCase):
    def test_fr016_fr031_metodo_unico_existe(self):
        """FR-016, FR-031: MotorSimulacion define _escribir_cerrada; sin él la prueba de fuente pasaría en vacío."""
        self.assertTrue(callable(getattr(MotorSimulacion, METODO_UNICO, None)),
                        f"MotorSimulacion no tiene {METODO_UNICO}")
        with open(os.path.join(DIR_MODELO, ARCHIVO_MOTOR), encoding="utf-8") as archivo:
            arbol = ast.parse(archivo.read())
        encontrado = False
        for nodo in arbol.body:
            if isinstance(nodo, ast.ClassDef) and nodo.name == CLASE_MOTOR:
                for miembro in nodo.body:
                    if isinstance(miembro, ast.FunctionDef) and miembro.name == METODO_UNICO:
                        encontrado = True
        self.assertTrue(encontrado, f"{METODO_UNICO} no está definido en la clase {CLASE_MOTOR} de {ARCHIVO_MOTOR}")

    def test_fr016_fr031_nadie_mas_escribe_cerrada(self):
        """FR-016, FR-031: en Modelo/ solo MotorSimulacion._escribir_cerrada escribe Salida.cerrada: fuera de él no
        hay `x.cerrada = ...` (x distinto de self), setattr(..., "cerrada", ...) ni
        _asignar_reversible(..., "cerrada", ...)."""
        archivos = [nombre for nombre in os.listdir(DIR_MODELO) if nombre.endswith(".py")]
        self.assertIn(ARCHIVO_MOTOR, archivos)
        hallazgos = []
        for nombre in archivos:
            if nombre in EXCLUIDOS:
                continue
            with open(os.path.join(DIR_MODELO, nombre), encoding="utf-8") as archivo:
                arbol = ast.parse(archivo.read(), filename=nombre)
            buscador = _BuscadorEscrituras(nombre == ARCHIVO_MOTOR)
            buscador.visit(arbol)
            for hallazgo in buscador.hallazgos:
                hallazgos.append(f"Modelo/{nombre}, {hallazgo}")
        self.assertEqual(hallazgos, [], "escrituras de `cerrada` fuera de "
                         f"{CLASE_MOTOR}.{METODO_UNICO}:\n  " + "\n  ".join(hallazgos))


if __name__ == "__main__":
    unittest.main()
