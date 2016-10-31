import manager

class Npb(manager.Benchmark):
    """ Class representing an npb benchmark """
    def __init__(self, prog, np, size, wd):
        super(Npb, self).__init__()

        self.prog = prog
        self.np = np
        self.size = size
        self.wd = wd

        self.compile_command = "make {} NPROCS={} CLASS={}".format(prog, np, size)

        self.name = "{}.{}.{}".format(self.prog, self.size, self.np)

    def __eq__(self, other):
        return ((self.prog == other.prog) and (self.np == self.np) and
                (self.size == other.size) and (self.wd == other.wd))

    def __hash__(self):
        return hash((self.prog, self.np, self.size, self.wd))

    def __str__(self):
        return "{}.{}.{} {}".format(self.prog, self.size, self.np, self.fail)
