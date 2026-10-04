from Modelo.Jugador import Jugador
from Modelo.Enemigo import Enemigo
from Modelo.MotorSimulacion import MotorSimulacion


# CREAR ACTORES


jugador = Jugador(id=1,vida=100,vida_max=100,ataque=20,defensa=10,velocidad=100)

enemigo = Enemigo(id=1,vida=50,vida_max=50,ataque=15,defensa=5,velocidad=150,comportamiento="errante")



# PRUEBA DE ACTORES

print("===== JUGADOR =====")
print("ID:", jugador.id)
print("Vida:", jugador.vida)
print("Vida máxima:", jugador.vida_max)
print("Ataque:", jugador.ataque)
print("Defensa:", jugador.defensa)
print("Velocidad:", jugador.velocidad)
print("Tiempo siguiente:", jugador.tiempo_siguiente)
print("Vivo:", jugador.vivo)


print("\n===== ENEMIGO =====")
print("ID:", enemigo.id)
print("Vida:", enemigo.vida)
print("Vida máxima:", enemigo.vida_max)
print("Ataque:", enemigo.ataque)
print("Defensa:", enemigo.defensa)
print("Velocidad:", enemigo.velocidad)
print("Comportamiento:", enemigo.comportamiento)
print("Activo:", enemigo.activo)
print("Vivo:", enemigo.vivo)

print("\n===== PRUEBA DEL MOTOR DE SIMULACIÓN =====")

motor = MotorSimulacion()
# El jugador comienza en tiempo 0
motor.programar_evento(tiempo=0, tipo="ACCION_JUGADOR", actor=jugador)

# El enemigo calcula su tiempo según su velocidad
motor.proxima_accion(enemigo)
motor.ejecutar()


# PRUEBA DE DAÑO

print("\n===== PRUEBA DE DAÑO =====")

enemigo.recibir_dano(20)
print("Vida del enemigo después de recibir 20 de daño:", enemigo.vida)
print("¿Está vivo?:",enemigo.esta_vivo())


enemigo.recibir_dano(30)
print("Vida del enemigo después de recibir otros 30:",enemigo.vida)
print("¿Está vivo?:",enemigo.esta_vivo())



# PRUEBA DE CURACIÓN

print("\n===== PRUEBA DE CURACIÓN =====")

jugador.recibir_dano(40)
print("Vida del jugador después de recibir daño:",jugador.vida)

jugador.curar(20)
print("Vida del jugador después de curarse:",jugador.vida)

jugador.curar(100)
print("Vida del jugador después de curarse 100:",jugador.vida)


