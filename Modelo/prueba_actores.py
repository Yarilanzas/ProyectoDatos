
from Modelo.MotorSimulacion import MotorSimulacion
from Modelo.Jugador import Jugador
from DTOS.SalaEsqueleto import SalaEsqueleto
from DTOS.Salida import Salida
from Modelo.Inventario import NodoInventario

def probar_movimiento():
    # Crear dos salas conectadas.
    sala1 = SalaEsqueleto(1, "Entrada", {})
    sala2 = SalaEsqueleto(2, "Pasillo", {})

    sala1.salidas["E"] = Salida(2, False, None, None)
    sala2.salidas["O"] = Salida(1, False, None, None)

    # Crear jugador y motor.
    jugador = Jugador(
        id="jugador",
        vida=100,
        vida_max=100,
        ataque=10,
        defensa=5,
        velocidad=10,
        sala=sala1
    )

    pergamino = NodoInventario(
        instancia_id="pergamino-1",
        tipo_id="pergamino_retroceso",
        nombre="Pergamino de retroceso",
        peso=1,
        valor=0,
        clase="pergamino_retroceso"
    )

    jugador.inventario.recoge(pergamino)

    motor = MotorSimulacion(semilla=123)
    motor.iniciar_partida(jugador, [sala1, sala2], [])

    # Estado inicial.
    assert jugador.sala is sala1
    assert sala1.rastro == 0

    reloj_inicial = motor.reloj
    rastro1_inicial = sala1.rastro
    rastro2_inicial = getattr(sala2, "rastro", None)


    # Guardar el estado inicial.
    reloj_inicial = motor.reloj
    sala_inicial = jugador.sala
    rastro1_inicial = getattr(sala1, "rastro", None)
    rastro2_inicial = getattr(sala2, "rastro", None)

    def eventos_actuales():
        return sorted(
            (
                evento.tiempo,
                evento.secuencia,
                evento.tipo,
                None if evento.actor is None else evento.actor.id,
                evento.cancelado
            )
            for evento in motor.agenda.heap
        )

    eventos_iniciales = eventos_actuales()

    # Ejecutar el movimiento.
    assert motor.ejecutar_accion("mover", "E")
    assert jugador.sala is sala2

    print("Después del movimiento:")
    print("Reloj:", motor.reloj)
    print("Sala:", jugador.sala.id)
    print("Rastro sala 1:", sala1.rastro)
    print("Rastro sala 2:", sala2.rastro)

    # Usar el pergamino.
    resultado = motor.usar_pergamino_retroceso(pergamino)
    print("\n¿Se ejecutó el retroceso?", resultado)

    print("Después del retroceso:")
    print("Reloj:", motor.reloj)
    print("Sala:", jugador.sala.id)
    print("Rastro sala 1:", getattr(sala1, "rastro", None))
    print("Rastro sala 2:", getattr(sala2, "rastro", None))
    print("Eventos:", eventos_actuales())

    # Comprobar restauración.
    assert resultado
    assert jugador.sala is sala_inicial
    assert motor.reloj == reloj_inicial
    assert getattr(sala1, "rastro", None) == rastro1_inicial
    assert getattr(sala2, "rastro", None) == rastro2_inicial

    print("\nPosición, reloj y rastros restaurados.")



if __name__ == "__main__":
    probar_movimiento()
