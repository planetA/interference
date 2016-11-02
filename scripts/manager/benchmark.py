import itertools
import subprocess as sp

class Benchmark:
    class SafeDict(dict):
        def __missing__(self, key):
            return '{' + key + '}'

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
    def __init__(self, BenchmarkClass, **kwargs):
        wd = kwargs['wd']
        if 'tmpl' not in kwargs:
            tmpl = ''
        else:
            tmpl = kwargs['tmpl']
        rest = {i : kwargs[i] for i in kwargs if i not in ('wd', 'tmpl')}
        params = list(dict(zip(rest, p)) for p in itertools.product(*rest.values()))
        params = [{**{'wd' : wd, 'tmpl' : tmpl}, **i} for i in params]
        self.benchmarks = tuple(BenchmarkClass(**i) for i in params)
        print([str(i) for i in self.benchmarks])

    def __add__(self, other):
        self.benchmarks = self.benchmarks + other.benchmarks
        return self
