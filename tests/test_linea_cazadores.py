# Los cazadores reales de A y la reconstrucción de la línea (spec 004, T079; Quickstart 14; FR-001, FR-025).
# Con enemigos de comportamiento «cazador» (`Enemigo.comportamiento == "cazador"`, 003-T045 a T048, no el doble de
# `utiles_linea`), una partida real y la que se reconstruye tras guardar, cargar y retroceder dan lo mismo turno por turno:
# sala, `activo`, `tiempo_siguiente` y vida de cada enemigo. Si el cazador consumiera azar o dependiera de algo que la copia
# no conserva, el sello `(reloj, secuencia)` lo detectaría y la reconstrucción terminaría en `ErrorReconstruccion`.
#
# `PruebasCazadoresReales` compara los estados, que es lo observable sin el registro de decisiones. T118: las de
# `PruebasRegistroDeDecisiones` repiten los escenarios con el registro de decisiones de A (003-T076) encendido con
# `motor.activar_registro_decisiones()` ANTES de `linea.iniciar`, y comparan cada entrada menos el ciclo (deshacer no lo baja).
# Usan `SesionLinea(registro=True)`.

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
from unittest import mock

from Controlador import ReconstructorLinea as modulo_reconstructor
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


# ───────────────────────── T118: el registro de decisiones de A (003-T076) encendido ─────────────────────────

# Un «vigía» es un cazador real cuyo rango (50) es menor que el costo de cualquier salida: nunca encuentra ruta, así que espera
# donde está. Sirve para tener cazadores activos en una sala ya visitada donde el jugador ya no está.
ID_VIGIA = "ent_vigia"
FICHA_VIGIA = dict(FICHA_CAZADOR, id=ID_VIGIA, nombre="Vigía", rango=50)

CONTENIDO_VIGIAS = [
    contenido_sala(1, objetos=(PERGAMINO,)),
    {"sala": 3, "trampas": [], "objetos": [],
     "enemigos": [{"instancia": "caz-1", "tipo": ID_CAZADOR}, {"instancia": "vig-1", "tipo": ID_VIGIA},
                  {"instancia": "vig-2", "tipo": ID_VIGIA}]},
    {"sala": 4, "trampas": [], "objetos": [], "enemigos": [{"instancia": "vig-3", "tipo": ID_VIGIA}]},
]


def decisiones(motor):
    """El registro de decisiones de los cazadores sin el ciclo (`entrada[0]`): reloj, id, acción, sala de destino, dirección
    y costo base. Deshacer no baja el ciclo y la reconstrucción lo recalcula: no se compara."""
    return [entrada[1:] for entrada in motor.registro_decisiones]


