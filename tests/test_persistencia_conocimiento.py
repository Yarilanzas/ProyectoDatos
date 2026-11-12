# Pruebas de persistencia del conocimiento: T069 (RegistroConocimiento, con exportar/restaurar de T074),
# T119 (copia, serialización y lotes reversibles para los puntos de control de Persona D, spec 004) y
# T068, T070 a T072 (guardar y cargar el CRPT 3 con el bloque de conocimiento).
# FR-004, FR-006, FR-014, FR-015, FR-016, PR-05, PR-06, PR-07. Contrato: contracts/formato-partida.md.

import os
import sys

# Permite ejecutar este archivo desde cualquier carpeta (PyCharm, unittest o pytest).
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import json
import struct
import unittest

from API.Fuentes import FuenteDatosOffline
from DTOS.Salida import Salida
from Gestor.GestorDatos import GestorDatos
from Gestor.PreparadorPartida import cargar_partida
from Modelo.Conocimiento import ABIERTA, AVISTADA, CERRADA, Conocimiento, DESCONOCIDA, EXPLORADA
from Modelo.retroceso import Historial
from Persistencia.ArchivoPartida import guardar_partida
from Persistencia.ConversorPartida import registro_jugador_desde_motor, registros_desde_motor
from Persistencia.FormatoBinario import FORMATO_PREFIJO, VersionIncompatible
from Persistencia.RegistroConocimiento import RegistroConocimiento
from Vista.VistaConsola import VistaConsola
from tests.test_antorcha import CONTENIDO as CONTENIDO_ANTORCHA, ID_ANTORCHA, ID_PERGAMINO
from tests.test_antorcha import mapa as mapa_antorcha
from tests.utiles_niebla import (CRIPTA_NIEBLA, ENEMIGO_LENTO, LLAVE, PERGAMINO, buscador_prueba,
                                 contenido_sala)
from tests.test_conocimiento import BaseConocimiento, foto
from tests.test_conocimiento import mapa as mapa_cuadro


def texto(cadena):
    datos = cadena.encode("utf-8")
    return struct.pack("<H", len(datos)) + datos


def registro_ejemplo():
    return RegistroConocimiento(
        exploradas=[1, 3],
        recuerdos=[(1, "E", ABIERTA), (2, "O", CERRADA)],
        puertas_reales=[(1, "E", False), (2, "O", True)],
    )


def campos(registro):
    return (list(registro.exploradas), [tuple(r) for r in registro.recuerdos],
            [tuple(p) for p in registro.puertas_reales])


def mismo_contenido(prueba, a, b):
    # Mismos elementos, sin importar el orden (el orden de revelación no se guarda: el bloque es canónico).
    prueba.assertEqual(len(a), len(b))
    for elemento in a:
        prueba.assertIn(elemento, b)


# T069: RegistroConocimiento.

class TestRegistroConocimiento(unittest.TestCase):

    def test_fr015_bytes_exactos_del_contrato(self):
        # <I cantidad, <I id; <I cantidad, <I sala <H+s dirección <B 1|2; <I cantidad, <I sala <H+s <B 0|1.
        esperado = (struct.pack("<I", 2) + struct.pack("<I", 1) + struct.pack("<I", 3)
                    + struct.pack("<I", 2)
                    + struct.pack("<I", 1) + texto("E") + struct.pack("<B", 1)
                    + struct.pack("<I", 2) + texto("O") + struct.pack("<B", 2)
                    + struct.pack("<I", 2)
                    + struct.pack("<I", 1) + texto("E") + struct.pack("<B", 0)
                    + struct.pack("<I", 2) + texto("O") + struct.pack("<B", 1))
        self.assertEqual(registro_ejemplo().to_bytes(), esperado)

    def test_fr015_ida_y_vuelta_binaria(self):
        registro = registro_ejemplo()
        self.assertEqual(campos(RegistroConocimiento.from_bytes(registro.to_bytes())), campos(registro))

    def test_fr015_ida_y_vuelta_json(self):
        registro = registro_ejemplo()
        datos = json.loads(json.dumps(registro.to_dict()))
        self.assertEqual(set(datos), {"exploradas", "recuerdos", "puertas_reales"})
        self.assertEqual(campos(RegistroConocimiento.from_dict(datos)), campos(registro))

    def test_fr015_el_mismo_estado_da_los_mismos_bytes(self):
        # Orden canónico por (sala, dirección), sin importar el orden de entrada.
        desordenado = RegistroConocimiento(
            exploradas=[3, 1],
            recuerdos=[(2, "O", CERRADA), (1, "E", ABIERTA)],
            puertas_reales=[(2, "O", True), (1, "E", False)],
        )
        self.assertEqual(desordenado.to_bytes(), registro_ejemplo().to_bytes())
        self.assertEqual(desordenado.to_dict(), registro_ejemplo().to_dict())

    def test_fr015_vacio(self):
        vacio = RegistroConocimiento([], [], [])
        self.assertEqual(vacio.to_bytes(), struct.pack("<III", 0, 0, 0))
        self.assertEqual(campos(RegistroConocimiento.from_bytes(vacio.to_bytes())), ([], [], []))

    def test_fr016_rechaza_bloques_danados(self):
        bueno = registro_ejemplo().to_bytes()
        malos = [
            bueno[:-1],                                   # truncado
            bueno + b"\x00",                              # bytes sobrantes
            bueno.replace(texto("O") + b"\x02", texto("O") + b"\x03", 1),  # recuerdo inválido
            bueno[:-1] + b"\x02",                         # puerta real inválida
            struct.pack("<III", 2, 3, 1) + bueno[12:],    # exploradas fuera de orden
        ]
        for datos in malos:
            with self.assertRaises(ValueError, msg=datos):
                RegistroConocimiento.from_bytes(datos)

    def test_fr016_rechaza_valores_invalidos_al_escribir_y_en_json(self):
        with self.assertRaises(ValueError):
            RegistroConocimiento([1], [(1, "E", 0)], []).to_bytes()  # sin observar no se guarda
        with self.assertRaises(ValueError):
            RegistroConocimiento([-1], [], []).to_bytes()
        with self.assertRaises(ValueError):
            RegistroConocimiento([1, 1], [], []).to_bytes()  # repetida
        with self.assertRaises(ValueError):
            RegistroConocimiento.from_dict({"exploradas": [1], "recuerdos": [[1, "E", 3]], "puertas_reales": []})


