# Contrato: interfaz de la ruta de «ir a»

Esta interfaz es la frontera de la **decisión pendiente D-PEND-01** ([research.md](../research.md#r6-búsqueda-de-la-ruta-de-ir-a-fr-023-fr-024-fr-026)).
Permite adoptar la implementación compartida (A) o la separada (B) cambiando solo el cuerpo de `Modelo/rutas_ir_a.py`.

## Función

```text
primer_paso(grafo, origen, destino) -> Paso | None
```

| Parámetro | Contenido |
|-----------|-----------|
| `grafo` | Objeto con la interfaz de grafo, abajo |
| `origen` | Sala actual |
| `destino` | Sala destino, distinta de `origen` |

`Paso` tiene `direccion`, `destino` (la vecina a la que se da el paso) y `costo_total` de la ruta completa. `None`
significa que no hay ruta. La función no modifica nada.

`Viaje` la recibe como parámetro: `Viaje(..., buscar=primer_paso)`. Las pruebas pueden inyectar un buscador de prueba.

## Interfaz de grafo

```text
grafo.ordinal(sala) -> entero en [0, grafo.cantidad_salas)
grafo.cantidad_salas -> entero
grafo.aristas(sala) -> iterable de (direccion, sala_destino, costo)
```

`GrafoConocido` la implementa. `aristas` entrega solo lo transitable (FR-023, FR-011, FR-029): salas exploradas y
salidas recordadas abiertas. La búsqueda no conoce la niebla, ni puertas, ni costos por defecto. El costo llega ya
resuelto por `motor.costo_salida`.

`ordinal` existe para que una implementación indexe sus arreglos sin usar `dict`. El orden de `aristas` es
determinista, pero no está ordenado por id: el desempate es responsabilidad de la búsqueda.

## Obligaciones de toda implementación

| # | Obligación | FR / Principio |
|---|------------|----------------|
| 1 | Devolver el primer paso de una ruta de costo total mínimo | FR-024 |
| 2 | Entre rutas de igual costo, el primer paso va a la vecina de menor id; entre dos salidas hacia esa misma vecina con igual costo, gana la primera en el orden N, S, E, O | FR-024 |
| 3 | Devolver `None` si el destino no es alcanzable | FR-022, FR-027d |
| 4 | Usar solo `grafo`, sin leer el mapa real | FR-012 |
| 5 | Ser determinista | Principio III |
| 6 | No usar `dict`/`set` como índice, `heapq`, `bisect`, `collections`, `networkx`, ni `sorted()`/`list.sort()` como sustituto. La cola de prioridad va a mano | Principio I |
| 7 | Documentar su complejidad | Principio I |

Precondición: costos no negativos. El costo es un entero mayor o igual que 1 (enunciado §3.1).

El desempate entre **dos salidas a la misma vecina con igual costo** lo fija FR-024 (P-03 resuelta): gana la primera en
el orden N, S, E, O, sin importar el orden en que `aristas` las entregue.

## Prueba de contrato

`tests/test_ruta_contrato.py` ejercita la interfaz, sin mirar la implementación, con grafos de prueba pequeños:

- ruta única, ruta más barata con más saltos, y sin ruta;
- empate con primeros pasos a vecinas distintas, en cualquier orden de `aristas`;
- empate decidido lejos del origen: el criterio es el **primer** paso, no el último;
- dos salidas a la misma vecina con igual costo: gana la primera en el orden N, S, E, O;
- costos distintos de 100, para demostrar que nada asume el valor por defecto.

Si se elige la opción A, la misma tabla de casos de desempate debe correr también contra el cazador.

## Qué cambia según D-PEND-01

| | Opción A: compartida | Opción B: separada |
|---|---|---|
| `Modelo/rutas_ir_a.py` | Delega en el módulo común | Contiene la búsqueda |
| Cola de prioridad | La del módulo común | `Modelo/ColaPrioridad.py` |
| `Viaje`, `GrafoConocido`, controlador, pruebas, M4 | Sin cambios | Sin cambios |
