#!/usr/bin/env python3

import socket
import manager
import subprocess as sp
import itertools
import os
import tempfile
import csv

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

class Npb(Benchmark):
    """ Class representing an npb benchmark """
    def __init__(self, prog, np, size, wd):
        super(Npb, self).__init__()

        self.prog = prog
        self.np = np
        self.size = size
        self.wd = wd

        self.compile_command = "make {} NPROCS={} CLASS={}".format(prog, np, size)

        self.name = "{}.{}.{}".format(self.prog, self.size, self.np)

class NpbGroup:
    """ Class representing a group of NPB benchmarks """
    def __init__(self, progs, sizes, np, wd):
        self.benchmarks = tuple((Npb(prog, np, size, wd),)
                            for (prog, np, size)
                            in itertools.product(progs, np, sizes))
        pass

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

    def __init__(self):
        self.env = os.environ.copy()
        self.env['INTERFERENCE_PREFIX'] = self.prefix
        self.env['INTERFERENCE_LOCALID'] = self.localid_var

    def get_script_path(self):
        return os.path.dirname(os.path.realpath(__file__))

    def get_interference_path(self):
        return self.get_script_path() + "/../lib/libinterference.so"


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
            self.augment_env(env, bench, sched, affinity)
            res.append((bench, nodes, env, sched, affinity, run))
        return res

    def compile(self):
        """ Compile benchmarks """

        # cd to wd

        env = self.env.copy()

        # execute compilation command
        for b in self.benchmarks:
            b[0].compile(env)

    def create_hostfile(self, nodes):
        self.hostfile = self.Hostfile(self, nodes)
        return self.hostfile

class PlanetaOS(Machine):
    def __init__(self):
        self.wd = "/home/desertfox/research/projects/ffmk/interference-bench/NPB3.3.1-MZ/NPB3.3-MZ-MPI/"
        self.group = NpbGroup(progs = ("sp-mz", "bt-mz"),
                              sizes = ("W", "S"),
                              np = (2, 4, 8),
                              wd = self.wd)

        self.mpiexec = 'mpirun'
        self.mpiexec_np = '-np'
        self.mpiexec_hostfile = '-hostfile {}'

        self.preload = '-x LD_PRELOAD={}'.format(self.get_interference_path())

        self.prefix = 'INTERFERENCE'
        self.localid_var = 'OMPI_COMM_WORLD_LOCAL_RANK'

        self.schedulers = (("cfs",), ("pinned",))
        self.affinities = (("2-3",), ("1,3",))

        self.nodes = ((1,),)

        self.runs = ((i,) for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = os.environ['HOME'] + '/hostfiles'

        super(PlanetaOS, self).__init__()

    def get_nodelist(self):
        return [socket.gethostname()]

    def format_command(self, bench, nodes):
        parameters = " ".join([self.mpiexec_hostfile.format(self.hostfile.path),
                               self.mpiexec_np, str(bench.np),
                               self.preload,
                               '-oversubscribe',
                               '--bind-to none'])
        return "{} {} ./bin/{}".format(self.mpiexec, parameters, bench.name)

    def augment_env(self, env, bench, sched, affinity):
        pass

def main():
    bmEnv = dict()

    machine = PlanetaOS()

    machine.compile()

    with open('runtimes.log', 'w') as runtimes_log:
        runtimes = csv.writer(runtimes_log)
        runtimes.writerow(['prog', 'nodes', 'np',
                           'size', 'run',
                           'sched', 'affinity', 'cpu',
                           'rank', 'node', 'iter',
                           'utime', 'wtime'])
        print('-'*62)
        for cfg in machine.configurations():
            (bench, nodes, env, sched, affinity, run) = cfg

            if bench.fail:
                continue

            with machine.create_hostfile(nodes) as hostfile:
                command = machine.format_command(bench, nodes)
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
                    print(p.returncode)
                    continue

                result = list(filter(lambda x : machine.prefix in x, out.splitlines()))
                if len(result) == 0:
                    print("Failed to get profiling data")
                    continue
                results = list(filter(lambda x : machine.prefix in x, out.splitlines()))
                for l in results:
                    row = {k.strip() : v.strip()
                           for (k,v) in
                            map(lambda x : x.split(':'),
                                filter(lambda x : ':' in x,
                                       l.split(',')))}
                    print(row)
                    runtimes.writerow([bench.name,
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



if __name__ == '__main__':
    main()