# T069 y T074: el registro a partir de una partida, con exportar y restaurar.

class BasePersistencia(BaseConocimiento):

    def nuevo(self, motor):
        # Un conocimiento recién creado sobre la misma cripta (mismos ordinales).
        return Conocimiento(motor._indice_salas, motor._destino)

    def assertMismoConocimiento(self, a, b):
        self.assertEqual(a.estado_sala, b.estado_sala)
        self.assertEqual(a.recuerdo_puerta, b.recuerdo_puerta)
        mismo_contenido(self, [s.id for s in a.reveladas], [s.id for s in b.reveladas])
        mismo_contenido(self, [(s._origen.id, s.sala_destino) for s in a.observadas],
                        [(s._origen.id, s.sala_destino) for s in b.observadas])


class TestExportarRestaurar(BasePersistencia):

    def test_fr015_recuerdos_de_salas_no_exploradas(self):
        # Al empezar en 1 se observan 2 -O-> 1 y 3 -N-> 1, que salen de salas solo avistadas.
        motor = self.partida(mapa_cuadro())
        exploradas, recuerdos = motor.conocimiento.exportar()
        self.assertEqual(exploradas, [1])
        self.assertEqual(recuerdos, [(1, "E", ABIERTA), (1, "S", ABIERTA), (2, "O", ABIERTA), (3, "N", ABIERTA)])

    def test_fr009_fr015_exploradas_por_antorcha(self):
        motor = self.partida(mapa_antorcha(), CONTENIDO_ANTORCHA)
        self.acciones(motor, ("recoger", ID_ANTORCHA), ("usar", ID_ANTORCHA), ("mover", "E"))
        exploradas, recuerdos = motor.conocimiento.exportar()
        self.assertEqual(exploradas, [1, 2, 3, 5])
        self.assertIn((2, "N", CERRADA), recuerdos)

        registro = RegistroConocimiento(exploradas, recuerdos, [])
        leido = RegistroConocimiento.from_bytes(registro.to_bytes())
        self.assertEqual(campos(leido), campos(registro))

    def test_fr004_fr015_avistadas_recalculadas_y_no_guardadas(self):
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, ("mover", "E"), ("mover", "S"))
        original = motor.conocimiento
        self.assertEqual(self.estados(motor), ([1, 2, 4], [3, 5], [6]))

        registro = RegistroConocimiento(*original.exportar(), [])
        leido = RegistroConocimiento.from_bytes(registro.to_bytes())
        restaurado = self.nuevo(motor)
        restaurado.restaurar(leido.exploradas, leido.recuerdos)

        self.assertMismoConocimiento(restaurado, original)
        self.assertEqual(restaurado.estado(self.sala(motor, 3)), AVISTADA)
        self.assertEqual(restaurado.estado(self.sala(motor, 6)), DESCONOCIDA)

    def test_fr015_restaurar_reemplaza_lo_que_habia_y_no_usa_historial(self):
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, ("mover", "E"))
        guardado = motor.conocimiento.exportar()
        self.acciones(motor, ("mover", "S"), ("mover", "S"))
        intervalos = len(motor.historial._intervalos)

        motor.conocimiento.restaurar(*guardado)
        self.assertEqual(motor.conocimiento.exportar(), guardado)
        self.assertEqual(motor.conocimiento.estado(self.sala(motor, 5)), DESCONOCIDA)
        self.assertEqual(len(motor.historial._intervalos), intervalos)

    def test_fr016_restaurar_rechaza_salas_y_direcciones_inexistentes(self):
        motor = self.partida(mapa_cuadro())
        conocimiento = self.nuevo(motor)
        for exploradas, recuerdos in (([99], []), ([1], [(1, "N", ABIERTA)]), ([1], [(1, "E", 7)])):
            with self.assertRaises(ValueError):
                conocimiento.restaurar(exploradas, recuerdos)


# T119: copia, serialización y lotes reversibles.

class TestCopia(BasePersistencia):

    def texto_mapa(self, motor):
        lineas = []
        VistaConsola(salida=lineas.append).mostrar_mapa(motor.mapa_conocido())
        return lineas

    def test_fr015_la_copia_es_independiente_y_da_el_mismo_mapa(self):
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, ("mover", "E"))
        original = motor.conocimiento
        mapa = self.texto_mapa(motor)
        copia = original.copiar()
        self.assertIsNot(copia, original)
        self.assertEqual(foto(copia), foto(original))

        motor.conocimiento = copia
        self.assertEqual(self.texto_mapa(motor), mapa)
        motor.conocimiento = original

        antes = foto(copia)
        self.acciones(motor, ("mover", "S"))  # cambia el original
        self.assertEqual(foto(copia), antes)

        antes = foto(original)
        copia.entrar(self.sala(motor, 3), False, Historial())  # cambia la copia
        self.assertEqual(foto(original), antes)
        self.assertEqual(copia.estado(self.sala(motor, 3)), EXPLORADA)


