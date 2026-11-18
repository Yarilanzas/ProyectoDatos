# Carga de enemigos activos en salas que no son la del jugador (capacidad 003, defecto de carga).
#
# `cargar_partida` restaura la sala del jugador y, por el mismo camino (RestauradorPartida -> _aplicar_registro), las
# salas guardadas que traen enemigos activos (tiempo >= 0), en orden de id ascendente. Antes de tocar el motor lee esos
# registros y pide sus fichas: si algo falla no se carga nada. Las demás salas se siguen leyendo al entrar.
#
# La partida es la cripta «8 salas» de tests/test_cazador_equivalencia.py, jugada con el controlador real. Tras las 21
# acciones de GUION el jugador está en la sala 3, `caz-1` activo en la sala 1 y `caz-2` activo en la sala 2 (vecina por
# el O). Sin red.

import contextlib
import io
import os
import sys
import unittest
from unittest import mock

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import main
from Gestor.GestorHistorico import SinDatosParaHistoria
from Gestor.PreparadorPartida import cargar_partida
from Persistencia import ConversorPartida
from Persistencia.ArchivoPartida import LectorPartida, guardar_partida
from Persistencia.RegistroSala import RegistroSala
from Vista.VistaConsola import VistaConsola
from tests.test_cazador_equivalencia import PREFIJO_FICHA_004, SEMILLA_004, opciones_de_paquete
from tests.utiles_linea import copia_sin_datos, partida_linea

GUION = ["mover S"] + ["esperar"] * 4 + ["mover N", "esperar", "mover E", "esperar", "mover O", "esperar", "mover E",
                                         "mover E", "esperar", "mover O", "esperar", "esperar", "mover E", "mover S",
                                         "mover N", "esperar"]
SALA_JUGADOR, SALA_CAZ1, SALA_CAZ2 = 3, 1, 2
FALTAN = "No se puede reconstruir sin nuevas solicitudes: faltan datos locales ("


def sin_entrada(_mensaje):
    raise EOFError


def leer(ruta):
    with open(ruta, "rb") as archivo:
        return archivo.read()


def eventos_de(motor, enemigo):
    return [evento for evento in motor.agenda.heap
            if not evento.cancelado and evento.tipo == "ACCION_ACTOR" and evento.actor is enemigo]


def orden_eventos(motor):
    """(tiempo, id) de las acciones pendientes de los enemigos, en el orden en que la agenda las ejecutará."""
    eventos = [evento for evento in motor.agenda.heap if not evento.cancelado and evento.tipo == "ACCION_ACTOR"
               and evento.actor is not motor.jugador]
    eventos.sort(key=lambda evento: (evento.tiempo, evento.secuencia))
    return [(evento.tiempo, evento.actor.id) for evento in eventos]


def activos(motor):
    return sorted((enemigo.id, enemigo.sala.id, enemigo.vida, enemigo.tiempo_siguiente) for enemigo in motor.enemigos
                  if enemigo.esta_vivo() and enemigo.activo)


def enemigo_por_id(motor, id_enemigo):
    for enemigo in motor.enemigos:
        if enemigo.id == id_enemigo:
            return enemigo
    return None


