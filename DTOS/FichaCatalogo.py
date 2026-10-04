class FichaCatalogo:
    def __init__(self, id, clase, nombre):
        self.id = id
        self.clase = clase
        self.nombre = nombre

        @classmethod
        def desde_json(cls, datos):
            if datos["clase"] == "enemigo":
                return FichaEnemigo.desde_json(datos)
            elif datos["clase"] == "arma":
                return FichaArma.desde_json(datos)
            elif datos["clase"] == "armadura":
                return FichaArmadura.desde_json(datos)
            elif datos["clase"] == "pocion":
                return FichaPocion.desde_json(datos)
            elif datos["clase"] == "antidoto":
                return FichaAntidoto.desde_json(datos)
            elif datos["clase"] == "llave":
                return FichaLlave.desde_json(datos)
            elif datos["clase"] == "pergamino_retroceso":
                return FichaPergamino.desde_json(datos)
            elif datos["clase"] == "trampa":
                return FichaTrampa.desde_json(datos)


class FichaEnemigo(FichaCatalogo):
    def __init__(self, id, clase, nombre, vida_max, ataque, defensa, velocidad, comportamiento, suelta):
        super().__init__(id, clase, nombre)
        self.vida_max = vida_max
        self.ataque = ataque
        self.defensa = defensa
        self.velocidad = velocidad
        self.comportamiento = comportamiento
        self.suelta = suelta

    @classmethod
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            clase=datos["clase"],
            nombre=datos["nombre"],
            vida_max=datos["vida_max"],
            ataque=datos["ataque"],
            defensa=datos["defensa"],
            velocidad=datos["velocidad"],
            comportamiento=datos["comportamiento"],
            suelta=datos["suelta"]
        )

class FichaArma(FichaCatalogo):
    def __init__(self, id, clase, nombre, peso, valor, ataque_bonus):
        super().__init__(id, clase, nombre)
        self.peso = peso
        self.valor = valor
        self.ataque_bonus = ataque_bonus


    @classmethod
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            clase=datos["clase"],
            nombre=datos["nombre"],
            peso=datos["peso"],
            valor=datos["valor"],
            ataque_bonus=datos["ataque_bonus"]
        )

class FichaArmadura(FichaCatalogo):
    def __init__(self, id, clase, nombre, peso, valor, defensa_bonus):
        super().__init__(id, clase, nombre)
        self.peso = peso
        self.valor = valor
        self.defensa_bonus = defensa_bonus


    @classmethod
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            clase=datos["clase"],
            nombre=datos["nombre"],
            peso=datos["peso"],
            valor=datos["valor"],
            defensa_bonus=datos["defensa_bonus"]

        )

class FichaPocion(FichaCatalogo):
    def __init__(self, id, clase, nombre, peso, valor,cura, modificador_velocidad, duracion):
        super().__init__(id, clase, nombre)
        self.peso = peso
        self.valor = valor
        self.cura = cura
        self.modificador_velocidad = modificador_velocidad
        self.duracion = duracion


    @classmethod
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            clase=datos["clase"],
            nombre=datos["nombre"],
            peso=datos["peso"],
            valor=datos["valor"],
            cura=datos["cura"],
            modificador_velocidad=datos["modificador_velocidad"],
            duracion=datos["duracion"]
        )
class FichaAntidoto(FichaCatalogo):
    def __init__(self, id, clase, nombre, peso, valor):
        super().__init__(id, clase, nombre)
        self.peso = peso
        self.valor = valor


    @classmethod
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            clase=datos["clase"],
            nombre=datos["nombre"],
            peso=datos["peso"],
            valor=datos["valor"]

        )


class FichaLlave(FichaCatalogo):
    def __init__(self, id, clase, nombre, peso, valor, abre):
        super().__init__(id, clase, nombre)
        self.peso = peso
        self.valor = valor
        self.abre = abre


    @classmethod
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            clase=datos["clase"],
            nombre=datos["nombre"],
            peso=datos["peso"],
            valor=datos["valor"],
            abre=datos["abre"]
        )

class FichaAntorcha(FichaCatalogo):
    def __init__(self, id, clase, nombre, peso, valor, duracion):
        super().__init__(id, clase, nombre)
        self.peso = peso
        self.valor = valor
        self.duracion = duracion


    @classmethod
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            clase=datos["clase"],
            nombre=datos["nombre"],
            peso=datos["peso"],
            valor=datos["valor"],
            duracion=datos["duracion"]
        )
class FichaPergamino(FichaCatalogo):
    def __init__(self, id, clase, nombre, peso, valor):
        super().__init__(id, clase, nombre)
        self.peso = peso
        self.valor = valor


    @classmethod
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            clase=datos["clase"],
            nombre=datos["nombre"],
            peso=datos["peso"],
            valor=datos["valor"]
        )


class FichaTrampa(FichaCatalogo):
    def __init__(self, id, clase, nombre, danio, rearme):
        super().__init__(id, clase, nombre)
        self.danio = danio
        self.rearme = rearme


    @classmethod
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            clase=datos["clase"],
            nombre=datos["nombre"],
            danio=datos["daño"],
            rearme=datos["rearme"]
        )