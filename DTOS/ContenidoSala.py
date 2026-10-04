from DTOS.EnemigoInstancia import EnemigoInstancia
from DTOS.TrampaInstancia import TrampaInstancia


class ContenidoSala:
    def __init__(self, id_sala,enemigos, trampas, objetos):
        self.id_sala= id_sala
        self.enemigos= enemigos
        self.trampas= trampas
        self.objetos= objetos





    @classmethod
    def desde_json(cls, datos):
        '''estos dos ciclos basicamente lo que hacen es convertir uno por uno los enemigos
        y las trampas que hay y guardarlas en una lista. EnemigoInstancia.desde_json(enemigo)
        llaman a su propio metodo creador que llama al init de una'''
        enemigos_convertidos = []
        trampas_convertidos = []
        objetos_convertidos = []

        for enemigo in datos["enemigos"]:
            enemigos_convertidos.append(EnemigoInstancia.desde_json(enemigo))
        for trampa in datos["trampas"]:
            trampas_convertidos.append(TrampaInstancia.desde_json(trampa))
        for objeto in datos["objetos"]:
            objetos_convertidos.append(TrampaInstancia.desde_json(objeto))

        return cls(
            id_sala=datos["sala"],
            enemigos=enemigos_convertidos,
            trampas=trampas_convertidos,
            objetos=objetos_convertidos

        )


