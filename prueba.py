#esto es una prueba!!

from Modelo.Inventario import Inventario, NodoInventario
from Modelo.retroceso import Historial


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
    if exito:
        historial.registrar(
            deshacer=lambda: inventario.suelta_actual() if inventario.actual() is nodo else None,
            description=f"recoger {nodo.nombre}"
        )
    return exito


if __name__ == "__main__":
    jugador = JugadorDePrueba(vida=30)
    inv = Inventario(cap_max=5)
    historial = Historial()

    # --- acción del jugador: se mueve, abre un intervalo nuevo ---
    historial.abrir_intervalo()

    daga = NodoInventario("i1", "itm_daga", "Daga oxidada", 2, 15, "arma")
    recoger_con_historial(inv, daga, historial)
    print("vida antes de daño:", jugador.vida)
    print("inventario antes de deshacer:", [n.nombre for n in inv])

    # simulamos que, dentro del mismo intervalo, algo le hace daño al jugador
    aplicar_dano(jugador, 7, historial)
    print("vida después de daño:", jugador.vida)

    # --- el jugador usa un pergamino ---
    historial.deshacer_ultimo()

    print("vida después de deshacer:", jugador.vida)          # esperado: 30
    print("inventario después de deshacer:", [n.nombre for n in inv])  # esperado: []