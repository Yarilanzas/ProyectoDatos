

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modelo.Inventario import Inventario, NodoInventario
from Modelo.retroceso import Historial


def test_inventario_ida_y_vuelta():
    inv = Inventario(cap_max=5)

    daga = NodoInventario("i1", "itm_daga", "Daga", 2, 15, "arma", ataque_bonus=3)
    armadura = NodoInventario("i2", "itm_armadura", "Armadura", 5, 20, "armadura", defensa_bonus=2)
    pocion = NodoInventario("i3", "itm_pocion", "Poción", 1, 5, "pocion")

    inv.recoge(daga)
    inv.recoge(armadura)
    inv.recoge(pocion)

    inv._cursor = daga
    inv.equipar_actual()   # daga equipada
    inv._cursor = armadura
    inv.equipar_actual()   # armadura equipada
    inv._cursor = pocion   # cursor queda en la poción

    original = [n.nombre for n in inv]
    print("inventario original:", original)
    print("arma equipada (original):", inv.arma_equipada().nombre)
    print("armadura equipada (original):", inv.armadura_equipada().nombre)
    print("cursor original:", inv.actual().nombre)

    datos = inv.to_bytes()
    print("tamaño en bytes:", len(datos))

    inv2 = Inventario.from_bytes(datos)

    restaurado = [n.nombre for n in inv2]
    print("inventario restaurado:", restaurado)
    print("arma equipada (restaurado):", inv2.arma_equipada().nombre)
    print("armadura equipada (restaurado):", inv2.armadura_equipada().nombre)
    print("cursor restaurado:", inv2.actual().nombre)
    print("bonos de la daga restaurada:", inv2.arma_equipada().ataque_bonus)

    assert original == restaurado, "el orden no coincide"
    assert inv2.arma_equipada().nombre == "Daga"
    assert inv2.armadura_equipada().nombre == "Armadura"
    assert inv2.actual().nombre == "Poción"
    assert inv2.arma_equipada().ataque_bonus == 3
    print("OK: inventario sobrevive la vuelta completa a bytes\n")


def test_inventario_vacio_ida_y_vuelta():
    inv = Inventario(cap_max=5)
    datos = inv.to_bytes()
    inv2 = Inventario.from_bytes(datos)
    print("inventario vacío restaurado:", [n.nombre for n in inv2])
    print("cursor:", inv2.actual())
    assert list(inv2) == []
    assert inv2.actual() is None
    print("OK: inventario vacío no rompe la serialización\n")


def test_historial_stub():
    historial = Historial()
    historial.abrir_intervalo()
    historial.registrar(deshacer=lambda: None, description="algo que no debería sobrevivir")

    datos = historial.to_bytes()
    print("bytes del historial:", datos)

    historial2 = Historial.from_bytes(datos)
    print("puede_deshacer tras cargar:", historial2.puede_deshacer())
    assert historial2.puede_deshacer() is False
    print("OK: historial se reconstruye vacío, como se decidió\n")


if __name__ == "__main__":
    test_inventario_ida_y_vuelta()
    test_inventario_vacio_ida_y_vuelta()
    test_historial_stub()
    print("Todas las pruebas de serialización pasaron.")