




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

    def is_empty(self):
        return self.front is None

    def size(self):
        contador = 0
        actual = self.front
        while actual is not None:
            contador += 1
            actual = actual.next
        return contador
