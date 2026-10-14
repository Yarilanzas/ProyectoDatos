# Vista (MVC) en consola: solo LEE el estado del motor y lo muestra.
# No modifica nada ni decide reglas; eso lo hace el controlador.
# entrada/salida se pueden reemplazar (por ejemplo en las pruebas) para no usar el teclado.

NOMBRES_DIRECCION = {"N": "norte", "S": "sur", "E": "este", "O": "oeste"}
MENSAJES_EN_PANTALLA = 6  # el registro guarda 20 (S4.8); en cada turno se muestran los ultimos

AYUDA = """Comandos:
  mover N|S|E|O    (atajos: n s e o)     abrir N|S|E|O
  atacar ID        recoger ID            soltar ID
  equipar ID       usar ID               esperar
  retroceder       (usa un pergamino de retroceso)
  inventario [peso|valor|nombre]         mensajes
  red              (solicitudes y cache)
  guardar [ARCHIVO]                      cargar ARCHIVO
  ayuda            salir"""


class VistaConsola:

    def __init__(self, entrada=input, salida=print):
        self._entrada = entrada
        self._salida = salida

    def mostrar(self, texto=""):
        self._salida(texto)

    def pedir_texto(self, mensaje):
        try:
            return self._entrada(mensaje)
        except EOFError:
            return None  # fin de la entrada (Ctrl+D o un archivo de comandos que termino)

    def pedir_comando(self):
        return self.pedir_texto("> ")

    def mostrar_bienvenida(self):
        self.mostrar("=== CRIPTA ===  (escriba 'ayuda' para ver los comandos)")

    def mostrar_ayuda(self):
        self.mostrar(AYUDA)

    def mostrar_aviso(self, texto):
        self.mostrar(f"* {texto}")

    def mostrar_error(self, texto):
        self.mostrar(f"! Error: {texto}")

    def mostrar_criptas(self, criptas):
        self.mostrar("Criptas disponibles:")
        for cripta in criptas:
            self.mostrar(f"  {cripta.id:<12} {cripta.nombre} ({cripta.salas} salas, {cripta.dificultad})")

    def _texto_salidas(self, sala):
        partes = []
        for direccion, salida in sala.salidas.items():
            estado = "cerrada" if salida.cerrada else "abierta"
            llave = getattr(salida, "llave", None)
            if salida.cerrada and llave:
                estado += f", llave {llave}"
            nombre = NOMBRES_DIRECCION.get(direccion, direccion)
            partes.append(f"{direccion} {nombre} ({estado})")
        return " | ".join(partes) if partes else "ninguna"

    def _texto_nodo(self, nodo, inventario=None):
        texto = f"{nodo.nombre} [{nodo.instancia_id}]"
        if inventario is not None:
            if nodo is inventario.arma_equipada() or nodo is inventario.armadura_equipada():
                texto += " (equipado)"
        return texto

    def mostrar_estado(self, motor):
        jugador = motor.jugador
        sala = jugador.sala

        self.mostrar()
        self.mostrar(f"--- Sala {sala.id}: {getattr(sala, 'nombre', '')} ---   reloj {motor.reloj}")
        self.mostrar(f"Vida {jugador.vida}/{jugador.vida_max}   acciones {motor.acciones_jugador}"
                     f"   derrotados {motor.enemigos_derrotados}")
        self.mostrar(f"Salidas: {self._texto_salidas(sala)}")

        enemigos = motor.obtener_enemigos(sala=sala, solo_vivos=True)
        if enemigos:
            self.mostrar("Enemigos: " + ", ".join(
                f"{enemigo.id} ({enemigo.tipo_id}, vida {enemigo.vida})" for enemigo in enemigos))

        suelo = motor.obtener_objetos_suelo(sala)
        if suelo:
            self.mostrar("En el suelo: " + ", ".join(self._texto_nodo(nodo) for nodo in suelo))

        inventario = jugador.inventario
        nodos = list(inventario)
        if nodos:
            self.mostrar("Inventario: " + ", ".join(self._texto_nodo(nodo, inventario) for nodo in nodos))
        else:
            self.mostrar("Inventario: vacío")

        mensajes = motor.mensajes.ultimos()
        for texto in mensajes[-MENSAJES_EN_PANTALLA:]:
            self.mostrar(f"  · {texto}")

    def mostrar_mensajes(self, mensajes):
        self.mostrar("Últimos mensajes:")
        for texto in mensajes:
            self.mostrar(f"  · {texto}")

    def mostrar_inventario_ordenado(self, nodos, criterio, inventario):
        # vista_ordenada (persona C) no cambia el orden real del inventario
        self.mostrar(f"Inventario por {criterio}:")
        for nodo in nodos:
            self.mostrar(f"  {self._texto_nodo(nodo, inventario):<45} peso {nodo.peso:<4} valor {nodo.valor}")

    def mostrar_red(self, resumen):
        presupuesto = "sin límite" if resumen.presupuesto is None else resumen.presupuesto
        self.mostrar(f"Solicitudes: {resumen.solicitudes} de {presupuesto}   "
                     f"caché: {resumen.aciertos_cache} aciertos / {resumen.fallos_cache} fallos")

    def mostrar_fin(self, resumen, resumen_red=None):
        if resumen["resultado"] == "victoria":
            self.mostrar("*** ¡Escapaste de la cripta! ***")
        else:
            self.mostrar("*** Has muerto en la cripta ***")
        self.mostrar(f"Acciones: {resumen['acciones']}   enemigos derrotados: "
                     f"{resumen['enemigos_derrotados']}   tiempo final: {resumen['tiempo_final']}")
        if resumen_red is not None:
            self.mostrar_red(resumen_red)