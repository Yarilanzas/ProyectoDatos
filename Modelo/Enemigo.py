from Modelo.Actor import Actor


class Enemigo(Actor):

    def __init__(self,id,vida,vida_max,ataque,defensa,velocidad,comportamiento,sala=None ):

        super().__init__(id,vida,vida_max,ataque,defensa,velocidad,sala)
        self.comportamiento = comportamiento # pueden ser guardian, errante o rastreador
        self.activo = False # para cuando aun no este activado, cuando no entre en la sala el jugador