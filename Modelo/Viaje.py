# Orden «ir a» en ejecución. FR-021 a FR-029, FR-031, PR-09. Ver data-model.md (Viaje).
# Vive solo mientras dura el comando: no se guarda ni se reanuda (FR-031). Cada paso lo ejecuta el
# controlador como un `mover` ordinario (FR-025); aquí están las reglas de parada, que son del juego.
# No conoce la vista (Principio II).

from Modelo.rutas_ir_a import primer_paso

# Motivos de parada (FR-027).
DESTINO = "DESTINO"                # (a) la sala actual es el destino
ENEMIGOS = "ENEMIGOS"              # (b) había enemigos vivos al entrar
DANO = "DANO"                      # (c) la vida bajó durante el paso
SIN_RUTA = "SIN_RUTA"              # (d) el recálculo no encuentra ruta
FIN_PARTIDA = "FIN_PARTIDA"        # (e) victoria o derrota
PASO_RECHAZADO = "PASO_RECHAZADO"  # (f) el motor rechazó el `mover`

# Rechazos de la orden (FR-022). Ninguno consume tiempo ni va a la bitácora (SC-005).
RECHAZO_DESCONOCIDA = "DESCONOCIDA"  # inexistente, desconocida, avistada o id no válido: un solo caso
RECHAZO_ACTUAL = "ACTUAL"            # es la sala actual
RECHAZO_SIN_RUTA = "SIN_RUTA"        # explorada, sin ruta conocida


class Viaje:
    """Una orden «ir a» aceptada: `destino` (sala explorada), `buscar` (con la firma de `primer_paso`) y
    `motivo` (None mientras sigue).

    Uso, por cada paso:
        paso = viaje.siguiente_paso()          # None si se detiene sin moverse (SIN_RUTA)
        aceptado = <mover paso.direccion>
        viaje.terminar_paso(aceptado)          # motivo, o None si sigue

    La ruta se recalcula antes de cada paso con el conocimiento vigente (FR-026). El primer cálculo es el
    que hizo `MotorSimulacion.preparar_viaje` al aceptar la orden, inmediatamente antes del primer paso,
    así que se usa tal cual en vez de repetirlo.

    Complejidad: siguiente_paso cuesta un cálculo de `buscar` (salvo el primero); terminar_paso, O(1).
    """

    def __init__(self, motor, destino, buscar=primer_paso, paso=None):
        self.motor = motor
        self.destino = destino
        self.buscar = buscar
        self.motivo = None
        self._paso = paso
        self._vida_antes = None

    def siguiente_paso(self):
        if self.motivo is not None:
            return None

        paso, self._paso = self._paso, None
        if paso is None:
            paso = self.buscar(self.motor.grafo_conocido(), self.motor.jugador.sala, self.destino)

        if paso is None:
            # FR-027d: se evalúa antes del paso, así que no consume tiempo.
            self.motivo = SIN_RUTA
            return None

        self._vida_antes = self.motor.jugador.vida
        return paso

    def terminar_paso(self, aceptado):
        # Prioridad cuando coinciden varias: FIN_PARTIDA, DANO, ENEMIGOS, DESTINO (contracts/comandos.md).
        motor = self.motor

        if not aceptado:
            self.motivo = PASO_RECHAZADO  # FR-027f: el rechazo no consumió tiempo
        elif motor.estado_partida() != "en_curso":
            self.motivo = FIN_PARTIDA
        elif motor.jugador.vida < self._vida_antes:
            self.motivo = DANO
        elif motor.enemigos_al_entrar:
            self.motivo = ENEMIGOS
        elif motor.jugador.sala is self.destino:
            self.motivo = DESTINO

        return self.motivo
