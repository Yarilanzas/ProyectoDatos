from Modelo.MotorSimulacion import MotorSimulacion
from Modelo.Enemigo import Enemigo
from Modelo.Jugador import Jugador
from DTOS.SalaEsqueleto import SalaEsqueleto
from DTOS.Salida import Salida


#SALIDAS

salida_norte = Salida(sala_destino=2, cerrada=False, llave=None,cierre_automatico=None)
salida_sur = Salida(sala_destino=3,cerrada=True,llave=None,cierre_automatico=None)


sala1 = SalaEsqueleto(id=1,nombre="Sala 1",salidas={ "N": salida_norte,  "S": salida_sur })
sala2 = SalaEsqueleto(id=2,nombre="Sala 2",salidas={})

motor = MotorSimulacion(123)
motor.salas = [sala1, sala2]


jugador = Jugador(id=1,vida=100,vida_max=100,ataque=10,defensa=5,velocidad=100,sala=sala1)

# Asignar jugador al motor
motor.jugador = jugador

enemigo = Enemigo(id=1, vida=100,vida_max=100,ataque=10,defensa=5, velocidad=100,comportamiento="errante",sala=sala1)


# =====================================================
# PRUEBA 1: SALIDAS ABIERTAS


print("========== PRUEBA 1 ==========")

salidas = motor.salidas_abiertas(sala1)

print("Salidas abiertas:")

for direccion, salida in salidas:
    print("Dirección:", direccion, "| Destino:", salida.sala_destino)


# =====================================================
# PRUEBA 2: ELEGIR SALIDA


print("\n========== PRUEBA 2 ==========")

resultado = motor.salida_errante(enemigo)

if resultado is None:
    print("No hay salidas abiertas")

else:
    direccion, salida = resultado

    print("Dirección elegida:", direccion)
    print("Sala destino:", salida.sala_destino)


# =====================================================
# PRUEBA 3: ENEMIGO Y JUGADOR EN LA MISMA SALA


print("\n========== PRUEBA 3 ==========")

print("Sala del jugador:", jugador.sala.id)
print("Sala del enemigo:", enemigo.sala.id)

accion = motor.accion_enemigo(enemigo, jugador)

print("Acción del enemigo:", accion)


# =====================================================
# PRUEBA 4: ENEMIGO EN OTRA SALA


print("\n========== PRUEBA 4 ==========")

enemigo.sala = sala2

print("Sala del jugador:", jugador.sala.id)
print("Sala del enemigo:", enemigo.sala.id)

accion = motor.accion_enemigo(enemigo, jugador)


print("Acción del enemigo:", accion)


# =====================================================
# PRUEBA 5: MOVIMIENTO


print("\n========== PRUEBA 5 ==========")

salas = [sala1, sala2]

enemigo.sala = sala1

print(
    "Sala antes de mover:",
    enemigo.sala.id
)

resultado = motor.salida_errante(enemigo)

if resultado is None:

    print("El enemigo no puede moverse")

else:

    direccion, salida = resultado

    print("Salida elegida:", direccion)
    print("ID destino:", salida.sala_destino)

    movio = motor.mover_enemigo( enemigo, salas, salida)

    if movio:

        print( "Sala después de mover:", enemigo.sala.id )

    else:

        print("No se encontró la sala destino")

