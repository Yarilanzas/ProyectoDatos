# escritura y lectura del archivo binario de la partida (S4.10)
# disposicion: [encabezado][largo jugador][bloque jugador][bloques de sala][indice de salas]
# el indice son registros de tamaño fijo ordenados por id de sala
# asi una sala se busca con busqueda binaria directo sobre el archivo, sin cargarlo completo

import struct
import os
import tempfile

from Modelo.ordenamiento import elegir_algoritmo
from Persistencia.FormatoBinario import EncabezadoPartida, VersionIncompatible, TAMANO_ENCABEZADO
from Persistencia.RegistroSala import RegistroSala
from Persistencia.RegistroJugador import RegistroJugador

# I id de sala | Q posicion del bloque en el archivo | I largo del bloque
FORMATO_ENTRADA = "<IQI"
TAMANO_ENTRADA = struct.calcsize(FORMATO_ENTRADA)

# I largo del bloque del jugador (0 si la partida no tiene jugador, p. ej. en el benchmark)
FORMATO_LARGO_JUGADOR = "<I"
TAMANO_LARGO_JUGADOR = struct.calcsize(FORMATO_LARGO_JUGADOR)


def guardar_partida(
    ruta, cripta_id, version_cripta, version_catalogo,
    semilla, reloj, registros, jugador=None
):
    # Ordena las salas por ID para construir el índice
    algoritmo = elegir_algoritmo(len(registros))
    ordenados, _ = algoritmo(
        registros, lambda registro: registro.sala_id
    )

    # Comprueba IDs repetidos.
    for i in range(1, len(ordenados)):
        if ordenados[i].sala_id == ordenados[i - 1].sala_id:
            raise ValueError( f"La sala {ordenados[i].sala_id} está repetida" )

    # Serializa todo antes de tocar el archivo final
    datos_jugador = jugador.to_bytes() if jugador is not None else b""
    bloques = []

    for registro in ordenados:
        bloques.append((registro.sala_id, registro.to_bytes()))

    # Calcula las posiciones de cada registro (las salas van despues del jugador)
    posicion = TAMANO_ENCABEZADO + TAMANO_LARGO_JUGADOR + len(datos_jugador)
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

    # Construye y valida el encabezado antes de escribir
    encabezado = EncabezadoPartida(cripta_id,version_cripta,version_catalogo, semilla,reloj,len(ordenados),offset_indice)

    datos_encabezado = encabezado.to_bytes()
    datos_indice = b"".join(entradas)

    # El archivo temporal se crea en el mismo directorio
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

            for datos in bloques_serializados:
                archivo.write(datos)

            archivo.write(datos_indice)

            archivo.seek(0)
            archivo.write(datos_encabezado)

            archivo.flush()
            os.fsync(archivo.fileno())

        # Reemplaza el archivo final solo si se escribió correctamente
        os.replace(ruta_temporal, ruta)
        ruta_temporal = None

    finally:
        # Limpia el temporal si hubo un error
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
            self._leer_largo_jugador()
        except Exception:
            self._archivo.close()
            raise

    def _validar_encabezado(self):
        encabezado = self.encabezado

        if encabezado.cantidad_salas < 0:
            raise VersionIncompatible("La cantidad de salas del archivo es inválida")

        if encabezado.offset_indice < TAMANO_ENCABEZADO + TAMANO_LARGO_JUGADOR:
            raise VersionIncompatible("La posición del índice está fuera del archivo" )

        fin_indice = (encabezado.offset_indice  + encabezado.cantidad_salas * TAMANO_ENTRADA)

        if fin_indice > self._tamano_archivo:
            raise VersionIncompatible( "El índice de salas está incompleto")

    def _leer_largo_jugador(self):
        # solo se leen 4 bytes, el bloque del jugador se lee cuando se pide
        datos = self._leer(TAMANO_ENCABEZADO, TAMANO_LARGO_JUGADOR)
        (self._largo_jugador,) = struct.unpack(FORMATO_LARGO_JUGADOR, datos)

        # las salas empiezan justo despues del jugador
        self._inicio_salas = TAMANO_ENCABEZADO + TAMANO_LARGO_JUGADOR + self._largo_jugador

        if self._inicio_salas > self.encabezado.offset_indice:
            raise VersionIncompatible("El bloque del jugador invade las salas del archivo")

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

        datos = self._leer(TAMANO_ENCABEZADO + TAMANO_LARGO_JUGADOR, self._largo_jugador)

        try:
            return RegistroJugador.from_bytes(datos)
        except (ValueError, struct.error, IndexError, UnicodeDecodeError) as error:
            raise VersionIncompatible("El registro del jugador está dañado") from error

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