
class Expr(object):
    def children(self):
        return None

    def depth(self):
        if (self.children() == None):
            return 1
        else:
            return 1 + max(c.depth() for c in self.children())

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
    def __rshift__(self, other):
        return ~self + other
    def __eq__(self, other):
        return type(self) == type(other) and str(self) == str(other)
    def positive_var(self):
        return isinstance(self, Var) and self.first_order and not self.dual
    def negative_var(self):
        return isinstance(self, Var) and self.first_order and self.dual
    def positive(self):
        if isinstance(self, Unit):
            return True
        elif isinstance(self, Var):
            return self.first_order and not self.dual
        elif isinstance(self, Tensor) or isinstance(self, Par):
            return all(e.positive() for e in self.children())
        else:
            return False
    def negative(self):
        return (~self).positive()


class Var(Expr):
    def __init__(self, name, dual=False, first_order=True):
        self.name = name
        self.dual = dual
        self.first_order = first_order
    def __str__(self):
        return ('~' if self.dual else '') + self.name
    def __invert__(self):
        return Var(self.name, not self.dual, self.first_order)

class Unit(Expr):
    def __str__(self):
        return 'I'
    def __invert__(self):
        return self

I = Unit()

class Par(Expr):
    def __init__(self, ch):
        self.ch = list(ch)
    def __invert__(self):
        return Tensor([~c for c in self.ch])
    def __str__(self):
        return ' + '.join([str(c) if isinstance(c, Var) else '(' + str(c) + ')' for c in self.ch])
    def children(self):
        return self.ch

class Tensor(Expr):
    def __init__(self, ch):
        self.ch = list(ch)
    def __invert__(self):
        return Par([~c for c in self.ch])
    def __str__(self):
        return ' * '.join([str(c) if isinstance(c, Var) else '(' + str(c) + ')' for c in self.ch])
    def children(self):
        return self.ch

