# Agenda con corte para consultar un instante entre dos decisiones (spec 004, T028; FR-001, FR-002, PR-04).
# Solo la usa un CLON: el clon cambia `agenda.__class__` y fija `corte`; la partida real nunca usa esta subclase.

from Modelo.AgendaEventos import AgendaEventos


class AgendaConCorte(AgendaEventos):
    """``AgendaEventos`` que oculta los eventos con ``tiempo > corte``.

    ``siguiente()`` devuelve ``None`` si el próximo evento tiene ``tiempo > corte``; un evento con ``tiempo == corte``
    se entrega. Como ``esta_vacia()`` y ``extraer()`` pasan por ``siguiente()``, el motor se detiene solo al llegar al
    corte. Los eventos ocultos siguen en el montículo (no se pierden): ``heap`` se puede leer completo.

    Uso: ``clon.agenda.__class__ = AgendaConCorte; clon.agenda.corte = t``.

    Complejidad: ``siguiente`` O(1) más lo de ``AgendaEventos`` (limpiar cancelados de la raíz).
    """

    corte = None  # sin corte (None) se comporta como AgendaEventos

    def siguiente(self):
        evento = super().siguiente()
        if evento is not None and self.corte is not None and evento.tiempo > self.corte:
            return None
        return evento

    def extraer(self):
        if self.siguiente() is None:
            return None
        return super().extraer()
