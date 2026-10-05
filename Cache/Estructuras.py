class NodeSinglyLinkedList:
    def __init__(self, value):
        self.obj = value
        self.next = None

class SinglyLinkedList:
    def __init__(self):
        self.head = None

    def insert(self, value):
        new_node = NodeSinglyLinkedList(value)
        if self.head is None:
            self.head = new_node
            return
        current = self.head
        while current.next:
            current = current.next
        current.next = new_node

'''se decide usar una lista enalazada para la cache del proyecto ya que 
en el enunciado dice que se va a tener mas busquedas que inserciones por lo que priorizar
el tiempo de busqueda es sensato ya que es a lo que mas se va a llamar. Su costo 
seria de O(log n) y la insercion es de O(log n) que es el aspecto que se veria
sacrificado ya que no va a tener muchas llamadas. Ademas esta lista siempre debe estar
ordenada por id'''
