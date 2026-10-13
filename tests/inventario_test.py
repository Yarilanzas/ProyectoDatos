import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modelo.Inventario import Inventario, NodoInventario

from Modelo.Inventario import Inventario, NodoInventario


def test_inventario_vacio():
    inv = Inventario(cap_max=5)

    print("actual (vacío):", inv.actual())
    print("avanza (vacío):", inv.avanza())
    print("retrocede (vacío):", inv.retrocede())
    print("suelta_actual (vacío):", inv.suelta_actual())
    print("equipar_actual (vacío):", inv.equipar_actual())


def test_equipar_cabeza_no_crea_enlace_a_si_mismo():
    inv = Inventario(cap_max=5)
    a = NodoInventario("a", "t1", "A", 1, 1, "arma")
    inv.recoge(a)
    inv._cursor = a

    inv.equipar_actual()
    inv.equipar_actual()  # equipar DE NUEVO lo que ya es cabeza

    print("siguiente de A:", a.siguiente)  # esperado: None
    print("anterior de A:", a.anterior)    # esperado: None


def test_reinsertar_incrementa_cantidad():
    inv = Inventario(cap_max=5)
    b = NodoInventario("b", "t2", "B", 1, 1, "arma")
    inv.recoge(b)
    print("cantidad tras recoger:", inv._cantidad)  # 1

    inv.suelta_nodo(b)
    print("cantidad tras soltar:", inv._cantidad)   # 0

    inv._reinsertar(b, None, None)
    print("cantidad tras reinsertar:", inv._cantidad)  # esperado: 1


def test_arma_y_armadura_equipadas_simultaneamente():
    inv = Inventario(cap_max=5)
    daga = NodoInventario("i1", "t1", "Daga", 2, 15, "arma")
    espada = NodoInventario("i2", "t2", "Espada", 3, 25, "arma")
    armadura = NodoInventario("i3", "t3", "Armadura", 5, 20, "armadura")

    inv.recoge(daga)
    inv.recoge(espada)
    inv.recoge(armadura)

    inv._cursor = daga
    inv.equipar_actual()
    print("arma equipada:", inv.arma_equipada().nombre)       # Daga
    print("armadura equipada:", inv.armadura_equipada())      # None

    inv._cursor = armadura
    inv.equipar_actual()
    print("arma equipada:", inv.arma_equipada().nombre)       # Daga (sigue igual)
    print("armadura equipada:", inv.armadura_equipada().nombre)  # Armadura

    inv._cursor = espada
    inv.equipar_actual()
    print("arma equipada:", inv.arma_equipada().nombre)       # Espada
    print("daga sigue en inventario:", any(n.nombre == "Daga" for n in inv))  # True


if __name__ == "__main__":
    print("--- inventario vacío ---")
    test_inventario_vacio()
    print("\n--- equipar cabeza, sin enlace a sí mismo ---")
    test_equipar_cabeza_no_crea_enlace_a_si_mismo()
    print("\n--- _reinsertar incrementa cantidad ---")
    test_reinsertar_incrementa_cantidad()
    print("\n--- arma y armadura simultáneas ---")
    test_arma_y_armadura_equipadas_simultaneamente()