class TestSerializacion(BasePersistencia):

    def test_fr015_fr016_serializar_y_reconstruir_da_el_mismo_estado(self):
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, ("mover", "E"), ("mover", "S"), ("mover", "O"))
        original = motor.conocimiento
        datos = RegistroConocimiento(*original.exportar(), []).to_bytes()

        leido = RegistroConocimiento.from_bytes(datos)
        reconstruido = self.nuevo(motor)
        reconstruido.restaurar(leido.exploradas, leido.recuerdos)
        self.assertMismoConocimiento(reconstruido, original)
        self.assertEqual(RegistroConocimiento(*reconstruido.exportar(), []).to_bytes(), datos)

    def test_fr015_el_mismo_estado_da_la_misma_serializacion(self):
        # Dos recorridos distintos del cuadro (observan las puertas en distinto orden) llegan al mismo
        # conocimiento.
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, ("mover", "E"), ("mover", "S"), ("mover", "O"), ("mover", "N"))
        primero = motor.conocimiento
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, ("mover", "S"), ("mover", "E"), ("mover", "N"), ("mover", "O"))
        segundo = motor.conocimiento

        self.assertNotEqual([s._ordinal for s in primero.observadas], [s._ordinal for s in segundo.observadas])
        self.assertEqual(primero.exportar(), segundo.exportar())
        self.assertEqual(RegistroConocimiento(*primero.exportar(), []).to_bytes(),
                         RegistroConocimiento(*segundo.exportar(), []).to_bytes())


class SalaFalsa:
    def __init__(self, id_sala, salidas):
        self.id = id_sala
        self.salidas = salidas


def cripta_falsa():
    # 1 - 2 - 3 - 4 en línea, de ida y vuelta.
    uno = SalaFalsa(1, {"E": Salida(2, False, None, None)})
    dos = SalaFalsa(2, {"O": Salida(1, False, None, None), "E": Salida(3, False, None, None)})
    tres = SalaFalsa(3, {"O": Salida(2, False, None, None), "S": Salida(4, False, None, None)})
    cuatro = SalaFalsa(4, {"N": Salida(3, False, None, None)})
    salas = [uno, dos, tres, cuatro]

    def destino_de(salida):
        for sala in salas:
            if sala.id == salida.sala_destino:
                return sala
        return None

    return salas, Conocimiento(salas, destino_de)


class TestLotesReversibles(unittest.TestCase):

    def preparar(self):
        # Tres lotes: entrar a 1; entrar a 2 con antorcha (3 pasa de avistada a explorada dentro del mismo
        # lote); y observar el cierre de 2 -E-> 3. Se guarda una foto antes y después de cada uno.
        salas, conocimiento = cripta_falsa()
        uno, dos = salas[0], salas[1]
        historial = Historial()
        fotos = [foto(conocimiento)]
        lotes = [conocimiento.entrar(uno, False, historial)]
        fotos.append(foto(conocimiento))
        lotes.append(conocimiento.entrar(dos, True, historial))
        fotos.append(foto(conocimiento))
        dos.salidas["E"].cerrada = True
        lotes.append(conocimiento.observar_puerta(dos.salidas["E"], historial))
        fotos.append(foto(conocimiento))
        return conocimiento, lotes, fotos

    def test_pr05_cada_lote_guarda_valor_anterior_y_nuevo(self):
        conocimiento, lotes, _ = self.preparar()
        for lote in lotes:
            self.assertTrue(lote)
            for cambio in lote:
                self.assertEqual(len(cambio), 4)  # (tipo, ordinal, anterior, nuevo)
                self.assertNotEqual(cambio[2], cambio[3])

    def test_fr014_pr05_invertir_y_aplicar_en_cualquier_secuencia_valida(self):
        conocimiento, lotes, fotos = self.preparar()
        secuencia = (("invertir", 2), ("invertir", 1), ("aplicar", 1), ("aplicar", 2),
                     ("invertir", 2), ("invertir", 1), ("invertir", 0), ("aplicar", 0),
                     ("aplicar", 1), ("invertir", 1), ("aplicar", 1), ("aplicar", 2))
        actual = 3
        for operacion, indice in secuencia:
            if operacion == "invertir":
                conocimiento.invertir(lotes[indice])
                actual = indice
            else:
                conocimiento.aplicar(lotes[indice])
                actual = indice + 1
            self.assertEqual(foto(conocimiento), fotos[actual], (operacion, indice))

    def test_pr05_una_secuencia_invalida_se_rechaza_sin_cambiar_nada(self):
        conocimiento, lotes, fotos = self.preparar()
        with self.assertRaises(ValueError):
            conocimiento.aplicar(lotes[2])  # ya aplicado
        self.assertEqual(foto(conocimiento), fotos[3])
        with self.assertRaises(ValueError):
            conocimiento.invertir(lotes[1])  # no es el último aplicado
        self.assertEqual(foto(conocimiento), fotos[3])

    def test_fr014_el_historial_sigue_revirtiendo_igual(self):
        # `revertir` (lo que llama el Historial) es invertir; Modelo/retroceso.py no cambia.
        salas, conocimiento = cripta_falsa()
        historial = Historial()
        conocimiento.entrar(salas[0], False, historial)
        antes = foto(conocimiento)
        historial.abrir_intervalo()
        conocimiento.entrar(salas[1], True, historial)
        self.assertNotEqual(foto(conocimiento), antes)
        self.assertTrue(historial.deshacer_ultimo())
        self.assertEqual(foto(conocimiento), antes)


class TestHistorialDelMotor(BasePersistencia):

    def test_fr014_el_pergamino_sigue_restaurando_el_conocimiento(self):
        motor = self.partida(mapa_cuadro())
        antes = foto(motor.conocimiento)
        self.acciones(motor, ("mover", "E"))
        self.assertTrue(motor.historial.deshacer_ultimo())
        self.assertEqual(foto(motor.conocimiento), antes)


# T068, T070 a T072: guardar y cargar el CRPT 3. T087 a T090: replay de partidas cargadas.

