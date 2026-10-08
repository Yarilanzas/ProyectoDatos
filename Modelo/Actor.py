class Actor:

    def __init__(self,id,vida,vida_max,ataque,defensa,velocidad, sala=None):

        self.id = id
        self.vida = vida
        self.vida_max = vida_max
        self.ataque = ataque
        self.defensa = defensa
        self.velocidad = velocidad
        self.sala = sala
        self.tiempo_siguiente = 0
        self.vivo = True
        self.evento_actual = None

    def recibir_dano(self, dano):
        
        self.vida -= dano
        if self.vida <= 0:
            self.vida = 0
            self.vivo = False

    def curar(self, cantidad):

        self.vida += cantidad
        if self.vida > self.vida_max:
            self.vida = self.vida_max

    def esta_vivo(self):
        return self.vivo