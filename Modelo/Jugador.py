from Modelo.Actor import Actor


class Jugador(Actor):

    def __init__(self,id,vida,vida_max,ataque,defensa,velocidad,sala=None ):

        super().__init__(id,vida,vida_max,ataque,defensa,velocidad,sala)