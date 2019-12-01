
class Expr(object):
    def __init__(self):
        self.prec = -1

    def children(self):
        return None

    def __add__(self, other):
        if isinstance(self, Par) and isinstance(other, Par):
            return Par(self.ch + other.ch)
        elif isinstance(self, Par):
            return Par(self.ch + [other])
        elif isinstance(other, Par):
            return Par([self] + other.ch)
        else:
            return Par([self, other])
    def __mul__(self, other):
        if isinstance(self, Tensor) and isinstance(other, Tensor):
            return Tensor(self.ch + other.ch)
        elif isinstance(self, Tensor):
            return Tensor(self.ch + [other])
        elif isinstance(other, Tensor):
            return Tensor([self] + other.ch)
        else:
            return Tensor([self, other])
    def __repr__(self):
        return "Expr(" + str(self) + ")"
    def __str__(self):
        return ""
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
        return ' + '.join([str(c) if isinstance(c, Var) else '(' + str(c) + ')' for c in self.ch])
    def children(self):
        return self.ch

class Tensor(Expr):
    def __init__(self, ch):
        self.ch = list(ch)
        self.prec = 2
    def __invert__(self):
        return Par([~c for c in self.ch])
    def __str__(self):
        return ' * '.join([str(c) if isinstance(c, Var) else '(' + str(c) + ')' for c in self.ch])
    def children(self):
        return self.ch