class BaseCargaEnemigosActivos(unittest.TestCase):

    def setUp(self):
        self.partida = partida_linea(semilla=SEMILLA_004, **opciones_de_paquete("8 salas"))
        self.addCleanup(self.partida.cerrar)
        self.motores = []
        self.addCleanup(self.cerrar_motores)
        controlador = self.partida.controlador
        for comando in GUION:
            self.assertTrue(controlador.ejecutar(comando), comando)
        motor = controlador.motor
        self.assertEqual(motor.estado_partida(), "en_curso")
        self.assertEqual(motor.jugador.sala.id, SALA_JUGADOR)
        self.activos_antes = activos(motor)
        self.orden_antes = orden_eventos(motor)
        self.reloj = motor.reloj
        self.base = self.partida.carpeta.name
        self.guardado = os.path.join(self.base, "guardado.cripta")
        self.assertTrue(controlador.guardar(self.guardado))
        controlador._cerrar()
        # precondición: el archivo trae enemigos activos en salas que no son la del jugador
        salas = {id_enemigo: sala for id_enemigo, sala, _, _ in self.activos_antes}
        self.assertEqual(salas.get("caz-1"), SALA_CAZ1)
        self.assertEqual(salas.get("caz-2"), SALA_CAZ2)

    def cerrar_motores(self):
        for motor in self.motores:
            if motor.restaurador is not None:
                motor.restaurador.cerrar()
                motor.restaurador = None

    def cargar(self, ruta=None, gestor=None):
        motor = cargar_partida(ruta or self.guardado, gestor or self.partida.nuevo_gestor(iniciado=False))
        self.motores.append(motor)
        return motor

    def reescribir(self, nombre, cambiar):
        """Copia del guardado con las salas que devuelve `cambiar(registros, motor_de_referencia)`. Usa el mismo
        escritor CRPT 3 (sin bloque de línea): solo cambia el contenido de las salas."""
        destino = os.path.join(self.base, nombre)
        with LectorPartida(self.guardado) as lector:
            encabezado = lector.encabezado
            registros = lector.leer_todas_salas()
            jugador = lector.leer_jugador()
            conocimiento = lector.leer_conocimiento()
        registros = cambiar(registros)
        guardar_partida(destino, encabezado.cripta_id, encabezado.version_cripta, encabezado.version_catalogo,
                        encabezado.semilla, encabezado.reloj, registros, jugador, conocimiento=conocimiento)
        return destino

    def tipo_cazador(self):
        with LectorPartida(self.guardado) as lector:
            return lector.leer_sala(SALA_CAZ2).enemigos[0][1]