class BloqueCrudo:
    # Se pasa a guardar_partida como `conocimiento` para escribir bytes arbitrarios en el bloque.
    def __init__(self, datos):
        self.datos = datos

    def to_bytes(self):
        return self.datos


class BaseGuardado(BasePersistencia):

    def ruta(self, nombre="prueba.cripta"):
        return os.path.join(self.carpeta, nombre)

    def gestor_nuevo(self):
        return GestorDatos(FuenteDatosOffline(os.path.join(self.carpeta, "paquete")),
                           ruta_base=os.path.join(self.carpeta, "cache_carga"), cache_size=25)

    def guardar(self):
        self.assertTrue(self.controlador.guardar(self.ruta()))
        return self.ruta()

    def cargar(self):
        cargado = cargar_partida(self.ruta(), self.gestor_nuevo())
        self.addCleanup(cargado.restaurador.cerrar)
        return cargado

    def escribir(self, motor, conocimiento, nombre="prueba.cripta"):
        # Igual que `guardar`, pero con el bloque de conocimiento que da la prueba.
        gestor = self.controlador.gestor
        guardar_partida(self.ruta(nombre), motor.cripta_id, gestor.version_cripta(motor.cripta_id),
                        gestor.version_catalogo(), motor.semilla, motor.reloj, registros_desde_motor(motor),
                        registro_jugador_desde_motor(motor), conocimiento=conocimiento)
        return self.ruta(nombre)

    def assertRechazo(self, ruta):
        # VersionIncompatible es el código de salida 2 en main.py (FR-016). Nada queda cargado: el
        # archivo quedó cerrado, porque en Windows no se puede borrar un archivo abierto.
        with self.assertRaises(VersionIncompatible):
            cargar_partida(ruta, self.gestor_nuevo())
        os.remove(ruta)

    def texto_mapa(self, motor):
        lineas = []
        VistaConsola(salida=lineas.append).mostrar_mapa(motor.mapa_conocido())
        return lineas


class TestGuardarYCargar(BaseGuardado):

    def test_fr015_sc003_escenario_us5_1_el_mapa_conocido_es_identico(self):
        # Apéndice B: exploradas 1, 2, 4 y 3, avistada 5, y 1 -E-> 2 recordada abierta pero cerrada en
        # realidad sin que el jugador lo vea.
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, ("mover", "E"), ("mover", "S"), ("mover", "O"))
        self.puerta(motor, 1, "E").cerrada = True
        self.assertEqual(self.recuerdo(motor, 1, "E"), ABIERTA)
        self.assertEqual(self.estados(motor), ([1, 2, 3, 4], [5], [6]))
        mapa = self.texto_mapa(motor)

        self.guardar()
        cargado = self.cargar()

        self.assertMismoConocimiento(cargado.conocimiento, motor.conocimiento)
        self.assertEqual(cargado.conocimiento.exportar(), motor.conocimiento.exportar())
        self.assertEqual(self.estados(cargado), ([1, 2, 3, 4], [5], [6]))
        self.assertEqual(self.texto_mapa(cargado), mapa)
        self.assertEqual(self.recuerdo(cargado, 1, "E"), ABIERTA)
        self.assertTrue(self.puerta(cargado, 1, "E").cerrada)


class TestRechazosAlCargar(BaseGuardado):

    def preparar(self):
        motor = self.partida(mapa_cuadro())
        self.acciones(motor, ("mover", "E"))  # el jugador queda en 2
        return motor

    def valido(self, motor):
        return RegistroConocimiento(*motor.conocimiento.exportar(), []).to_bytes()

    def test_fr016_version_2(self):
        self.preparar()
        ruta = self.guardar()
        with open(ruta, "r+b") as archivo:
            archivo.write(struct.pack(FORMATO_PREFIJO, b"CRPT", 2))
        self.assertRechazo(ruta)

    def test_fr016_sin_bloque_de_conocimiento(self):
        motor = self.preparar()
        self.assertRechazo(self.escribir(motor, None))

    def test_fr016_bloque_truncado_o_con_bytes_sobrantes(self):
        motor = self.preparar()
        valido = self.valido(motor)
        for indice, datos in enumerate((valido[:-1], valido + b"\x00", b"\x01\x00")):
            with self.subTest(largo=len(datos)):
                self.assertRechazo(self.escribir(motor, BloqueCrudo(datos), f"caso{indice}.cripta"))

    def test_fr016_valor_invalido(self):
        motor = self.preparar()
        exploradas = struct.pack("<I", 2) + struct.pack("<I", 1) + struct.pack("<I", 2)
        recuerdo_7 = struct.pack("<I", 1) + struct.pack("<I", 1) + texto("E") + struct.pack("<B", 7)
        real_5 = struct.pack("<I", 1) + struct.pack("<I", 1) + texto("E") + struct.pack("<B", 5)
        ninguno = struct.pack("<I", 0)
        for indice, datos in enumerate((exploradas + recuerdo_7 + ninguno, exploradas + ninguno + real_5)):
            with self.subTest(datos=datos):
                self.assertRechazo(self.escribir(motor, BloqueCrudo(datos), f"caso{indice}.cripta"))

    def test_fr016_sala_o_direccion_inexistente(self):
        motor = self.preparar()
        casos = (
            RegistroConocimiento([1, 2, 99], [], []),
            RegistroConocimiento([1, 2], [(1, "N", ABIERTA)], []),
            RegistroConocimiento([1, 2], [(99, "E", ABIERTA)], []),
            RegistroConocimiento([1, 2], [], [(1, "N", True)]),
            RegistroConocimiento([1, 2], [], [(99, "E", True)]),
        )
        for indice, registro in enumerate(casos):
            with self.subTest(registro=campos(registro)):
                self.assertRechazo(self.escribir(motor, registro, f"caso{indice}.cripta"))

    def test_fr016_sala_del_jugador_no_explorada(self):
        motor = self.preparar()
        self.assertRechazo(self.escribir(motor, RegistroConocimiento([1], [], [])))

    def test_fr016_el_controlador_conserva_la_partida_en_curso(self):
        motor = self.preparar()
        ruta = self.escribir(motor, None)
        self.assertTrue(self.controlador.ejecutar(f"cargar {ruta}"))
        self.assertIs(self.controlador.motor, motor)
        self.assertEqual(self.controlador.vista.lineas[-1][0], "mostrar_error")


