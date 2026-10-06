

'''se decide usar una lista enalazada para la cache del proyecto ya que 
en el enunciado dice que se va a tener mas busquedas que inserciones por lo que priorizar
el tiempo de busqueda es sensato ya que es a lo que mas se va a llamar. Su costo 
seria de O(log n) y la insercion es de O(log n) que es el aspecto que se veria
sacrificado ya que no va a tener muchas llamadas. Ademas esta lista siempre debe estar
ordenada por id'''


class NodeQueue:
    def __init__(self, value):
        self.value = value
        self.next = None  # Pointer to next node


class Queue:
    def __init__(self):
        self.front = None
        self.rear = None

    def enqueue(self, value):
        new_node = NodeQueue(value)
        if self.rear is None:
            self.front = self.rear = new_node
            return
        self.rear.next = new_node
        self.rear = new_node

    def dequeue(self):
        if self.front is None:
            return None
        value = self.front.value
        self.front = self.front.next
        if self.front is None:
            self.rear = None
        return value

