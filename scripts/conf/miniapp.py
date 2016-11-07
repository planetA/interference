import manager
from numpy import prod


class Miniapp(manager.Benchmark):
    """ Class representing an npb benchmark """

    def __init__(self, **kwargs):
        super().__init__()

        for k, v in kwargs.items():
            if callable(v):
                print(k, v)
                v_arguments = v.__code__.co_varnames[:v.__code__.co_argcount]
                args = {arg: kwargs[arg] for arg in v_arguments}
                if len([a for a in args.values() if callable(a)]):
                    raise Exception("Parameter resolution depends " +
                                    "on potenitally unresolved parameters")
                setattr(self, k, v(**args))
                print(getattr(self, k))
            else:
                setattr(self, k, v)

        if 'compile_command' not in kwargs:
            self.compile_command = "make"

        self.name = self.tmpl.format_map(self.SafeDict(**self.__dict__))

    def __eq__(self, other):
        return ((self.prog == other.prog) and (self.np == self.np) and
                (self.size == other.size) and (self.wd == other.wd))

    def __hash__(self):
        return hash((self.prog, self.np, self.size, self.wd))

    def __str__(self):
        return "{} {} -np {} {}".format(self.prog, self.size, self.np,
                                        self.fail)

    def factors(n):
        for i in range(2, n):
            if n % i == 0:
                return [i] + Miniapp.factors(n // i)
        return [n]

    def partition(l, n):
        """ Partition list @l into @n groups. First group contains
         elements 0, n, 2*n, ... Second group contains elements
         1, n, 2*n ...
         """
        f = [1] * 3 + Miniapp.factors(n)
        p = [[f[j] for j in range(i, len(f), n)] for i in range(n)]
        return list(map(prod, p))