class TestPuertasReales(BaseGuardado):

    def test_fr006_fr015_h2_puerta_abierta_de_una_sala_no_restaurada(self):
        # 1 -E-> 2 cerrada con llave: se abre, se pasa a 2 y se guarda. Al cargar solo se lee el bloque
        # de 2, pero 1 -E-> 2 sigue abierta en memoria (tabla de puertas reales, PR-07).
        id_llave = f"obj-{CRIPTA_NIEBLA}-1-{LLAVE}-0"
        motor = self.partida(mapa_cuadro(cerrada=True, llave=LLAVE), [contenido_sala(1, objetos=[LLAVE])])
        self.acciones(motor, ("recoger", id_llave), ("abrir", "E"), ("mover", "E"))
        self.guardar()

        cargado = self.cargar()
        self.assertEqual(cargado._salas_contenido_cargado, [2])
        self.assertFalse(self.puerta(cargado, 1, "E").cerrada)
        self.assertEqual(cargado._salas_contenido_cargado, [2])  # no se leyó el bloque de la sala 1
        self.assertEqual(self.recuerdo(cargado, 1, "E"), ABIERTA)

        # Al volver a 1 se observa con su estado real: el recuerdo sigue siendo correcto.
        self.acciones(cargado, ("mover", "O"))
        self.assertEqual(self.recuerdo(cargado, 1, "E"), ABIERTA)
        self.assertFalse(self.puerta(cargado, 1, "E").cerrada)

    def test_fr006_fr015_h2_puerta_cerrada_en_el_esqueleto_sin_llave_ni_cierre(self):
        # 1 -E-> 2 viene cerrada en el esqueleto, sin llave ni cierre automático: se abre libremente.
        # Abierta hoy, solo la regla «estaba cerrada en el esqueleto» la mete en la tabla (PR-07).
        motor = self.partida(mapa_cuadro(cerrada=True))
        self.acciones(motor, ("abrir", "E"), ("mover", "E"))
        self.guardar()

        cargado = self.cargar()
        self.assertFalse(self.puerta(cargado, 1, "E").cerrada)
        self.assertEqual(cargado._salas_contenido_cargado, [2])  # no se leyó el bloque de la sala 1
        self.assertEqual(self.recuerdo(cargado, 1, "E"), ABIERTA)

    def test_fr006_fr015_h2_doble_ida_y_vuelta_tras_leer_el_bloque_de_la_sala(self):
        # Tras cargar se visita 1 (se lee su bloque) y se vuelve a guardar: restaurar la sala no debe hacer
        # que la puerta pierda «cerrada en el esqueleto» y salga de la tabla de puertas reales (PR-07).
        from Controlador.ControladorPartida import ControladorPartida
        from Persistencia.ArchivoPartida import LectorPartida
        from tests.test_integracion import VistaFalsa

        motor = self.partida(mapa_cuadro(cerrada=True))
        self.acciones(motor, ("abrir", "E"), ("mover", "E"))
        self.guardar()

        controlador = ControladorPartida(self.gestor_nuevo(), VistaFalsa(), os.path.join(self.carpeta, "segunda.log"))
        self.addCleanup(controlador._cerrar)
        controlador.cargar(self.ruta())
        self.assertTrue(controlador.motor.ejecutar_accion("mover", "O"))
        self.assertIn(1, controlador.motor._salas_contenido_cargado)  # se leyó el bloque de la sala 1
        self.assertTrue(self.puerta(controlador.motor, 1, "E").cerrada_en_esqueleto)

        segunda = self.ruta("segunda.cripta")
        self.assertTrue(controlador.guardar(segunda))
        with LectorPartida(segunda) as lector:
            self.assertIn((1, "E", False), [tuple(p) for p in lector.leer_conocimiento().puertas_reales])

        cargado = cargar_partida(segunda, self.gestor_nuevo())
        self.addCleanup(cargado.restaurador.cerrar)
        self.assertEqual(cargado.jugador.sala.id, 1)
        self.assertFalse(self.puerta(cargado, 1, "E").cerrada)
        self.assertEqual(self.recuerdo(cargado, 1, "E"), ABIERTA)


