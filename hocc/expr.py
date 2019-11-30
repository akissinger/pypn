
class Expr(object):
    def __init__(self):
        self.ch = []
        self.prec = -1
    def __add__(self, other):
        if type(self) == Par and type(other) == Par:
            return Par(self.ch + other.ch)
        elif type(self) == Par:
            return Par(self.ch + [other])
        elif type(other) == Par:
            return Par([self] + other.ch)
        else:
            return Par([self, other])
    def __mul__(self, other):
        if type(self) == Tensor and type(other) == Tensor:
            return Tensor(self.ch + other.ch)
        elif type(self) == Tensor:
            return Tensor(self.ch + [other])
        elif type(other) == Tensor:
            return Tensor([self] + other.ch)
        else:
            return Tensor([self, other])
    def __repr__(self):
        return "Expr(" + str(self) + ")"
    def __gt__(self, other):
        return ~self + other


class Var(Expr):
    def __init__(self, name, dual=False):
        self.name = name
        self.dual = dual
        self.prec = 100
    def __str__(self):
        return ('~' if self.dual else '') + self.name
    def __invert__(self):
        return Var(self.name, not self.dual)

class Par(Expr):
    def __init__(self, ch):
        self.ch = list(ch)
        self.prec = 1
    def __invert__(self):
        return Tensor([~c for c in self.ch])
    def __str__(self):
        return ' + '.join([str(c) if type(c) == Var else '(' + str(c) + ')' for c in self.ch])

class Tensor(Expr):
    def __init__(self, ch):
        self.ch = list(ch)
        self.prec = 2
    def __invert__(self):
        return Par([~c for c in self.ch])
    def __str__(self):
        return ' * '.join([str(c) if type(c) == Var else '(' + str(c) + ')' for c in self.ch])

