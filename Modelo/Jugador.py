
from Modelo.Actor import Actor
from Modelo.Inventario import Inventario


class Jugador(Actor):

    def __init__(self, id, vida, vida_max, ataque, defensa,velocidad, sala=None, capacidad_inventario=10):

        super().__init__(id, vida, vida_max, ataque, defensa, velocidad, sala)
        self.inventario = Inventario(capacidad_inventario)