class TestCargaConAntorcha(BaseGuardado):

    def test_fr015_pr06_antorcha_conserva_lo_ganado_queda_apagada_y_no_reobserva(self):
        motor = self.partida(mapa_antorcha(), CONTENIDO_ANTORCHA)
        self.acciones(motor, ("recoger", ID_ANTORCHA), ("recoger", ID_PERGAMINO), ("usar", ID_ANTORCHA),
                      ("mover", "E"))
        # 2 -N-> 3 quedó recordada cerrada; se abre sin que el jugador lo vea. Si cargar volviera a
        # observar las puertas de la sala actual, el recuerdo pasaría a abierta.
        self.puerta(motor, 2, "N").cerrada = False
        guardado = motor.conocimiento.exportar()
        self.assertEqual(guardado[0], [1, 2, 3, 5])
        self.assertIn((2, "N", CERRADA), guardado[1])
        self.guardar()

        cargado = self.cargar()
        self.assertEqual(cargado.conocimiento.exportar(), guardado)
        self.assertFalse(getattr(cargado.jugador, "antorcha_encendida", False))
        self.assertEqual(cargado._salas_contenido_cargado, [2])  # la carga sigue perezosa

    def test_fr015_pr07_retroceder_tras_cargar_como_en_la_parte_i(self):
        motor = self.partida(mapa_antorcha(), CONTENIDO_ANTORCHA)
        self.acciones(motor, ("recoger", ID_ANTORCHA), ("recoger", ID_PERGAMINO), ("usar", ID_ANTORCHA),
                      ("mover", "E"))
        guardado = motor.conocimiento.exportar()
        self.guardar()

        cargado = self.cargar()
        # Sin historial no hay nada que deshacer y el pergamino no se consume.
        self.assertFalse(cargado.ejecutar_accion("retroceder", ""))
        self.assertEqual(cargado.conocimiento.exportar(), guardado)
        self.assertTrue(any(o.clase == "pergamino_retroceso" for o in cargado.jugador.inventario))

        # Tras jugar después de cargar, retroceder deshace el último paso con su conocimiento.
        self.assertTrue(cargado.ejecutar_accion("mover", "S"))
        antes = cargado.conocimiento.exportar()
        self.assertTrue(cargado.ejecutar_accion("mover", "E"))  # 4 no estaba explorada
        self.assertNotEqual(cargado.conocimiento.exportar(), antes)
        self.assertTrue(cargado.ejecutar_accion("retroceder", ""))
        self.assertEqual(cargado.jugador.sala.id, 5)
        self.assertEqual(cargado.conocimiento.exportar(), antes)


# T087 a T090: replay de partidas cargadas (FR-017, SC-004, PR-12). El replay no recibe vista (PR-14).

class FuenteContada(FuenteDatosOffline):
    # Cuenta solicitudes (`solicitudes_realizadas`, de FuenteDatosOffline) y recibe el presupuesto como la
    # fuente HTTP, para comprobar el Principio VII sin red.
    presupuesto = None

    def fijar_presupuesto(self, presupuesto_solicitudes):
        self.presupuesto = presupuesto_solicitudes


class BaseReplay(BaseGuardado):

    def controlador_nuevo(self, nombre_log, buscar=None):
        from Controlador.ControladorPartida import ControladorPartida
        from tests.test_integracion import VistaFalsa
        controlador = ControladorPartida(self.gestor_nuevo(), VistaFalsa(), os.path.join(self.carpeta, nombre_log))
        if buscar is not None:
            controlador.buscar_ruta = buscar
        self.addCleanup(controlador._cerrar)
        return controlador

    def jugar(self, controlador, comandos):
        for comando in comandos:
            self.assertTrue(controlador.ejecutar(comando), comando)

    def replay(self, nombre_log, gestor=None):
        from main import ejecutar_replay
        return ejecutar_replay(os.path.join(self.carpeta, nombre_log), gestor or self.gestor_nuevo())

    def guardar_cargar_continuar(self, antes, despues, buscar=None):
        # Juega `antes` en la partida de self.partida, guarda, carga en otro controlador y juega `despues`.
        # Devuelve el controlador de la partida continuada (bitácora "continuada.log").
        self.jugar(self.controlador, antes)
        self.guardar()
        self.controlador._cerrar()
        continuada = self.controlador_nuevo("continuada.log", buscar)
        continuada.cargar(self.ruta())
        self.jugar(continuada, despues)
        return continuada


ANTES_ANTORCHA = [f"recoger {ID_ANTORCHA}", f"recoger {ID_PERGAMINO}", f"usar {ID_ANTORCHA}", "e", "abrir N"]
DESPUES_ANTORCHA = ["n", "atacar e-rata", "atacar e-rata", "esperar", "s", "esperar"]


