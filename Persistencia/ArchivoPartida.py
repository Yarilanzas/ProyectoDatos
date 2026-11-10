# Escritura y lectura del archivo binario de la partida (S4.10)
# disposicion (CRPT 3, contracts/formato-partida.md):
# [encabezado][largo jugador][jugador][largo conocimiento][conocimiento][largo linea de tiempo][linea de tiempo][salas][indice]
# el indice son registros de tamaño fijo ordenados por id de sala asi una sala se busca con busqueda binaria directo sobre el archivo, sin cargarlo completo
# la linea de tiempo es de Persona D (spec 004): aqui es un bloque opaco, se escribe con largo 0 y al leer solo se salta con su largo

import struct
import os
import tempfile

from Modelo.ordenamiento import elegir_algoritmo
from Persistencia.FormatoBinario import EncabezadoPartida, VersionIncompatible, TAMANO_ENCABEZADO
from Persistencia.RegistroConocimiento import RegistroConocimiento
from Persistencia.RegistroSala import RegistroSala
from Persistencia.RegistroJugador import RegistroJugador

# I id de sala | Q posicion del bloque en el archivo | I largo del bloque
FORMATO_ENTRADA = "<IQI"
TAMANO_ENTRADA = struct.calcsize(FORMATO_ENTRADA)

# I largo de un bloque: jugador (0 si la partida no tiene jugador, p. ej. en el benchmark),
# conocimiento (0 si no hay conocimiento) y linea de tiempo (opaco, por ahora siempre 0)
FORMATO_LARGO_JUGADOR = "<I"
TAMANO_LARGO_JUGADOR = struct.calcsize(FORMATO_LARGO_JUGADOR)
FORMATO_LARGO_BLOQUE = "<I"
TAMANO_LARGO_BLOQUE = struct.calcsize(FORMATO_LARGO_BLOQUE)

# lo minimo antes de las salas: el encabezado y los tres campos de largo
INICIO_MINIMO_SALAS = TAMANO_ENCABEZADO + TAMANO_LARGO_JUGADOR + 2 * TAMANO_LARGO_BLOQUE


def guardar_partida(
    ruta, cripta_id, version_cripta, version_catalogo,
    semilla, reloj, registros, jugador=None, conocimiento=None
):
    """Escribe el CRPT 3. `conocimiento` es un RegistroConocimiento (o cualquier objeto con
    `to_bytes()`); None escribe largo 0. La linea de tiempo se escribe con largo 0.

    O(s log s + B): ordenar las s salas con `elegir_algoritmo` y escribir los B bytes del archivo.
    """
    # ordena las salas por ID para construir el índice
    algoritmo = elegir_algoritmo(len(registros))
    ordenados, _ = algoritmo(
        registros, lambda registro: registro.sala_id
    )

    # comprueba IDs repetidos
    for i in range(1, len(ordenados)):
        if ordenados[i].sala_id == ordenados[i - 1].sala_id:
            raise ValueError( f"La sala {ordenados[i].sala_id} está repetida" )

    # serializa todo antes de tocar el archivo final
    datos_jugador = jugador.to_bytes() if jugador is not None else b""
    datos_conocimiento = conocimiento.to_bytes() if conocimiento is not None else b""
    datos_linea_tiempo = b""  # bloque de Persona D: por ahora vacio
    bloques = []

    for registro in ordenados:
        bloques.append((registro.sala_id, registro.to_bytes()))

    # calcula las posiciones de cada registro (las salas van despues de los tres bloques con largo)
    posicion = (INICIO_MINIMO_SALAS + len(datos_jugador) + len(datos_conocimiento)
                + len(datos_linea_tiempo))
    entradas = []
    bloques_serializados = []

    for sala_id, datos in bloques:
        entrada = struct.pack(
            FORMATO_ENTRADA,
            sala_id,
            posicion,
            len(datos)
        )

        entradas.append(entrada)
        bloques_serializados.append(datos)
        posicion += len(datos)

    offset_indice = posicion

    # construye y valida el encabezado antes de escribir
    encabezado = EncabezadoPartida(cripta_id,version_cripta,version_catalogo, semilla,reloj,len(ordenados),offset_indice)

    datos_encabezado = encabezado.to_bytes()
    datos_indice = b"".join(entradas)

    # el archivo temporal se crea en el mismo directorio
    directorio = os.path.dirname(os.path.abspath(ruta))
    ruta_temporal = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=directorio,
            prefix=".partida_",
            suffix=".tmp",
            delete=False
        ) as archivo:
            ruta_temporal = archivo.name

            archivo.write(bytes(TAMANO_ENCABEZADO))
            archivo.write(struct.pack(FORMATO_LARGO_JUGADOR, len(datos_jugador)))
            archivo.write(datos_jugador)
            archivo.write(struct.pack(FORMATO_LARGO_BLOQUE, len(datos_conocimiento)))
            archivo.write(datos_conocimiento)
            archivo.write(struct.pack(FORMATO_LARGO_BLOQUE, len(datos_linea_tiempo)))
            archivo.write(datos_linea_tiempo)

            for datos in bloques_serializados:
                archivo.write(datos)

            archivo.write(datos_indice)

            archivo.seek(0)
            archivo.write(datos_encabezado)

            archivo.flush()
            os.fsync(archivo.fileno())

        # reemplaza el archivo final solo si se escribió correctamente
        os.replace(ruta_temporal, ruta)
        ruta_temporal = None

    finally:
        # limpia el temporal si hubo un error
        if ruta_temporal is not None and os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)