class PruebasRestauracion(BaseCargaEnemigosActivos):

    def test_al_cargar_estan_los_enemigos_activos_de_las_demas_salas_con_su_instante(self):
        motor = self.cargar()
        self.assertEqual(activos(motor), self.activos_antes)
        for sala in (SALA_JUGADOR, SALA_CAZ1, SALA_CAZ2):
            self.assertTrue(motor.contenido_disponible(sala), sala)
        for enemigo in motor.enemigos:
            if enemigo.activo:
                eventos = eventos_de(motor, enemigo)
                self.assertEqual(len(eventos), 1, enemigo.id)
                self.assertEqual(eventos[0].tiempo, enemigo.tiempo_siguiente)

    def test_los_eventos_restaurados_conservan_el_orden_tiempo_secuencia_de_la_partida_guardada(self):
        motor = self.cargar()
        self.assertEqual(orden_eventos(motor), self.orden_antes)
        self.assertGreaterEqual(len(self.orden_antes), 2)

    def test_a_entrar_a_una_sala_ya_restaurada_no_la_lee_ni_duplica_enemigos_objetos_ni_eventos(self):
        motor = self.cargar()
        sala = motor.buscar_sala(motor.salas, SALA_CAZ2)
        ids_antes = sorted(enemigo.id for enemigo in motor.enemigos)
        objetos_antes = [objeto.instancia_id for objeto in motor.obtener_objetos_suelo(sala)]
        lecturas = []
        leer_sala = motor.restaurador.lector.leer_sala
        with mock.patch.object(motor.restaurador.lector, "leer_sala",
                               side_effect=lambda id_sala: lecturas.append(id_sala) or leer_sala(id_sala)):
            self.assertTrue(motor.ejecutar_accion("mover", "O"))
            self.assertEqual(motor.jugador.sala.id, SALA_CAZ2)
            # el camino del motor también: preparar_sala de una sala restaurada no vuelve a aplicarla
            motor.preparar_sala(motor.buscar_sala(motor.salas, SALA_CAZ1))
        self.assertNotIn(SALA_CAZ2, lecturas)
        self.assertNotIn(SALA_CAZ1, lecturas)

        ids = [enemigo.id for enemigo in motor.enemigos]
        self.assertEqual(len(ids), len(set(ids)), "enemigo duplicado")
        self.assertEqual(sorted(ids), ids_antes)
        for id_sala in (SALA_CAZ1, SALA_CAZ2):
            self.assertEqual(sum(1 for contenido in motor.contenidos_salas if contenido.id_sala == id_sala), 1)
            self.assertEqual(motor._salas_contenido_cargado.count(id_sala), 1)
            self.assertEqual(sum(1 for entrada in motor.objetos_suelo if entrada[0] == id_sala), 1)
        self.assertEqual([objeto.instancia_id for objeto in motor.obtener_objetos_suelo(sala)], objetos_antes)
        for enemigo in motor.enemigos:
            self.assertLessEqual(len(eventos_de(motor, enemigo)), 1, enemigo.id)

    def test_c_un_enemigo_inactivo_no_se_restaura_al_cargar(self):
        tipo = self.tipo_cazador()
        motor_referencia = self.cargar()
        guardadas = {SALA_JUGADOR, SALA_CAZ1, SALA_CAZ2}
        with LectorPartida(self.guardado) as lector:
            guardadas.update(lector.ids_salas())
        libres = [sala.id for sala in motor_referencia.salas
                  if sala.id not in guardadas and sala.id != motor_referencia.sala_salida]
        self.assertTrue(libres, "no hay una sala sin guardar para la prueba")
        dormida = libres[0]

        def cambiar(registros):
            for registro in registros:
                if registro.sala_id == SALA_CAZ2:  # sala mixta: un activo (caz-2) y un inactivo
                    registro.enemigos.append(("dormido-mixto", tipo, 5, -1))
            registros.append(RegistroSala(dormida, -1, [("dormido-solo", tipo, 5, -1)], [], [], []))
            return registros

        ruta = self.reescribir("inactivos.cripta", cambiar)
        motor = self.cargar(ruta)

        # sala solo con un inactivo: no se restaura al cargar, queda para cuando el jugador entre
        self.assertIsNone(enemigo_por_id(motor, "dormido-solo"))
        self.assertFalse(motor.contenido_disponible(dormida))
        # sala mixta: se restaura por su activo; el inactivo existe pero sigue inactivo y sin acción programada
        mixto = enemigo_por_id(motor, "dormido-mixto")
        self.assertIsNotNone(mixto)
        self.assertFalse(mixto.activo)
        self.assertEqual(eventos_de(motor, mixto), [])
        self.assertTrue(enemigo_por_id(motor, "caz-2").activo)
        self.assertEqual(activos(motor), self.activos_antes)

        # al entrar (preparar_sala) la sala dormida se lee del archivo como siempre, y su enemigo sigue inactivo
        motor.preparar_sala(motor.buscar_sala(motor.salas, dormida))
        solo = enemigo_por_id(motor, "dormido-solo")
        self.assertIsNotNone(solo)
        self.assertFalse(solo.activo)
        self.assertEqual(eventos_de(motor, solo), [])

    def test_con_el_mismo_instante_va_primero_el_enemigo_de_la_sala_de_id_menor(self):
        # El CRPT 3 guarda el instante de cada enemigo, no su secuencia: en un empate de instante entre salas distintas
        # el orden tras cargar lo fija la restauración (sala del jugador primero, luego id ascendente), no la partida
        # guardada. Se intercambian caz-1 y caz-2 de sala para que el orden por sala sea el contrario al de sus ids.
        empate = self.reloj + 500

        def cambiar(registros):
            por_sala = {registro.sala_id: registro for registro in registros}
            uno = [e for e in por_sala[SALA_CAZ1].enemigos if e[0] == "caz-1"][0]
            dos = [e for e in por_sala[SALA_CAZ2].enemigos if e[0] == "caz-2"][0]
            por_sala[SALA_CAZ1].enemigos = [e for e in por_sala[SALA_CAZ1].enemigos if e[0] != "caz-1"]
            por_sala[SALA_CAZ2].enemigos = [e for e in por_sala[SALA_CAZ2].enemigos if e[0] != "caz-2"]
            por_sala[SALA_CAZ1].enemigos.append((dos[0], dos[1], dos[2], empate))
            por_sala[SALA_CAZ2].enemigos.append((uno[0], uno[1], uno[2], empate))
            return registros

        motor = self.cargar(self.reescribir("empate.cripta", cambiar))
        caz2, caz1 = enemigo_por_id(motor, "caz-2"), enemigo_por_id(motor, "caz-1")
        self.assertEqual((caz2.sala.id, caz1.sala.id), (SALA_CAZ1, SALA_CAZ2))
        self.assertEqual(caz2.evento_actual.tiempo, caz1.evento_actual.tiempo)
        self.assertLess(caz2.evento_actual.secuencia, caz1.evento_actual.secuencia)

        # y es determinista: otra carga del mismo archivo da el mismo orden
        otra = self.cargar(self.reescribir("empate_2.cripta", cambiar))
        self.assertEqual(orden_eventos(otra), orden_eventos(motor))


