import os
import itertools
import subprocess as sp

from .cache import Cache
from .context import Context


class Machine:
    class Hostfile(Context):
        def __enter__(self):
            self.hostfile = self.create_file(
                self.machine.hostfile_dir, 'hostfile')
            self.hostfile.f.write(
                "\n".join(self.machine.nodelist[:self.bench.nodes]) + '\n')

            return super().__enter__()

    def create_context(self, machine, cfg):
        return self.Hostfile(machine, cfg)

    def __init__(self, args):
        self.args = args

        self.env['INTERFERENCE_PREFIX'] = self.prefix

        self.suffix = "{}-{}".format(type(self).__name__, self.lib.name)

    def get_script_path(self):
        return os.path.dirname(os.path.realpath(__file__))

    def get_lib(self):
        return self.get_lib_path() + 'libinterference.so'

    def get_lib_path(self):
        lib = "/../../install-{}/usr/local/lib/"
        return self.get_script_path() + lib.format(self.suffix)

    def configurations(self):
        confs = tuple(
            itertools.product(self.runs, self.benchmarks, self.affinities))
        res = list()
        for (run, bench, affinity) in confs:
            print(run, bench, affinity)
            env = self.env.copy()
            env['INTERFERENCE_AFFINITY'] = affinity
            env['INTERFERENCE_SCHED'] = bench.schedulers
            res.append((run, bench, env, affinity))
        return res

    def compile_benchmarks(self):

        with Cache(self) as cache:
            env = self.env.copy()

            # execute compilation command
            for b in self.benchmarks:
                print(b)
                if b in cache:
                    b.fail = cache.compiled[b]
                    print("Skipping: {}".format(b))
                    continue
                print("Compiling: {}".format(b))
                b.compile(env)

                cache.add(b)

    def run_benchmarks(self, runtimes_log, runtimes_file):
        print('-' * 62)
        for cfg in self.configurations():
            (run, bench, env, affinity) = cfg

            if bench.fail:
                continue

            with self.create_context(self, cfg) as context:
                command = self.format_command(context)
                print("Run ", bench.name, bench.nodes, {
                      i: env[i] for i in filter(lambda k: 'INTERFERENCE' in k, env.keys())})
                print(command)
                p = sp.Popen(command, stdout=sp.PIPE, stderr=sp.STDOUT,
                             cwd=bench.wd, env=env, shell=True)
                out = p.stdout.read().decode('UTF-8')
                err = p.stdout.read().decode('UTF-8')
                p.communicate()

                if (p.returncode):
                    print("Error")
                    print("".join(out))
                    print("".join(err))
                    print(p.returncode)
                    continue

                results = list(
                    filter(lambda x: self.prefix in x, out.splitlines()))
                if len(results) == 0:
                    print("Failed to get profiling data")
                    print("".join(out))
                    print("".join(err))
                    continue
                for l in results:
                    row = {k.strip(): v.strip()
                           for (k, v) in
                           map(lambda x: x.split(':'),
                               filter(lambda x: ':' in x,
                                      l.split(',')))}
                    print(row)
                    runtimes_log.writerow([bench.prog,
                                           bench.nodes,
                                           bench.np,
                                           bench.size,
                                           bench.oversub,
                                           run,
                                           bench.schedulers,
                                           affinity,
                                           row['CPU'],
                                           row['RANK'],
                                           row['NODE'],
                                           row['ITER'],
                                           row['UTIME'],
                                           row['WTIME']])
                runtimes_file.flush()
                print('=' * 40)

    def compile_libs(self):
        path = self.get_script_path()
        build_path = path + '/../../build-' + self.suffix + '/'
        install_path = path + '/../../install-' + self.suffix + '/'
        if not os.path.exists(build_path):
            os.makedirs(build_path)
        self.lib.compile_pre = 'pwd'
        sequence = [
            self.lib.compile_pre,
            'cd {}'.format(build_path),
            'cmake .. {}'.format(self.lib.compile_flags),
            'make clean',
            'make',
            'make install DESTDIR=' + install_path]
        command = ' && '.join(filter(lambda x: len(x) > 0, sequence))
        print(command)
        p = sp.Popen('/bin/bash',
                     cwd=build_path,
                     env=self.env,
                     stdin=sp.PIPE,
                     stdout=sp.PIPE,
                     stderr=sp.PIPE)
        (out, err) = p.communicate(input=command.encode())
        if p.returncode:
            print(out.decode('UTF-8'))
            print(err.decode('UTF-8'))
            raise Exception("Failed to prepare library.")
        print(out.decode('UTF-8'))
        print(err.decode('UTF-8'))
