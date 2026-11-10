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
from tests.utiles_niebla import CRIPTA_NIEBLA, LLAVE, contenido_sala
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


# T068, T070 a T072: guardar y cargar el CRPT 3.

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


if __name__ == "__main__":
    unittest.main()
