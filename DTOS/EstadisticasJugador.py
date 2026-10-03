
class EstadisticasJugador:
    def __init__(self, vida,ataque, defensa, velocidad):
        self.vida = vida
        self.ataque  = ataque
        self.defensa = defensa
        self.velocidad = velocidad

    @classmethod
    def desde_json(cls, datos):
        return cls(
            vida=datos["vida_max"],
            ataque=datos["ataque"],
            defensa=datos["defensa"],
            velocidad=datos["velocidad"],
        )