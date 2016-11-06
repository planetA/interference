import manager


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
