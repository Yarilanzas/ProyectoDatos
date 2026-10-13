import sys
import os
#provicional:
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Cache.Estructuras import Queue

ORDEN_DIRECCIONES = ["N", "S", "E", "O"]




class PlanificadorPrecarga:
    def __init__(self, esqueleto, limite=10):
        self.esqueleto = esqueleto
        self.limite = limite

    def _buscar_sala(self, id_sala):
        for sala in self.esqueleto:
            if sala.id == id_sala:
                return sala
        return None

    def planificar(self, sala_actual, ya_cargadas):
        a_pedir = []
        if sala_actual not in ya_cargadas:
            a_pedir.append(sala_actual)

        visitadas = [sala_actual]
        cola = Queue()
        cola.enqueue(sala_actual)

        while not cola.is_empty() and len(a_pedir) < self.limite:
            id_actual = cola.dequeue()
            sala = self._buscar_sala(id_actual)
            if sala is None:
                continue

            for direccion in ORDEN_DIRECCIONES:
                if direccion not in sala.salidas:
                    continue
                destino = sala.salidas[direccion].sala_destino
                if destino in visitadas:
                    continue

                visitadas.append(destino)
                cola.enqueue(destino)
                if destino not in ya_cargadas and len(a_pedir) < self.limite:
                    a_pedir.append(destino)

        return a_pedir



'''if __name__ == "__main__":
    fuente = FuenteDatosHTTP()
    esqueleto = fuente.obtener_esqueleto_cripta("cripta-01")

    planificador = PlanificadorPrecarga(esqueleto)
    print(planificador.planificar(1, []))  # nada cargado
    print(planificador.planificar(1, [1, 2]))'''