from models.usuario import Usuario


class Operador(Usuario):
    def etiqueta(self):
        return f"Operador {self.nombre}"
