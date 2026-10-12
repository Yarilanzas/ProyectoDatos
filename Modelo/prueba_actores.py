
from Modelo.MotorSimulacion import MotorSimulacion

motor = MotorSimulacion(semilla=123)

assert motor.gestor_datos.estado_juego is motor

print("Conexión correcta")

motor.es_ficha_activa = lambda id_ficha: id_ficha == "ficha_activa"

assert motor.gestor_datos.esta_en_uso("ficha_activa") is True
assert motor.gestor_datos.esta_en_uso("ficha_inactiva") is False

print("Consulta de fichas activas correcta")