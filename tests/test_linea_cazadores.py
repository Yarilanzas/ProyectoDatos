# Los cazadores reales de A y la reconstrucción de la línea (spec 004, T079; Quickstart 14; FR-001, FR-025).
# Con enemigos de comportamiento «cazador» (`Enemigo.comportamiento == "cazador"`, 003-T045 a T048, no el doble de
# `utiles_linea`), una partida real y la que se reconstruye tras guardar, cargar y retroceder dan lo mismo turno por turno:
# sala, `activo`, `tiempo_siguiente` y vida de cada enemigo. Si el cazador consumiera azar o dependiera de algo que la copia
# no conserva, el sello `(reloj, secuencia)` lo detectaría y la reconstrucción terminaría en `ErrorReconstruccion`.
#
# El registro de decisiones de los cazadores (003-T076) existe en el motor de A, pero repetir esta prueba con él encendido queda
# para T118: aquí se comparan los estados, que es lo observable sin ese registro.

import os
import sys
import unittest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from Controlador.ControladorPartida import guardar_motor
from Controlador.ReconstructorLinea import ReconstructorLinea
from Gestor.PreparadorPartida import cargar_partida
from Persistencia.ConversorPartida import RestauradorPartida
from tests.utiles_linea import FICHA_CAZADOR, ID_CAZADOR, SesionLinea
from tests.utiles_niebla import PERGAMINO, TRAMPA, contenido_sala

# 1 -E- 2 -E- 3 (los cazadores esperan en la 3 y salen tras el jugador); la 1 tiene el pergamino de retroceso
CONTENIDO = [
    contenido_sala(1, objetos=(PERGAMINO,)),
    contenido_sala(3, enemigos=("caz-1", "caz-2"), tipo_enemigo=ID_CAZADOR),
    contenido_sala(5, trampas=("t-dardos-1",)),
]

# huir de la 3 hacia la 1, esperar, guardar y cargar, volver hacia los cazadores, retroceder y seguir
ANTES_DE_GUARDAR = [("mover", "E"), ("mover", "E"), ("mover", "O"), ("mover", "O"), ("esperar", ""), ("esperar", "")]
DESPUES_DE_CARGAR = [("mover", "E"), ("esperar", ""), ("esperar", ""), ("mover", "O"), ("esperar", "")]
TRAS_RETROCEDER = [("esperar", ""), ("mover", "E"), ("esperar", ""), ("mover", "O"), ("esperar", "")]


def estado(motor):
    """Lo que se compara de cada enemigo: (id, sala, activo, tiempo_siguiente, vida), en el orden del motor."""
    return [(e.id, e.sala.id, e.activo, e.tiempo_siguiente, e.vida) for e in motor.enemigos]


class BaseCazadores(unittest.TestCase):

    def sesion(self, k=3):
        sesion = SesionLinea(k=k, semilla=5, pergaminos=1, huellas=False, contenido=CONTENIDO, catalogo_extra=[FICHA_CAZADOR])
        self.addCleanup(sesion.cerrar)
        return sesion

    def jugar(self, sesion, acciones, estados):
        """Ejecuta `acciones` y anota el estado de los enemigos justo antes de cada una que se acepta."""
        for accion in acciones:
            antes = estado(sesion.motor)
            if sesion.hacer([accion]):
                estados.append(antes)

    def retroceder(self, sesion, estados):
        self.assertTrue(sesion.retroceder())
        del estados[sesion.linea.acciones:]

    def partida_completa(self, sesion):
        """La partida del enunciado: acciones, guardar y cargar, más acciones, retroceso y más acciones. Devuelve la lista
        de estados de los enemigos antes de cada acción vigente y la posición del retroceso (acciones que quedan)."""
        estados = [None] * sesion.linea.acciones     # recoger el pergamino ya se jugó en la sesión: no se compara
        self.jugar(sesion, ANTES_DE_GUARDAR, estados)
        sesion.guardar_y_cargar()
        self.jugar(sesion, DESPUES_DE_CARGAR, estados)
        self.retroceder(sesion, estados)
        posicion = sesion.linea.acciones
        self.jugar(sesion, TRAS_RETROCEDER, estados)
        return estados, posicion