class PruebasCargaAtomica(BaseCargaEnemigosActivos):

    def test_b_sin_carpeta_de_datos_con_enemigos_en_otras_salas_sale_con_codigo_1_y_no_carga_nada(self):
        copia = copia_sin_datos(self.partida, "datos")
        self.addCleanup(copia.cerrar)
        guardado = copia.ruta("guardado.cripta")
        continuacion = copia.ruta("continuacion.log")
        puntajes = copia.ruta("puntajes.txt")
        antes = leer(guardado)
        argv = ["main.py", "--offline", copia.paquete, "--datos-locales", copia.ruta_datos, "--puntajes", puntajes,
                "--cargar", guardado, "--bitacora", continuacion]
        salida = io.StringIO()
        with contextlib.ExitStack() as pila:
            pila.enter_context(mock.patch.object(main, "VistaConsola", lambda: VistaConsola(entrada=sin_entrada)))
            pila.enter_context(mock.patch.object(main, "configurar_logging", lambda *a, **k: None))
            pila.enter_context(mock.patch.object(sys, "argv", argv))
            pila.enter_context(contextlib.redirect_stdout(salida))
            codigo = main.main()
        texto = salida.getvalue()
        self.assertEqual(codigo, 1, texto)
        self.assertTrue(texto.startswith(f"! Error: {FALTAN}"), texto)
        self.assertFalse(os.path.exists(continuacion), "se creó la bitácora de la continuación")
        self.assertFalse(os.path.exists(puntajes))
        self.assertEqual(leer(guardado), antes)

    def test_b_si_falta_la_ficha_de_un_enemigo_de_otra_sala_falla_antes_de_modificar_el_motor(self):
        gestor = self.partida.nuevo_gestor(iniciado=False)
        original = gestor.obtener_ficha

        def obtener_ficha(tipo):
            if str(tipo).startswith(PREFIJO_FICHA_004):
                raise SinDatosParaHistoria(f"{FALTAN}ficha {tipo})")
            return original(tipo)

        aplicados, puertas, restauradores = [], [], []
        aplicar = ConversorPartida._aplicar_registro
        reales = ConversorPartida.aplicar_puertas_reales
        crear_restaurador = ConversorPartida.RestauradorPartida

        def nuevo_restaurador(ruta):
            restaurador = crear_restaurador(ruta)
            restauradores.append(restaurador)
            return restaurador

        with mock.patch.object(gestor, "obtener_ficha", side_effect=obtener_ficha), \
                mock.patch.object(ConversorPartida, "_aplicar_registro",
                                  side_effect=lambda m, r: aplicados.append(r.sala_id) or aplicar(m, r)), \
                mock.patch("Gestor.PreparadorPartida.aplicar_puertas_reales",
                           side_effect=lambda m, r: puertas.append(True) or reales(m, r)), \
                mock.patch("Gestor.PreparadorPartida.RestauradorPartida", side_effect=nuevo_restaurador):
            with self.assertRaises(SinDatosParaHistoria):
                cargar_partida(self.guardado, gestor)

        self.assertEqual(aplicados, [], "se aplicó una sala antes de fallar")
        self.assertEqual(puertas, [], "se tocaron las puertas antes de fallar")
        self.assertEqual(len(restauradores), 1)
        # cargar_partida cerró el archivo: se puede reemplazar (en Windows no se podría con el lector abierto)
        os.replace(self.guardado, self.guardado + ".movido")


if __name__ == "__main__":
    unittest.main()
