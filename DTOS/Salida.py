COSTO_POR_DEFECTO = 100


def _es_entero(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)

class Salida:
    def __init__(self, sala_destino, cerrada, llave, cierre_automatico, costo=COSTO_POR_DEFECTO):
        self.sala_destino= sala_destino
        self.cerrada= cerrada
        self.llave= llave
        self.cierre_automatico= cierre_automatico
        self.costo = costo

    def a_json(self):
        return {
            "sala": self.sala_destino,
            "cerrada": self.cerrada,
            "llave": self.llave,
            "cierre_automatico": self.cierre_automatico,
            "costo": self.costo
        }

    @classmethod
    def desde_json(cls, datos):

        if "costo" in datos:
            costo = datos["costo"]
            if not _es_entero(costo) or costo < 1:
                raise ValueError(
                    f"Costo de salida inválido hacia la sala {datos.get('sala')!r}: {costo!r}. "
                    f"Debe ser un entero mayor o igual que 1."
                )
        else:
            costo = COSTO_POR_DEFECTO
        return cls(
            sala_destino=datos["sala"], #aqui si se exige que si o si tenga una sala, no puede quedar en none
            cerrada=datos.get("cerrada", False),
            llave=datos.get("llave"), #.get no exige que la llave esté, osea si no esta se declara como none
            cierre_automatico=datos.get("cierre_automatico"),
            costo=costo

        )


