import itertools
import subprocess as sp

class Benchmark:
    def __init__(self):
        self.fail = False

    def compile(self, env):
        p = sp.Popen(self.compile_command,
                     cwd = self.wd,
                     env = env,
                     stderr = sp.PIPE,
                     stdout = sp.PIPE,
                     shell = True)
        err = p.stderr.read().decode('UTF-8')
        out = p.stdout.read().decode('UTF-8')
        p.communicate()
        if (p.returncode):
            self.fail = True
            print("Failed to complie benchmark")
            print(out)
            print(err)


class BenchGroup:
    """ Class representing a group of NPB benchmarks """
    def __init__(self, BenchmarkClass, progs, sizes, np, wd):
        self.benchmarks = tuple((BenchmarkClass(prog, np, size, wd),)
                            for (prog, np, size)
                            in itertools.product(progs, np, sizes))

    def __add__(self, other):
        self.benchmarks = self.benchmarks + other.benchmarks
        return self
