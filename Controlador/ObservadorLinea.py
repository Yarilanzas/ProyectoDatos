# Adaptador entre el controlador (o el Reproductor) y la línea de tiempo (spec 004, T034; contracts/interfaz-linea.md;
# FR-025, FR-016, PR-12).
#
# La partida jugada, el replay y la reconstrucción al cargar registran por el MISMO camino, que es lo que garantiza FR-025:
#
#     al_crear_motor(motor)                       -> linea.iniciar(motor)
#     despues_de_accion(motor, nombre, argumento) -> linea.registrar_accion(...) o, si es «retroceder»,
#                                                    linea.registrar_retroceso(motor)
#     despues_de_carga(motor)                     -> copia privada del archivo cargado + linea.registrar_carga(motor, ruta)
#
# No guarda referencias al motor: cada aviso trae el motor vivo (en `despues_de_carga`, el NUEVO) y se lo pasa a la línea.
# El controlador llama a `despues_de_accion` DESPUÉS de que `ejecutar_accion` devolvió True y de `bitacora.registrar`;
# una acción rechazada no llega aquí.
#
# Nota: `registrar_retroceso` y `registrar_carga` de `LineaTiempo` son de tareas posteriores (T047 y T082); hasta entonces
# solo `retroceder` y `@cargar` fallarían con AttributeError si se enganchara el observador en el juego real, por eso el
# enganche (T035) va después de T047.

import os
import shutil


class ObservadorLinea:
    """Traduce los tres avisos a la `LineaTiempo`. `carpeta_copias` es una carpeta (la crea y la borra quien la pasa) donde
    se guardan las copias privadas de los archivos cargados; sin ella la época se abre sin copia (``ruta_copia = None``).

    Decisión pendiente de aprobación (M3): la ruta del archivo cargado se toma de ``motor.restaurador.ruta`` (así lo hace
    ``guardar_motor`` con ``anterior.ruta``); si el motor no tiene restaurador, la época se abre sin copia privada.
    """

    def __init__(self, linea, carpeta_copias=None):
        self._linea = linea
        self._carpeta_copias = carpeta_copias
        self._copias = []  # rutas de las copias privadas hechas, para borrarlas al cerrar

    @property
    def linea(self):
        return self._linea

    def al_crear_motor(self, motor):
        self._linea.iniciar(motor)

    def despues_de_accion(self, motor, nombre, argumento=""):
        if nombre == "retroceder":
            self._linea.registrar_retroceso(motor)
        else:
            self._linea.registrar_accion(motor, nombre, argumento)

    def despues_de_carga(self, motor):
        self._linea.registrar_carga(motor, self._copia_privada(motor))

    def _copia_privada(self, motor):
        restaurador = getattr(motor, "restaurador", None)
        ruta = getattr(restaurador, "ruta", None)
        if ruta is None or self._carpeta_copias is None:
            return None
        destino = os.path.join(self._carpeta_copias, f"epoca_{len(self._copias) + 1}.cripta")
        shutil.copyfile(ruta, destino)
        self._copias.append(destino)
        return destino

    def cerrar(self):
        """Borra las copias privadas hechas por este observador."""
        for ruta in self._copias:
            try:
                os.remove(ruta)
            except OSError:
                pass
        self._copias = []
