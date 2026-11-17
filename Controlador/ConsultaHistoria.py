# Consulta del pasado de una bitácora: lo que hace `--replay <bitácora> --hasta <t>` (spec 004, T062; FR-007, FR-011, FR-012,
# FR-028, FR-030; PR-12; contracts/comandos-historia.md).
#
# Reproduce la bitácora **completa** con el `Reproductor`, un `ObservadorLinea` y una `LineaTiempo` de K dado, y da las líneas
# de texto de `main.py`: el resumen histórico del instante `t`, o el del estado final si `t` llega al final de la bitácora.
# El texto sale de `Vista/TextoResumen.py`, el mismo que usa el comando `historia`, y no se instancia ninguna vista
# (Principio II). No lee ni escribe nada fuera de su carpeta temporal.
#
#   - `t` menor que el reloj final: el resumen del instante `t`, igual que `historia t` en la partida jugada.
#   - `t` igual al reloj final: el resumen del estado final (con `Resultado:` si la partida terminó), sin aviso.
#   - `t` mayor que el reloj final: el aviso `La partida termina antes del instante <t> (la bitácora acaba en el reloj
#     <final>): se muestra el estado final.` y luego el resumen del estado final.
#
# La consulta se hace **antes** de cerrar el replay: el estado final y los clones de la línea todavía leen archivos abiertos
# (los temporales de las recargas de cada `@cargar` y las copias privadas de cada época). Por eso hay dos formas de usarla:
#
#   consulta = ConsultaHistoria(gestor, t, k)
#   lineas = consulta.reproducir(ruta)            # todo en uno; borra todo al terminar
#
# o, desde un replay que ya existe (`main.ejecutar_replay`, T063b), con las piezas:
#
#   observador = consulta.preparar(cripta_id)     # pasa `observador=` al `Reproductor`
#   ...                                           # `Reproductor.reproducir(ruta)`
#   consulta.al_terminar(motor)                   # justo después, antes de cerrar restauradores y borrar carpetas
#   consulta.cerrar()                             # al final
#
# Errores: `VersionIncompatible` (versiones distintas, código 2), `SinDatosParaHistoria` y `ErrorReconstruccion` (código 1) los
# lanza tal cual; los atrapa quien llama (`main.py`). Complejidad: reproducir la bitácora O(n · a + C · S) y la consulta
# O(log n + log C + S + K · a); memoria O(n + C · S).

import os
import shutil
import tempfile

from Bitacora.BitacoraPartida import leer_bitacora
from Bitacora.Reproductor import Reproductor
from Controlador.ObservadorLinea import ObservadorLinea
from DTOS.ResumenHistorico import REFERENCIA_FINAL
from Gestor.GestorHistorico import GestorHistorico
from Gestor.PreparadorPartida import cargar_partida, preparar_partida
from Modelo.LineaTiempo import K_POR_OMISION, LineaTiempo
from Modelo.ResumenHistorico import resumir
from Persistencia.ConversorPartida import RestauradorPartida
from Vista.TextoResumen import lineas_resumen

SUBCARPETA_RECARGAS = "recargas"


def aviso_de_fin(t, final):
    """El aviso de FR-012: `t` está más allá del final de la bitácora."""
    return f"La partida termina antes del instante {t} (la bitácora acaba en el reloj {final}): se muestra el estado final."


def _cerrar_restaurador(motor):
    if motor is not None and motor.restaurador is not None:
        motor.restaurador.cerrar()
        motor.restaurador = None


