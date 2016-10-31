import os
import subprocess
import itertools
import tempfile
import subprocess as sp

from .cache import Cache

class Machine:
    class Hostfile:
        def __init__(self, machine, nodes):
            if not os.path.exists(machine.hostfile_dir):
                os.makedirs(machine.hostfile_dir)

            (fd,
             self.path) = tempfile.mkstemp(prefix='hostfile.',
                                           dir = machine.hostfile_dir, text=True)
            self.hostfile = open(self.path, "w")
            self.hostfile.write("\n".join(machine.nodelist[:nodes])+'\n')
            self.hostfile.flush()

        def __enter__(self):
            return self.hostfile

        def __exit__(self, exc_type, exc_value, traceback):
            self.hostfile.close()
            if os.path.exists(self.path):
                os.remove(self.path)

    def __init__(self, args):
        self.args = args

        self.env['INTERFERENCE_PREFIX'] = self.prefix
        self.env['INTERFERENCE_LOCALID'] = self.localid_var

        if args.comm == 'prepare':
            for l in args.targets:
                if l not in self.known_libs:
                    raise Exception("Unknown MPI library requested")
            self.libs = [self.known_libs[l] for l in args.targets]
        elif args.comm == 'run':
            self.libs = [self.known_libs['default'],]
        else:
            raise Exception('Unknown command')
        self.suffix = "{}-{}".format(type(self).__name__,self.libs[0].name)

    def get_script_path(self):
        return os.path.dirname(os.path.realpath(__file__))

    def get_lib(self):
        lib = "/../../install-{}/usr/local/lib/libinterference.so"
        return self.get_script_path() + lib.format(self.suffix)


    def configurations(self):
        confs = tuple(sum(x, ()) for x in
                      itertools.product(self.benchmarks,
                                        self.schedulers,
                                        self.nodes,
                                        self.affinities,
                                        self.runs))
        res = list()
        for (bench, sched, nodes, affinity, run) in confs:
            env = self.env.copy()
            env['INTERFERENCE_AFFINITY'] = affinity
            env['INTERFERENCE_SCHED'] = sched
            res.append((bench, nodes, env, sched, affinity, run))
        return res

    def compile_benchmarks(self):

        with Cache(self) as cache:
            env = self.env.copy()

            # execute compilation command
            for b_l in self.benchmarks:
                b = b_l[0]
                if b in cache:
                    b_l[0].fail = cache.compiled[b]
                    print("Skipping: {}".format(b))
                    continue
                print("Compiling: {}".format(b))
                b.compile(env)

                cache.add(b)

    def create_hostfile(self, nodes):
        self.hostfile = self.Hostfile(self, nodes)
        return self.hostfile

    def run_benchmarks(self, runtimes_log):
        print('-'*62)
        for cfg in self.configurations():
            (bench, nodes, env, sched, affinity, run) = cfg

            if bench.fail:
                continue

            with self.create_hostfile(nodes) as hostfile:
                command = self.format_command(bench, nodes)
                print("Run ", bench.name, nodes, {i : env[i] for i in filter(lambda k : 'INTERFERENCE' in k, env.keys())})
                print(command)
                p = sp.Popen(command, stdout = sp.PIPE, stderr = sp.STDOUT,
                             cwd = bench.wd, env = env, shell = True)
                out = p.stdout.read().decode('UTF-8')
                err = p.stdout.read().decode('UTF-8')
                p.communicate()

                if (p.returncode):
                    print("Error")
                    print("".join(out))
                    print("".join(err))
                    print(p.returncode)
                    continue

                results = list(filter(lambda x : self.prefix in x, out.splitlines()))
                if len(results) == 0:
                    print("Failed to get profiling data")
                    print("".join(out))
                    print("".join(err))
                    continue
                for l in results:
                    row = {k.strip() : v.strip()
                           for (k,v) in
                            map(lambda x : x.split(':'),
                                filter(lambda x : ':' in x,
                                       l.split(',')))}
                    print(row)
                    runtimes_log.writerow([bench.name,
                                           nodes,
                                           bench.np,
                                           bench.size,
                                           run,
                                           sched,
                                           affinity,
                                           row['CPU'],
                                           row['RANK'],
                                           row['NODE'],
                                           row['ITER'],
                                           row['UTIME'],
                                           row['WTIME']])

                print('='*40)
                continue

    def compile_libs(self):
        for lib in self.libs:
            path = self.get_script_path()
            build_path = path + '/../../build-' + self.suffix +'/'
            install_path = path + '/../../install-' + self.suffix +'/'
            if not os.path.exists(build_path):
                os.makedirs(build_path)
            lib.compile_pre='pwd'
            sequence =  [
                lib.compile_pre,
                'cd {}'.format(build_path),
                'cmake .. {}'.format(lib.compile_flags),
                'make',
                'make install DESTDIR='+install_path]
            command = ' && '.join(filter(lambda x : len(x) > 0, sequence))
            print(command)
            p = sp.Popen('/bin/bash',
                         cwd = build_path,
                         stdin = sp.PIPE,
                         stdout = sp.PIPE,
                         stderr = sp.PIPE)
            (out, err) = p.communicate(input=command.encode())
            if p.returncode:
                print(out.decode('UTF-8'))
                print(err.decode('UTF-8'))
                raise Exception("Failed to prepare library.")
            print(out.decode('UTF-8'))
            print(err.decode('UTF-8'))
