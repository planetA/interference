import itertools
import subprocess as sp

from . import m

class Benchmark:
    class SafeDict(dict):
        def __missing__(self, key):
            return '{' + key + '}'

    def __init__(self, **kwargs):
        self.fail = False

        for k, v in kwargs.items():
            if callable(v):
                v_arguments = v.__code__.co_varnames[:v.__code__.co_argcount]
                args = {arg: kwargs[arg] for arg in v_arguments}
                if len([a for a in args.values() if callable(a)]):
                    raise Exception("Parameter resolution depends " +
                                    "on potenitally unresolved parameters")
                setattr(self, k, v(**args))
            else:
                setattr(self, k, v)

    def compile(self, env):
        print(self.compile_command)
        p = sp.Popen(self.compile_command,
                     cwd=self.wd,
                     env=env,
                     stderr=sp.PIPE,
                     stdout=sp.PIPE,
                     shell=True)
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
        if 'tmpl' not in kwargs:
            kwargs['tmpl'] = ''

        def is_container(x):
            return isinstance(kwargs[x], list) or isinstance(kwargs[x], tuple)

        def is_not_container(x):
            return not is_container(x)
        rest = {k: kwargs[k] for k in filter(is_not_container, kwargs)}
        lists = {k: kwargs[k] for k in filter(is_container, kwargs)}
        params = [dict(zip(lists, p))
                  for p in itertools.product(*lists.values())]
        params = [m(rest, i) for i in params]
        self.benchmarks = tuple(BenchmarkClass(**i) for i in params)

    def __add__(self, other):
        self.benchmarks = self.benchmarks + other.benchmarks
        return self
