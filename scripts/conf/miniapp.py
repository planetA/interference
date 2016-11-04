import manager

class Miniapp(manager.Benchmark):
    """ Class representing an npb benchmark """
    def __init__(self, **kwargs):
        super().__init__()

        self.prog = kwargs['prog']
        self.np = kwargs['np']
        self.size = kwargs['size']
        self.wd = kwargs['wd']

        if 'compile_command' in kwargs:
            self.compile_command = kwargs['compile_command']
        else:
            self.compile_command = "make"

        self.name = kwargs['tmpl'].format_map(self.SafeDict(**kwargs))

    def __eq__(self, other):
        return ((self.prog == other.prog) and (self.np == self.np) and
                (self.size == other.size) and (self.wd == other.wd))

    def __hash__(self):
        return hash((self.prog, self.np, self.size, self.wd))

    def __str__(self):
        return "{} {} -np {} {}".format(self.prog, self.size, self.np, self.fail)
