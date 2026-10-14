import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Modelo.Inventario import Inventario, NodoInventario
from Modelo.retroceso import Historial, usar_pergamino, soltar_reversible, equipar_reversible, recoger_reversible


def test_pergaminos_consecutivos():
    inv = Inventario(cap_max=10)
    historial = Historial()

    pergamino_1 = NodoInventario("p1", "itm_pergamino", "Pergamino 1", 1, 30, "pergamino_retroceso")
    pergamino_2 = NodoInventario("p2", "itm_pergamino", "Pergamino 2", 1, 30, "pergamino_retroceso")
    inv.recoge(pergamino_1)
    inv.recoge(pergamino_2)

    historial.abrir_intervalo()
    daga = NodoInventario("i1", "itm_daga", "Daga oxidada", 2, 15, "arma")
    recoger_reversible(inv, daga, historial)

    historial.abrir_intervalo()
    armadura = NodoInventario("i2", "itm_armadura", "Armadura de cuero", 5, 20, "armadura")
    recoger_reversible(inv, armadura, historial)

    print("inventario antes de usar pergaminos:", [n.nombre for n in inv])

    usar_pergamino(inv, historial, pergamino_1)
    print("después del 1er pergamino:", [n.nombre for n in inv])  # sin Armadura

    usar_pergamino(inv, historial, pergamino_2)
    print("después del 2do pergamino:", [n.nombre for n in inv])  # sin Daga tampoco


def test_historial_vacio_no_rompe():
    historial = Historial()
    print("puede_deshacer (recién creado):", historial.puede_deshacer())
    print("resultado de deshacer_ultimo:", historial.deshacer_ultimo())

    historial.abrir_intervalo()
    historial.registrar(deshacer=lambda: print("deshaciendo cambio único"))
    print("puede_deshacer (con 1 intervalo):", historial.puede_deshacer())
    historial.deshacer_ultimo()

    print("puede_deshacer (después de deshacer el único):", historial.puede_deshacer())
    print("resultado de deshacer_ultimo (otra vez, sin nada):", historial.deshacer_ultimo())


def test_recoger_reversible_con_inventario_lleno():
    inv = Inventario(cap_max=2)
    historial = Historial()
    historial.abrir_intervalo()

    a = NodoInventario("a", "t1", "Objeto A", 1, 1, "arma")
    b = NodoInventario("b", "t2", "Objeto B", 1, 1, "arma")
    c = NodoInventario("c", "t3", "Objeto C", 1, 1, "arma")  # no debería entrar

    print("recoger A:", recoger_reversible(inv, a, historial))
    print("recoger B:", recoger_reversible(inv, b, historial))
    print("recoger C (lleno):", recoger_reversible(inv, c, historial))
    print("contenido:", [n.nombre for n in inv])
    print("cantidad:", inv._cantidad)

    historial.deshacer_ultimo()
    print("contenido después de deshacer:", [n.nombre for n in inv])

def test_pergamino_no_corrompe_lista_al_deshacer_soltar():
    inv = Inventario(cap_max=10)
    historial = Historial()

    pergamino = NodoInventario("p1", "itm_pergamino", "Pergamino", 1, 30, "pergamino_retroceso")
    daga = NodoInventario("i1", "itm_daga", "Daga", 2, 15, "arma")
    armadura = NodoInventario("i2", "itm_armadura", "Armadura", 5, 20, "armadura")

    inv.recoge(pergamino)
    inv.recoge(daga)
    inv.recoge(armadura)
    print("orden inicial:", [n.nombre for n in inv])  # Pergamino, Daga, Armadura

    historial.abrir_intervalo()
    soltar_reversible(inv, daga, historial)
    print("después de soltar daga:", [n.nombre for n in inv])  # Pergamino, Armadura

    usar_pergamino(inv, historial, pergamino)
    resultado = [n.nombre for n in inv]
    print("después de usar el pergamino:", resultado)

    # el pergamino se consume, la daga vuelve a estar en la lista
    assert "Pergamino" not in resultado
    assert "Daga" in resultado
    assert "Armadura" in resultado
    assert len(resultado) == 2
    print("OK: la lista no se corrompió al deshacer con el pergamino de por medio\n")

if __name__ == "__main__":
    print("--- pergaminos consecutivos ---")
    test_pergaminos_consecutivos()
    print("\n--- historial vacío no rompe ---")
    test_historial_vacio_no_rompe()
    print("\n--- recoger_reversible con inventario lleno ---")
    test_recoger_reversible_con_inventario_lleno()
    print("\n--- pergamino no corrompe la lista al deshacer un soltar ---")
    test_pergamino_no_corrompe_lista_al_deshacer_soltar()