class LectorPartida:
    def __init__(self, ruta):
        self.ruta = ruta
        self._archivo = open(ruta, "rb")
        self._tamano_archivo = os.fstat(self._archivo.fileno() ).st_size
        self.bytes_leidos = 0

        try:
            self.encabezado = EncabezadoPartida.desde_archivo(self._archivo)
            self.bytes_leidos = TAMANO_ENCABEZADO
            self._validar_encabezado()
            self._leer_largos()
        except Exception:
            self._archivo.close()
            raise

    def _validar_encabezado(self):
        encabezado = self.encabezado

        if encabezado.cantidad_salas < 0:
            raise VersionIncompatible("La cantidad de salas del archivo es inválida")

        # el indice va despues de los tres campos de largo (jugador, conocimiento y linea de tiempo)
        if encabezado.offset_indice < INICIO_MINIMO_SALAS:
            raise VersionIncompatible("La posición del índice está fuera del archivo" )

        fin_indice = (encabezado.offset_indice  + encabezado.cantidad_salas * TAMANO_ENTRADA)

        if fin_indice > self._tamano_archivo:
            raise VersionIncompatible( "El índice de salas está incompleto")

    def _leer_largo(self, posicion, nombre):
        # lee un campo de largo y comprueba que su bloque no invada las salas. Devuelve donde
        # empieza el bloque y su largo. O(1): solo 4 bytes
        datos = self._leer(posicion, TAMANO_LARGO_BLOQUE)
        (largo,) = struct.unpack(FORMATO_LARGO_BLOQUE, datos)
        inicio = posicion + TAMANO_LARGO_BLOQUE

        if inicio + largo > self.encabezado.offset_indice:
            raise VersionIncompatible(f"El bloque {nombre} invade las salas del archivo")

        return inicio, largo

    def _leer_largos(self):
        # solo se leen los tres campos de largo (12 bytes); los bloques se leen cuando se piden
        self._inicio_jugador, self._largo_jugador = self._leer_largo(TAMANO_ENCABEZADO, "del jugador")
        self._inicio_conocimiento, self._largo_conocimiento = self._leer_largo(
            self._inicio_jugador + self._largo_jugador, "de conocimiento")
        # linea de tiempo de Persona D: opaca, solo se salta con su largo
        inicio_linea, largo_linea = self._leer_largo(
            self._inicio_conocimiento + self._largo_conocimiento, "de línea de tiempo")

        # las salas empiezan justo despues de la linea de tiempo
        self._inicio_salas = inicio_linea + largo_linea

    def _leer(self, posicion, cantidad):
        if posicion < 0 or cantidad < 0:
            raise VersionIncompatible("Se intentó leer una posición inválida")

        if posicion + cantidad > self._tamano_archivo:
            raise VersionIncompatible( "La lectura excede el tamaño del archivo")

        self._archivo.seek(posicion)
        datos = self._archivo.read(cantidad)
        self.bytes_leidos += len(datos)

        if len(datos) != cantidad:
            raise VersionIncompatible("El archivo está incompleto o dañado")

        return datos

    def leer_jugador(self):
        if self._largo_jugador == 0:
            return None

        datos = self._leer(self._inicio_jugador, self._largo_jugador)

        try:
            return RegistroJugador.from_bytes(datos)
        except (ValueError, struct.error, IndexError, UnicodeDecodeError) as error:
            raise VersionIncompatible("El registro del jugador está dañado") from error

    def leer_conocimiento(self):
        """RegistroConocimiento del bloque, leido de una sola vez; None si el largo es 0.

        Un bloque truncado, con un valor invalido o con bytes sobrantes lanza VersionIncompatible
        (FR-016). O(c) en los c bytes del bloque; no lee bloques de sala.
        """
        if self._largo_conocimiento == 0:
            return None

        datos = self._leer(self._inicio_conocimiento, self._largo_conocimiento)

        try:
            return RegistroConocimiento.from_bytes(datos)
        except ValueError as error:
            raise VersionIncompatible(f"El bloque de conocimiento está dañado: {error}") from error

    def buscar_sala(self, sala_id):
        inicio = 0
        fin = self.encabezado.cantidad_salas

        while inicio < fin:
            medio = (inicio + fin) // 2
            posicion_indice = (self.encabezado.offset_indice + medio * TAMANO_ENTRADA)
            datos = self._leer(posicion_indice, TAMANO_ENTRADA )
            id_medio, posicion, largo = struct.unpack(FORMATO_ENTRADA, datos)

            if (posicion < self._inicio_salas or largo <= 0 or posicion + largo > self.encabezado.offset_indice):
                raise VersionIncompatible("Una entrada del índice contiene una posición de sala inválida")

            if id_medio == sala_id:
                return posicion, largo

            if id_medio < sala_id:
                inicio = medio + 1
            else:
                fin = medio

        return None

    def leer_sala(self, sala_id):
        ubicacion = self.buscar_sala(sala_id)

        if ubicacion is None:
            return None

        posicion, largo = ubicacion
        datos = self._leer(posicion, largo)

        try:
            registro = RegistroSala.from_bytes(datos)
        except (ValueError, struct.error, IndexError) as error:
            raise VersionIncompatible(f"El registro de la sala {sala_id} está dañado") from error

        if registro.sala_id != sala_id:
            raise VersionIncompatible( "El ID de la sala no coincide con el índice")
        return registro

    def ids_salas(self):
        # lee solo el indice (12 bytes por sala), no los bloques de las salas
        cantidad = self.encabezado.cantidad_salas
        datos = self._leer(self.encabezado.offset_indice, cantidad * TAMANO_ENTRADA)

        ids = []
        for i in range(cantidad):
            id_sala, _, _ = struct.unpack_from(FORMATO_ENTRADA, datos, i * TAMANO_ENTRADA)
            ids.append(id_sala)
        return ids

    def leer_todas_salas(self):
        cantidad = self.encabezado.cantidad_salas
        offset = self.encabezado.offset_indice
        largo_indice = cantidad * TAMANO_ENTRADA

        datos = self._leer(offset, largo_indice)

        registros = []
        id_anterior = None
        fin_anterior = self._inicio_salas

        for i in range(cantidad):
            posicion_indice = i * TAMANO_ENTRADA

            id_sala, posicion, largo = struct.unpack_from(FORMATO_ENTRADA,datos,posicion_indice)

            # El índice debe estar ordenado y sin IDs repetidos
            if id_anterior is not None and id_sala <= id_anterior:
                raise VersionIncompatible("El índice no está ordenado o contiene IDs repetidos")

            # Los registros se escriben físicamente en orden de ID
            # Esto detecta bloques en conflicto o que invaden el índice
            if (posicion != fin_anterior or largo <= 0 or posicion + largo > offset):
                raise VersionIncompatible( f"Entrada inválida en el índice para la sala {id_sala}")

            bloque = self._leer(posicion, largo)

            try:
                registro = RegistroSala.from_bytes(bloque)
            except (ValueError, struct.error, IndexError) as error:
                raise VersionIncompatible( f"Registro binario inválido para la sala {id_sala}") from error

            if registro.sala_id != id_sala:
                raise VersionIncompatible("El ID del índice no coincide con el registro de sala")

            registros.append(registro)
            id_anterior = id_sala
            fin_anterior = posicion + largo

        if fin_anterior != offset:
            raise VersionIncompatible("Hay bytes sin asignar entre los registros y el índice")

        return registros

    def cerrar(self):
        if not self._archivo.closed:
            self._archivo.close()

    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, traza):
        self.cerrar()