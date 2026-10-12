# guardado de la partida en JSON - existe solo para compararlo contra el formato binario (S4.10)
# guarda los mismos datos que ArchivoPartida: el encabezado y los registros de sala

import json
from Persistencia.RegistroSala import RegistroSala

def _sala_a_json(registro):
    return {
        "sala_id": registro.sala_id,
        "rastro": registro.rastro,
        "enemigos": registro.enemigos,
        "objetos": registro.objetos,
        "trampas": registro.trampas,
        "puertas": registro.puertas,
    }

# json devuelve listas, el registro usa tuplas
def _json_a_sala(datos):
    return RegistroSala(
        sala_id=datos["sala_id"],
        rastro=datos["rastro"],
        enemigos=[tuple(enemigo) for enemigo in datos["enemigos"]],
        objetos=datos["objetos"],
        trampas=[tuple(trampa) for trampa in datos["trampas"]],
        puertas=[tuple(puerta) for puerta in datos["puertas"]],
    )

def guardar_partida_json(ruta, cripta_id, version_cripta, version_catalogo, semilla, reloj, registros):
    datos = {
        "cripta_id": cripta_id,
        "version_cripta": version_cripta,
        "version_catalogo": version_catalogo,
        "semilla": semilla,
        "reloj": reloj,
        "salas": [_sala_a_json(registro) for registro in registros],
    }
    with open(ruta, "w", encoding="utf-8") as archivo:
        # compacto y sin escapar tildes, asi la comparacion de tamaño con el binario es justa
        json.dump(datos, archivo, separators=(",", ":"), ensure_ascii=False)


def cargar_partida_json(ruta):
    with open(ruta, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    return [_json_a_sala(sala) for sala in datos["salas"]]

# json no permite leer una sola parte, hay que cargar todo el archivo y recorrer la lista
def leer_sala_json(ruta, sala_id):
    with open(ruta, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    for sala in datos["salas"]:
        if sala["sala_id"] == sala_id:
            return _json_a_sala(sala)
    return None