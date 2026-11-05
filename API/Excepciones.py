
class ErrorCliente(RuntimeError):

    reintentable = False


class PresupuestoAgotadoError(ErrorCliente):

    def __init__(self, presupuesto, url):
        self.presupuesto = presupuesto
        self.url = url
        super().__init__(
            f"Se agotó el presupuesto de solicitudes ({presupuesto}) "
            f"al consultar {url}"
        )


class SinConexionError(ErrorCliente):

    reintentable = True

    def __init__(self, url):
        self.url = url
        super().__init__(f"No hay conexión al consultar {url}")


class TiempoAgotadoError(ErrorCliente):

    reintentable = True

    def __init__(self, url, segundos):
        self.url = url
        self.segundos = segundos
        super().__init__(
            f"El servidor no respondió en {segundos} s al consultar {url}"
        )


class RespuestaInvalidaError(ErrorCliente):

    def __init__(self, url, detalle):
        self.url = url
        self.detalle = detalle
        super().__init__(f"Respuesta inválida de {url}: {detalle}")


class ErrorServicio(ErrorCliente):

    def __init__(self, url, codigo, mensaje=None):
        self.url = url
        self.codigo = codigo
        self.mensaje = mensaje
        self.reintentable = codigo >= 500

        texto = f"El servicio respondió {codigo} al consultar {url}"
        if mensaje:
            texto += f": {mensaje}"
        super().__init__(texto)