class TestReplayDePartidasCargadas(BaseReplay):

    def test_fr017_sc004_escenario_us5_2_guardar_cargar_continuar_y_reproducir(self):
        # H1: antes del cambio el replay de una partida cargada divergía en todas las semillas probadas.
        for semilla in (1, 7, 42, 1234):
            with self.subTest(semilla=semilla):
                motor = self.partida(mapa_antorcha(), CONTENIDO_ANTORCHA, semilla=semilla)
                self.jugar(self.controlador, ANTES_ANTORCHA)
                self.assertTrue(motor.jugador.antorcha_encendida)  # encendida al guardar
                self.guardar()
                self.controlador._cerrar()

                continuada = self.controlador_nuevo("continuada.log")
                continuada.cargar(self.ruta())
                # apagada tras cargar (el atributo solo existe una vez encendida)
                self.assertFalse(getattr(continuada.motor.jugador, "antorcha_encendida", False))
                self.jugar(continuada, DESPUES_ANTORCHA)
                esperado = continuada.motor.obtener_estado_resumen()
                continuada._cerrar()

                repetido = self.replay("continuada.log")
                self.assertFalse(getattr(repetido.jugador, "antorcha_encendida", False))
                resumen = repetido.obtener_estado_resumen()
                for clave in ("reloj", "secuencia", "azar", "jugador", "conocimiento"):
                    self.assertEqual(resumen[clave], esperado[clave], clave)
                self.assertEqual(resumen, esperado)

    def test_fr017_fr030_fr031_ir_a_y_pergaminos_sin_y_con_carga(self):
        id_pergamino = f"obj-{CRIPTA_NIEBLA}-1-{PERGAMINO}-0"
        contenido = [contenido_sala(1, objetos=[PERGAMINO]),
                     contenido_sala(3, enemigos=["e-babosa"], tipo_enemigo=ENEMIGO_LENTO)]
        antes = [f"recoger {id_pergamino}", "e", "s", "o", "n", "ir a 4"]
        despues = ["retroceder", "ir a 1", "esperar", "ir a 4"]

        for con_carga in (False, True):
            with self.subTest(con_carga=con_carga):
                self.partida(mapa_cuadro(), contenido)
                self.controlador.buscar_ruta = buscador_prueba
                if con_carga:
                    final = self.guardar_cargar_continuar(antes, despues, buscador_prueba)
                    log = "continuada.log"
                else:
                    self.jugar(self.controlador, antes + despues)
                    final, log = self.controlador, "partida.log"
                esperado = final.motor.obtener_estado_resumen()
                final._cerrar()

                with open(os.path.join(self.carpeta, log), encoding="utf-8") as archivo:
                    texto_log = archivo.read()
                self.assertIn("# ir a 4", texto_log)
                self.assertEqual("@cargar" in texto_log.splitlines(), con_carga)

                resumen = self.replay(log).obtener_estado_resumen()
                for clave in ("reloj", "jugador", "conocimiento"):
                    self.assertEqual(resumen[clave], esperado[clave], clave)
                self.assertEqual(resumen, esperado)

    def test_fr017_principio_vii_varios_cargar_no_superan_el_presupuesto(self):
        self.partida(mapa_antorcha(), CONTENIDO_ANTORCHA)
        continuada = self.guardar_cargar_continuar(ANTES_ANTORCHA, ["n", "atacar e-rata"])
        segunda = self.ruta("segunda.cripta")
        self.assertTrue(continuada.guardar(segunda))
        continuada._cerrar()
        tercera = self.controlador_nuevo("tercera.log")
        tercera.cargar(segunda)
        self.jugar(tercera, ["atacar e-rata", "esperar", "s"])
        esperado = tercera.motor.obtener_estado_resumen()
        tercera._cerrar()

        with open(os.path.join(self.carpeta, "tercera.log"), encoding="utf-8") as archivo:
            self.assertEqual(archivo.read().splitlines().count("@cargar"), 2)

        fuente = FuenteContada(os.path.join(self.carpeta, "paquete"))
        gestor = GestorDatos(fuente, ruta_base=os.path.join(self.carpeta, "cache_presupuesto"), cache_size=25)
        repetido = self.replay("tercera.log", gestor)
        self.assertEqual(repetido.obtener_estado_resumen(), esperado)
        self.assertIsNotNone(fuente.presupuesto)
        self.assertLessEqual(fuente.solicitudes_realizadas, fuente.presupuesto,
                             f"{fuente.solicitudes_realizadas} solicitudes con presupuesto {fuente.presupuesto}")


class TestRiesgosDelReplay(BaseReplay):

    # T120: --bitacora igual a <guardado>.log es un error de uso (pedido de Persona D, FR-030 de la spec 004).
    # Reemplaza la prueba de T090 que lo tomaba como caso seguro. El código 1 de main se prueba en
    # tests/test_integracion.py.

    def guardado_con_su_bitacora(self):
        # Juega y guarda con la bitácora "partida.log"; devuelve los bytes de prueba.cripta.log.
        self.partida(mapa_antorcha(), CONTENIDO_ANTORCHA)
        primera = self.controlador_nuevo("partida.log")
        primera.nueva_partida(CRIPTA_NIEBLA, 7)
        self.jugar(primera, ANTES_ANTORCHA)
        self.assertTrue(primera.guardar(self.ruta()))
        primera._cerrar()
        return self.leer_bytes(self.ruta("prueba.cripta.log"))

    def leer_bytes(self, ruta):
        with open(ruta, "rb") as archivo:
            return archivo.read()

    def assertCargaRechazada(self, ruta_bitacora):
        copia = self.guardado_con_su_bitacora()
        segunda = self.controlador_nuevo(ruta_bitacora)
        with self.assertRaises(ValueError) as contexto:
            segunda.cargar(self.ruta())
        self.assertIn("prueba.cripta.log", str(contexto.exception))
        self.assertIsNone(segunda.motor)  # no se cargó nada
        self.assertIsNone(segunda.bitacora)
        self.assertEqual(self.leer_bytes(self.ruta("prueba.cripta.log")), copia)  # ni se tocó la bitácora

    def test_fr017_cargar_con_la_bitacora_del_guardado_se_rechaza(self):
        self.assertCargaRechazada("prueba.cripta.log")

    def test_fr017_cargar_con_ruta_equivalente_se_rechaza(self):
        self.assertCargaRechazada(os.path.join("sub", "..", "prueba.cripta.log"))

    @unittest.skipUnless(os.path.normcase("A") == "a", "solo donde las rutas no distinguen mayúsculas")
    def test_fr017_cargar_con_mayusculas_distintas_se_rechaza(self):
        self.assertCargaRechazada("PRUEBA.Cripta.LOG")

    def test_fr017_cargar_con_otra_bitacora_sigue_funcionando(self):
        copia = self.guardado_con_su_bitacora()
        segunda = self.controlador_nuevo("otra.log")
        segunda.cargar(self.ruta())
        self.jugar(segunda, DESPUES_ANTORCHA)
        esperado = segunda.motor.obtener_estado_resumen()
        segunda._cerrar()
        self.assertEqual(self.leer_bytes(self.ruta("prueba.cripta.log")), copia)
        self.assertEqual(self.replay("otra.log").obtener_estado_resumen(), esperado)

    def partida_con_bitacora(self, nombre_log):
        self.partida(mapa_antorcha(), CONTENIDO_ANTORCHA)
        controlador = self.controlador_nuevo(nombre_log)
        controlador.nueva_partida(CRIPTA_NIEBLA, 7)
        self.jugar(controlador, ANTES_ANTORCHA)
        return controlador

    def assertGuardadoRechazado(self, nombre_log, nombre_destino="prueba.cripta"):
        controlador = self.partida_con_bitacora(nombre_log)
        destino = self.ruta(nombre_destino)
        ruta_log = os.path.join(self.carpeta, nombre_log)
        antes_log = self.leer_bytes(ruta_log)
        reloj = controlador.motor.reloj
        with self.assertRaises(ValueError):
            controlador.guardar(destino)
        self.assertFalse(os.path.exists(destino))  # no se escribió el archivo de partida
        self.assertEqual(self.leer_bytes(ruta_log), antes_log)  # ni la bitácora
        self.assertEqual(controlador.motor.reloj, reloj)
        return controlador

    def test_fr017_guardar_con_la_bitacora_del_destino_se_rechaza(self):
        self.assertGuardadoRechazado("prueba.cripta.log")

    @unittest.skipUnless(os.path.normcase("A") == "a", "solo donde las rutas no distinguen mayúsculas")
    def test_fr017_guardar_con_mayusculas_distintas_se_rechaza(self):
        self.assertGuardadoRechazado("PRUEBA.CRIPTA.LOG")

    def test_fr017_guardar_rechazado_no_reemplaza_un_guardado_anterior(self):
        controlador = self.partida_con_bitacora("prueba.cripta.log")
        self.assertTrue(controlador.guardar(self.ruta("otro.cripta")))
        os.replace(self.ruta("otro.cripta"), self.ruta())
        anterior = self.leer_bytes(self.ruta())
        with self.assertRaises(ValueError):
            controlador.guardar(self.ruta())
        self.assertEqual(self.leer_bytes(self.ruta()), anterior)

    def test_fr017_comando_guardar_rechazado_muestra_error_y_la_partida_sigue(self):
        controlador = self.partida_con_bitacora("prueba.cripta.log")
        self.assertTrue(controlador.ejecutar(f"guardar {self.ruta()}"))
        nombre, argumentos = controlador.vista.lineas[-1]
        self.assertEqual(nombre, "mostrar_error")
        self.assertIn("prueba.cripta.log", argumentos[0])
        self.assertFalse(os.path.exists(self.ruta()))
        self.jugar(controlador, ["n"])  # la partida continúa
        self.assertTrue(controlador.guardar(self.ruta("otro.cripta")))

    def test_fr017_sc004_guardar_sin_cargar_no_toca_azar_ni_agenda(self):
        motor = self.partida(mapa_antorcha(), CONTENIDO_ANTORCHA)
        self.jugar(self.controlador, ANTES_ANTORCHA + ["n", "atacar e-rata"])
        antes = motor.obtener_estado_resumen()
        self.guardar()  # carga por _asegurar_salas_con_estado las salas que hagan falta
        despues = motor.obtener_estado_resumen()
        for clave in ("reloj", "secuencia", "azar", "eventos"):
            self.assertEqual(despues[clave], antes[clave], clave)

        self.jugar(self.controlador, ["atacar e-rata", "esperar", "s"])
        esperado = motor.obtener_estado_resumen()
        self.controlador._cerrar()
        self.assertEqual(self.replay("partida.log").obtener_estado_resumen(), esperado)