class ConsultaHistoria:
    """Una consulta `--hasta t` sobre una bitácora. `gestor` es el gestor de datos del replay (el mismo que `ejecutar_replay`
    da a `preparar_partida`); `t` un entero >= 0 ya validado; `k` el máximo de acciones entre puntos de control (solo cambia
    el costo, FR-028)."""

    def __init__(self, gestor, t, k=K_POR_OMISION):
        self._gestor = gestor
        self._t = t
        self._k = k
        self._linea = None
        self._observador = None
        self._carpeta = None
        self.lineas = None   # el resultado: las líneas a imprimir, tras `al_terminar`

    @property
    def carpeta(self):
        """Carpeta temporal propia, o None si no hay (todavía, o ya se cerró)."""
        return self._carpeta

    @property
    def observador(self):
        return self._observador

    @property
    def linea(self):
        return self._linea

    def preparar(self, cripta_id):
        """Crea la línea (con un gestor histórico sin red para sus clones), su observador y la carpeta temporal propia.
        Devuelve el `ObservadorLinea` que debe recibir el `Reproductor`. O(S + N + E) al iniciar el motor."""
        self.cerrar()
        historico = GestorHistorico.desde_gestor(self._gestor, cripta_id)
        self._carpeta = tempfile.mkdtemp(prefix="cripta_hasta_")
        self._linea = LineaTiempo(self._k, historico, RestauradorPartida)
        self._observador = ObservadorLinea(self._linea, self._carpeta)
        return self._observador

    def al_terminar(self, motor):
        """Con `motor` (el final del replay) ya reproducido, arma `lineas`. Hay que llamarlo antes de cerrar los
        restauradores y de borrar la carpeta temporal. O(log n + log C + S + K · a)."""
        linea = self._linea
        final = linea.reloj_actual
        t = self._t
        aviso = []
        if t < final:
            resumen = linea.consultar_instante(t, motor)
        else:
            if t > final:
                aviso = [aviso_de_fin(t, final)]
            resumen = resumir(motor, motor.reloj, (REFERENCIA_FINAL, None))
        self.lineas = aviso + lineas_resumen(resumen)

    def reproducir(self, ruta):
        """Reproduce la bitácora `ruta` completa y devuelve las líneas del resumen pedido. Todo lo que crea (restauradores,
        copias, carpeta) queda cerrado y borrado al volver, también si hay un error."""
        encabezado, _ = leer_bitacora(ruta)
        gestor = self._gestor
        observador = self.preparar(encabezado.cripta_id)
        recargas = os.path.join(self._carpeta, SUBCARPETA_RECARGAS)
        os.mkdir(recargas)
        abiertos = []   # motores que pueden tener un temporal abierto

        def fabrica_motor(cripta_id, semilla):
            return preparar_partida(cripta_id, semilla, gestor)

        def recargar(motor):
            # lo mismo que `ejecutar_replay`: repite la carga real (guarda el motor y lo vuelve a cargar)
            from Controlador.ControladorPartida import guardar_motor  # aquí y no arriba: evita el ciclo de imports
            temporal = os.path.join(recargas, f"recarga_{len(abiertos)}.cripta")
            guardar_motor(motor, temporal, gestor)
            _cerrar_restaurador(motor)  # el motor anterior ya no se usa
            nuevo = cargar_partida(temporal, gestor)
            abiertos.append(nuevo)
            return nuevo

        try:
            reproductor = Reproductor(fabrica_motor, gestor.version_cripta(encabezado.cripta_id),
                                      gestor.version_catalogo(), recargar=recargar, observador=observador)
            motor = reproductor.reproducir(ruta)
            self.al_terminar(motor)
        finally:
            self._linea.cerrar()  # suelta el clon (y el archivo que tenga abierto) antes de borrar
            for motor_abierto in abiertos:
                _cerrar_restaurador(motor_abierto)
            self.cerrar()
        return self.lineas

    def cerrar(self):
        """Borra las copias privadas y la carpeta temporal. Idempotente."""
        if self._linea is not None:
            self._linea.cerrar()
        if self._observador is not None:
            self._observador.cerrar()
        self._linea = None
        self._observador = None
        if self._carpeta is not None:
            shutil.rmtree(self._carpeta, ignore_errors=True)
            self._carpeta = None