class PruebasRegistroDeDecisiones(BaseCazadores):
    """T118 (FR-025, 003-T058 y 003-T059): con el registro encendido, la partida real y cada estado reconstruido dan las
    mismas decisiones de los cazadores, turno por turno."""

    def sesion(self, k=3, contenido=CONTENIDO, fichas=None):
        sesion = SesionLinea(k=k, semilla=5, pergaminos=1, huellas=False, registro=True, contenido=contenido,
                             catalogo_extra=fichas or [FICHA_CAZADOR])
        self.addCleanup(sesion.cerrar)
        return sesion

    def jugar(self, sesion, acciones, vistas):
        """Ejecuta `acciones` y anota el registro de decisiones justo antes de cada una que se acepta."""
        for accion in acciones:
            antes = decisiones(sesion.motor)
            if sesion.hacer([accion]):
                vistas.append(antes)

    def partida(self, sesion):
        """Acciones, guardar y cargar, más acciones, retroceso y más acciones. Devuelve las decisiones antes de cada acción
        vigente (None para recoger el pergamino, que se jugó al crear la sesión) y las acciones que quedaron al retroceder."""
        vistas = [None] * sesion.linea.acciones
        self.jugar(sesion, ANTES_DE_GUARDAR, vistas)
        sesion.guardar_y_cargar()
        self.jugar(sesion, DESPUES_DE_CARGAR, vistas)
        self.assertTrue(sesion.retroceder())
        del vistas[sesion.linea.acciones:]
        posicion = sesion.linea.acciones
        self.jugar(sesion, TRAS_RETROCEDER, vistas)
        return vistas, posicion

    def comparar(self, linea, motor, vistas, desde=1):
        for k in range(desde, linea.acciones + 1):
            if vistas[k - 1] is None:
                continue
            clon = linea.clon_antes_de(k, motor)
            self.assertIsNotNone(clon.registro_decisiones, f"acción {k}: el clon perdió el registro")
            self.assertEqual(decisiones(clon), vistas[k - 1], f"acción {k}")

    def con_registro_encendido(self):
        """La reproducción del guion crea sus motores con `preparar_partida` y `cargar_partida`, y el archivo no guarda el
        registro: se envuelven solo en la prueba para encenderlo igual que en la partida real."""
        preparar = modulo_reconstructor.preparar_partida
        cargar = modulo_reconstructor.cargar_partida

        def preparar_con_registro(*args, **kwargs):
            motor = preparar(*args, **kwargs)
            motor.activar_registro_decisiones()
            return motor

        def cargar_con_registro(*args, **kwargs):
            motor = cargar(*args, **kwargs)
            motor.activar_registro_decisiones()
            return motor

        return mock.patch.multiple(modulo_reconstructor, preparar_partida=preparar_con_registro,
                                   cargar_partida=cargar_con_registro)

    def test_fr025_el_registro_se_enciende_antes_de_iniciar_y_los_cazadores_deciden(self):
        sesion = self.sesion()
        self.assertEqual(sesion.motor.registro_decisiones, [])
        self.jugar(sesion, ANTES_DE_GUARDAR, [])
        self.assertGreater(len(sesion.motor.registro_decisiones), 4)
        self.assertTrue(all(entrada[2] in ("caz-1", "caz-2") for entrada in sesion.motor.registro_decisiones))

    def test_fr025_la_linea_viva_da_las_mismas_decisiones_tras_guardar_y_cargar(self):
        sesion = self.sesion()
        vistas = [None] * sesion.linea.acciones
        self.jugar(sesion, ANTES_DE_GUARDAR, vistas)
        sesion.guardar_y_cargar()
        self.jugar(sesion, DESPUES_DE_CARGAR, vistas)
        self.assertGreater(len(sesion.motor.registro_decisiones), 0)
        self.comparar(sesion.linea, sesion.motor, vistas)

    def test_fr025_tras_retroceder_el_registro_vivo_solo_conserva_las_vigentes_y_lo_posterior_coincide(self):
        sesion = self.sesion()
        vistas, posicion = self.partida(sesion)
        self.assertGreater(len(vistas) - posicion, 3)
        self.comparar(sesion.linea, sesion.motor, vistas, desde=posicion + 1)       # tras un retroceso: solo lo posterior

    def test_fr025_el_retroceso_deja_el_registro_vivo_igual_al_de_antes_de_esa_accion(self):
        sesion = self.sesion()
        vistas = [None] * sesion.linea.acciones
        self.jugar(sesion, ANTES_DE_GUARDAR, vistas)
        antes = decisiones(sesion.motor)
        self.assertTrue(sesion.retroceder())
        posicion = sesion.linea.acciones
        self.assertLess(posicion, len(vistas))
        self.assertEqual(decisiones(sesion.motor), vistas[posicion])     # solo las vigentes, en orden, sin filtrar por reloj
        self.assertLess(len(decisiones(sesion.motor)), len(antes))

    def test_fr025_reconstruir_tras_guardar_da_las_mismas_decisiones(self):
        sesion = self.sesion()
        vistas, posicion = self.partida(sesion)
        ruta = os.path.join(sesion.partida.carpeta.name, "final.cripta")
        registro = sesion.linea.a_registro()
        guardar_motor(sesion.motor, ruta, sesion.partida.gestor, linea=registro)
        restaurador = RestauradorPartida(ruta)
        self.addCleanup(restaurador.cerrar)
        reconstructor = ReconstructorLinea(sesion.partida.nuevo_gestor(iniciado=False))
        self.addCleanup(reconstructor.cerrar)
        with self.con_registro_encendido():
            linea = reconstructor.reconstruir(restaurador.leer_linea(), restaurador.encabezado, restaurador.leer_jugador())
            self.assertEqual(linea.a_registro(), registro)
            self.comparar(linea, sesion.motor, vistas, desde=posicion + 1)       # tras un retroceso: solo lo posterior

    def test_fr025_tras_cargar_con_cazadores_activos_en_salas_donde_el_jugador_ya_no_esta(self):
        sesion = self.sesion(contenido=CONTENIDO_VIGIAS, fichas=[FICHA_CAZADOR, FICHA_VIGIA])
        vistas = [None] * sesion.linea.acciones
        # entrar a la 3 activa a los tres; los vigías esperan allí y el cazador sale tras el jugador
        self.jugar(sesion, [("mover", "E"), ("mover", "E"), ("mover", "O"), ("mover", "O"), ("esperar", "")], vistas)
        lejos = [e.id for e in sesion.motor.enemigos if e.activo and e.sala is not sesion.motor.jugador.sala]
        self.assertIn("vig-1", lejos, "el escenario necesita enemigos activos fuera de la sala del jugador")
        sesion.guardar_y_cargar()
        # la carga los dejó activos, cada uno en su sala
        self.assertEqual([e.id for e in sesion.motor.enemigos if e.activo and e.sala is not sesion.motor.jugador.sala], lejos)
        self.jugar(sesion, [("esperar", ""), ("mover", "E"), ("esperar", ""), ("mover", "O"), ("esperar", "")], vistas)
        self.comparar(sesion.linea, sesion.motor, vistas)
        self.assertTrue(sesion.retroceder())
        del vistas[sesion.linea.acciones:]
        posicion = sesion.linea.acciones
        self.jugar(sesion, [("esperar", ""), ("mover", "E"), ("esperar", "")], vistas)
        self.comparar(sesion.linea, sesion.motor, vistas, desde=posicion + 1)

    def test_fr025_tras_cargar_dos_enemigos_de_salas_distintas_con_el_mismo_instante(self):
        # vig-1 espera en la 3 y vig-3 en la 4, y los dos tienen programada su siguiente acción en el MISMO instante: el CRPT 3
        # guarda ese instante pero no la secuencia, y la carga los restaura por id de sala (límite conocido de la carga)
        sesion = self.sesion(contenido=CONTENIDO_VIGIAS, fichas=[FICHA_CAZADOR, FICHA_VIGIA])
        vistas = [None] * sesion.linea.acciones
        self.jugar(sesion, [("mover", "E"), ("mover", "E"), ("mover", "O"), ("mover", "O"), ("mover", "S"), ("esperar", ""),
                            ("mover", "N")], vistas)
        motor = sesion.motor
        vig = {e.id: e for e in motor.enemigos}
        self.assertTrue(vig["vig-1"].activo and vig["vig-3"].activo)
        self.assertNotEqual(vig["vig-1"].sala.id, vig["vig-3"].sala.id)
        self.assertEqual(vig["vig-1"].tiempo_siguiente, vig["vig-3"].tiempo_siguiente)
        sesion.guardar_y_cargar()
        self.jugar(sesion, [("esperar", ""), ("esperar", ""), ("mover", "S"), ("esperar", "")], vistas)
        self.comparar(sesion.linea, sesion.motor, vistas)

    def test_fr025_tras_cargar_el_enemigo_de_la_sala_mayor_se_activo_antes_con_el_mismo_instante(self):
        # igual que el anterior, pero vig-3 (sala 4) se activó ANTES que vig-1 (sala 3): en la partida real le toca antes en
        # el mismo instante y tras cargar la sala de id menor va primero. Si los registros difieren, es ese límite de la carga.
        sesion = self.sesion(contenido=CONTENIDO_VIGIAS, fichas=[FICHA_CAZADOR, FICHA_VIGIA])
        vistas = [None] * sesion.linea.acciones
        self.jugar(sesion, [("mover", "S"), ("mover", "N"), ("mover", "E"), ("mover", "E"), ("mover", "O"), ("esperar", "")], vistas)
        vig = {e.id: e for e in sesion.motor.enemigos}
        self.assertTrue(vig["vig-1"].activo and vig["vig-3"].activo)
        self.assertEqual(vig["vig-1"].tiempo_siguiente, vig["vig-3"].tiempo_siguiente)
        sesion.guardar_y_cargar()
        self.jugar(sesion, [("esperar", ""), ("esperar", ""), ("mover", "O"), ("esperar", "")], vistas)
        self.comparar(sesion.linea, sesion.motor, vistas)

    def test_fr025_con_k_distinta_las_decisiones_reconstruidas_son_las_mismas(self):
        referencia = None
        for k in (1, 4, 50):
            with self.subTest(k=k):
                sesion = self.sesion(k=k)
                vistas, posicion = self.partida(sesion)
                vistos = [decisiones(sesion.linea.clon_antes_de(n, sesion.motor)) for n in range(posicion + 1, sesion.linea.acciones + 1)]
                self.assertEqual(vistos, vistas[posicion:])
                referencia = referencia or vistos
                self.assertEqual(vistos, referencia)


if __name__ == "__main__":
    unittest.main()