# T122: disposición final del CRPT 3 cerrada por Persona D (contracts/formato-partida.md, FR-016, PR-05).

class TestDisposicionCrpt3(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(self.carpeta.cleanup)
        self.ruta = os.path.join(self.carpeta.name, "crudo.cripta")

    def escribir(self, largos, offset_indice=None):
        # Encabezado sin salas, los tres largos con bloques de relleno y el índice (vacío) al final.
        from Persistencia.FormatoBinario import EncabezadoPartida
        cuerpo = b"".join(struct.pack("<I", largo) + bytes([65 + i]) * largo for i, largo in enumerate(largos))
        from Persistencia.FormatoBinario import TAMANO_ENCABEZADO
        if offset_indice is None:
            offset_indice = TAMANO_ENCABEZADO + len(cuerpo)
        encabezado = EncabezadoPartida(CRIPTA_NIEBLA, "v1", "cat-1", semilla=7, reloj=0,
                                       cantidad_salas=0, offset_indice=offset_indice)
        with open(self.ruta, "wb") as archivo:
            archivo.write(encabezado.to_bytes() + cuerpo)

    def lector(self):
        from Persistencia.ArchivoPartida import LectorPartida
        lector = LectorPartida(self.ruta)
        self.addCleanup(lector.cerrar)
        return lector

    def test_fr016_inicio_salas_sigue_la_formula_de_d(self):
        from Persistencia.FormatoBinario import TAMANO_ENCABEZADO
        for jugador, conocimiento, linea in [(0, 0, 0), (5, 0, 0), (0, 7, 0), (0, 0, 9), (3, 11, 6)]:
            with self.subTest(jugador=jugador, conocimiento=conocimiento, linea=linea):
                self.escribir([jugador, conocimiento, linea])
                lector = self.lector()
                self.assertEqual(lector._inicio_salas, TAMANO_ENCABEZADO + (4 + jugador) + (4 + conocimiento)
                                 + (4 + linea))
                # solo se leyeron el encabezado y los tres largos de 4 bytes, ningún bloque
                self.assertEqual(lector.bytes_leidos, TAMANO_ENCABEZADO + 12)
                lector.cerrar()

    def test_fr016_validar_encabezado_exige_indice_tras_los_tres_largos(self):
        from Persistencia.FormatoBinario import TAMANO_ENCABEZADO
        self.escribir([0, 0, 0], offset_indice=TAMANO_ENCABEZADO + 12)
        self.assertEqual(self.lector()._inicio_salas, TAMANO_ENCABEZADO + 12)  # el mínimo se acepta

        for offset in (TAMANO_ENCABEZADO + 11, TAMANO_ENCABEZADO + 8, TAMANO_ENCABEZADO, 0):
            with self.subTest(offset_indice=offset):
                self.escribir([0, 0, 0], offset_indice=offset)
                with self.assertRaises(VersionIncompatible):
                    self.lector()


if __name__ == "__main__":
    unittest.main()
