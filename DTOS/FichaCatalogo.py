def _es_entero(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)

class FichaCatalogo:
    def __init__(self, id, clase, nombre):
        self.id = id
        self.clase = clase
        self.nombre = nombre

    def a_json(self):
        return {
            "id": self.id,
            "clase": self.clase,
            "nombre": self.nombre
        }
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
        elif datos["clase"] == "antorcha":
            return FichaAntorcha.desde_json(datos)
        return None


class FichaEnemigo(FichaCatalogo):
    def __init__(self, id, clase, nombre, vida_max, ataque, defensa, velocidad, comportamiento, suelta, rango=None):
        super().__init__(id, clase, nombre)
        self.vida_max = vida_max
        self.ataque = ataque
        self.defensa = defensa
        self.velocidad = velocidad
        self.comportamiento = comportamiento
        self.suelta = suelta
        self.rango = rango

    def a_json(self):
        datos = super().a_json()
        datos.update({
            "vida_max": self.vida_max,
            "ataque": self.ataque,
            "defensa": self.defensa,
            "velocidad": self.velocidad,
            "comportamiento": self.comportamiento
        })
        if self.suelta is not None:
            datos["suelta"] = self.suelta
        if self.rango is not None:
            datos["rango"] = self.rango
        return datos

    @classmethod
    def desde_json(cls, datos):
        rango = None
        if datos["comportamiento"] == "cazador":
            if "rango" not in datos:
                raise ValueError(
                    f"El cazador {datos.get('id')!r} no declara rango. "
                    f"Debe ser un entero mayor o igual que 0."
                )
            rango = datos["rango"]
            if not _es_entero(rango) or rango < 0:
                raise ValueError(
                    f"Rango inválido para el cazador {datos.get('id')!r}: {rango!r}. "
                    f"Debe ser un entero mayor o igual que 0."
                )

        return cls(
            id=datos["id"],
            clase=datos["clase"],
            nombre=datos["nombre"],
            vida_max=datos["vida_max"],
            ataque=datos["ataque"],
            defensa=datos["defensa"],
            velocidad=datos["velocidad"],
            comportamiento=datos["comportamiento"],
            suelta=datos.get("suelta"),  # no siempre van a soltar cosas por eso el . get
            rango=rango
        )
class FichaArma(FichaCatalogo):
    def __init__(self, id, clase, nombre, peso, valor, ataque_bonus):
        super().__init__(id, clase, nombre)
        self.peso = peso
        self.valor = valor
        self.ataque_bonus = ataque_bonus

    def a_json(self):
        datos = super().a_json()
        datos.update({"peso": self.peso, "valor": self.valor, "ataque_bonus": self.ataque_bonus})
        return datos
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

    def a_json(self):
        datos = super().a_json()
        datos.update({"peso": self.peso, "valor": self.valor, "defensa_bonus": self.defensa_bonus})
        return datos

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

    def a_json(self):
        datos = super().a_json()
        datos.update({"peso": self.peso, "valor": self.valor})
        if self.cura is not None:
            datos["cura"] = self.cura
        if self.modificador_velocidad is not None:
            datos["modificador_velocidad"] = self.modificador_velocidad
        if self.duracion is not None:
            datos["duracion"] = self.duracion
        return datos
    @classmethod
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            clase=datos["clase"],
            nombre=datos["nombre"],
            peso=datos["peso"],
            valor=datos["valor"],
            cura=datos.get("cura"),
            modificador_velocidad=datos.get("modificador_velocidad"),
            duracion=datos.get("duracion")
        )
class FichaAntidoto(FichaCatalogo):
    def __init__(self, id, clase, nombre, peso, valor):
        super().__init__(id, clase, nombre)
        self.peso = peso
        self.valor = valor

    def a_json(self):
        datos = super().a_json()
        datos.update({"peso": self.peso,
                      "valor": self.valor})
        return datos
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

    def a_json(self):
        datos = super().a_json()
        datos.update({"peso": self.peso, "valor": self.valor, "abre": self.abre})
        return datos

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

    def a_json(self):
        datos = super().a_json()
        datos.update({"peso": self.peso,
                      "valor": self.valor,
                      "duracion": self.duracion})
        return datos

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

    def a_json(self):
        datos = super().a_json()
        datos.update({"peso": self.peso,
                      "valor": self.valor})
        return datos


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

    def a_json(self):
        datos = super().a_json()
        datos["daño"] = self.danio
        if self.rearme is not None:
            datos["rearme"] = self.rearme
        return datos

    @classmethod
    def desde_json(cls, datos):
        return cls(
            id=datos["id"],
            clase=datos["clase"],
            nombre=datos["nombre"],
            danio=datos["daño"],
            rearme=datos.get("rearme")
        )