#esto es una prueba!!

from Modelo.Inventario import Inventario, NodoInventario
from Modelo.retroceso import Historial, usar_pergamino


class JugadorDePrueba:
    """Clase mínima solo para probar — el motor de A tendrá la real."""
    def __init__(self, vida):
        self.vida = vida


def aplicar_dano(jugador, cantidad, historial):
    vida_anterior = jugador.vida
    jugador.vida = max(0, jugador.vida - cantidad)
    historial.registrar(
        deshacer=lambda: setattr(jugador, "vida", vida_anterior),
        description=f"daño de {cantidad}"
    )

def recoger_con_historial(inventario, nodo, historial):
    exito = inventario.recoge(nodo)
    if exito and nodo.clase != "pergamino_retroceso":
        historial.registrar(
            deshacer=lambda: inventario.suelta_nodo(nodo),
            description=f"recoger {nodo.nombre}"
        )
    return exito

if __name__ == "__main__":
    inv = Inventario(cap_max=10)
    historial = Historial()

    pergamino_1 = NodoInventario("p1", "itm_pergamino", "Pergamino 1", 1, 30, "pergamino_retroceso")
    pergamino_2 = NodoInventario("p2", "itm_pergamino", "Pergamino 2", 1, 30, "pergamino_retroceso")
    inv.recoge(pergamino_1)
    inv.recoge(pergamino_2)

    # --- acción 1 del jugador: recoge la daga ---
    historial.abrir_intervalo()
    daga = NodoInventario("i1", "itm_daga", "Daga oxidada", 2, 15, "arma")
    recoger_con_historial(inv, daga, historial)

    # --- acción 2 del jugador: recoge la armadura ---
    historial.abrir_intervalo()
    armadura = NodoInventario("i2", "itm_armadura", "Armadura de cuero", 5, 20, "armadura")
    recoger_con_historial(inv, armadura, historial)

    print("inventario antes de usar pergaminos:", [n.nombre for n in inv])

    # el jugador usa el primer pergamino → deshace la acción 2 (armadura)
    usar_pergamino(inv, historial, pergamino_1)
    print("después del 1er pergamino:", [n.nombre for n in inv])

    # el jugador usa el segundo pergamino, sin que haya pasado tiempo virtual
    # → debe deshacer la acción 1 (daga), NO volver a intentar deshacer la acción 2
    usar_pergamino(inv, historial, pergamino_2)
    print("después del 2do pergamino:", [n.nombre for n in inv])