class PruebasCazadoresReales(BaseCazadores):

    def test_fr025_los_enemigos_son_cazadores_reales_y_hacen_algo(self):
        sesion = self.sesion()
        estados = []
        self.jugar(sesion, ANTES_DE_GUARDAR, estados)
        cazadores = [e for e in sesion.motor.enemigos if e.comportamiento == "cazador"]
        self.assertEqual(len(cazadores), 2)
        for cazador in cazadores:
            self.assertEqual(type(cazador).__name__, "Enemigo")
            self.assertEqual(cazador.rango, 3000)
        # se activaron al entrar el jugador a su sala y se movieron: las fotos no son todas iguales
        self.assertTrue(any(foto != estados[0] for foto in estados))
        self.assertTrue(any(activo for _id, _sala, activo, _t, _v in estados[-1]))
        salas = [[sala for _id, sala, _a, _t, _v in foto] for foto in estados]
        self.assertTrue(any(salas[i] != salas[i + 1] for i in range(len(salas) - 1)), "ningún cazador cambió de sala")

    def test_fr025_la_linea_viva_reproduce_cada_turno_antes_y_despues_del_retroceso(self):
        sesion = self.sesion()
        estados, posicion = self.partida_completa(sesion)
        linea = sesion.linea
        self.assertEqual(linea.acciones, len(estados))
        for k in range(1, linea.acciones + 1):
            clon = linea.clon_antes_de(k, sesion.motor)
            if estados[k - 1] is not None:
                self.assertEqual(estado(clon), estados[k - 1], f"acción {k}" + (" (posterior al retroceso)" if k > posicion else ""))
        self.assertGreater(len(estados) - posicion, 3)       # hay turnos posteriores al retroceso que comparar

    def test_fr025_la_linea_reconstruida_tras_guardar_y_cargar_reproduce_los_mismos_turnos(self):
        sesion = self.sesion()
        estados, posicion = self.partida_completa(sesion)
        ruta = os.path.join(sesion.partida.carpeta.name, "final.cripta")
        registro = sesion.linea.a_registro()
        guardar_motor(sesion.motor, ruta, sesion.partida.gestor, linea=registro)
        restaurador = RestauradorPartida(ruta)
        self.addCleanup(restaurador.cerrar)
        reconstructor = ReconstructorLinea(sesion.partida.nuevo_gestor(iniciado=False))
        self.addCleanup(reconstructor.cerrar)
        linea = reconstructor.reconstruir(restaurador.leer_linea(), restaurador.encabezado, restaurador.leer_jugador())
        self.assertEqual(linea.a_registro(), registro)      # los sellos de cada acción coinciden: no se consumió azar de más
        for k in range(1, linea.acciones + 1):
            if estados[k - 1] is None:
                continue
            clon = linea.clon_antes_de(k, sesion.motor)
            self.assertEqual(estado(clon), estados[k - 1], f"acción {k}")

    def test_fr025_el_motor_cargado_y_la_linea_que_sigue_a_la_carga_siguen_igual(self):
        sesion = self.sesion()
        self.jugar(sesion, ANTES_DE_GUARDAR, [])
        ruta = os.path.join(sesion.partida.carpeta.name, "guardado.cripta")
        guardar_motor(sesion.motor, ruta, sesion.partida.gestor, linea=sesion.linea.a_registro())
        antes_de_guardar = estado(sesion.motor)
        motor = cargar_partida(ruta, sesion.partida.nuevo_gestor(iniciado=False))
        self.addCleanup(lambda: motor.restaurador is not None and motor.restaurador.cerrar())
        # el cazador se reactiva igual al cargar: cada enemigo conserva sala, estado de activación y vida
        for (id_a, sala_a, _aa, _ta, vida_a), (id_b, sala_b, _ab, _tb, vida_b) in zip(antes_de_guardar, estado(motor)):
            self.assertEqual((id_a, sala_a, vida_a), (id_b, sala_b, vida_b))

    def test_fr025_sin_consumir_azar_el_sello_no_diverge(self):
        # si un cazador gastara azar, el clon (que hereda el azar del punto) y la partida real se separarían: el sello
        # `(reloj, secuencia)` de alguna acción no coincidiría y las consultas darían ErrorReconstruccion
        sesion = self.sesion(k=2)
        estados, _ = self.partida_completa(sesion)
        linea = sesion.linea
        for k in range(1, linea.acciones + 2):
            linea.consultar_accion(k, sesion.motor)       # no lanza ErrorReconstruccion
        for t in range(0, linea.reloj_actual, 37):
            linea.consultar_instante(t, sesion.motor)

    def test_fr025_la_reconstruccion_con_k_distinta_da_los_mismos_estados(self):
        referencia = None
        for k in (1, 4, 50):
            with self.subTest(k=k):
                sesion = self.sesion(k=k)
                estados, _ = self.partida_completa(sesion)
                vistos = []
                for numero in range(1, sesion.linea.acciones + 1):
                    clon = sesion.linea.clon_antes_de(numero, sesion.motor)
                    vistos.append(estado(clon))
                referencia = referencia or vistos
                self.assertEqual(vistos, referencia)


if __name__ == "__main__":
    unittest.main()
