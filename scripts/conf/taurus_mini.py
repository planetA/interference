import os
import socket
import subprocess as sp
from numpy import prod

import manager

from .miniapp import Miniapp


class Taurus_Mini(manager.Machine):
    """Module for running miniapps with mvapich"""

    def __init__(self, args):
        self.env = os.environ.copy()

        base = self.env['HOME'] + "/interference-bench/miniapps/"

        nodes = (1, 2, 4, 8)
        cpu_per_node = 24
        schedulers = ("cfs", "pinned")
        schedulers = ("pinned",)

        def factors(n):
            for i in range(2, n):
                if n % i == 0:
                    return [i] + factors(n // i)
            return [n]

        def partition(l, n):
            """ Partition list @l into @n groups. First group contains
             elements 0, n, 2*n, ... Second group contains elements
             1, n, 2*n ...
             """
            return [[l[j] for j in range(i, len(l), n)] for i in range(n)]

        def np_func(nodes):
            return nodes * cpu_per_node

        def comd_size_param(size, nodes):
            np = np_func(nodes)
            f = [1] * 3 + factors(np)
            # Ensure that f has at least 3 groups
            p = partition(f, 3)
            problem_size = '-x 200 -y 200 -z 200'
            decomposition = '-i {} -j {} -k {} '.format(*map(prod, p))
            return decomposition + problem_size

        self.modules_load = 'source {}/mini.env'.format(base)
        compile_command = self.modules_load + '; cd ../src-mpi ; make'
        tmpl = './{prog} {size_param}'
        self.group = \
            manager.BenchGroup(Miniapp, prog=("CoMD-mpi",),
                               size=(1,),
                               np=np_func,
                               schedulers=schedulers,
                               nodes=nodes,
                               size_param=comd_size_param,
                               wd=base + "CoMD/bin",
                               compile_command=compile_command,
                               tmpl=tmpl)  # + \

        compile_command = self.modules_load + '; make lassen_mpi'

        def lassen_size_param(size, nodes, max_nodes):
            np = np_func(nodes)
            f = [1] * 3 + factors(np)
            # Ensure that f has at least 3 groups
            p = partition(f, 3)
            domains = list(map(prod, p))
            decomposition = '{} {} {}'.format(*domains)
            global_zones = ' {}'.format(cpu_per_node * max_nodes * size) * 3
            return "default {} {}".format(decomposition, global_zones)

        self.group = \
            manager.BenchGroup(Miniapp, prog=("lassen_mpi",),
                               size_param=lassen_size_param,
                               size=(2,),
                               nodes=nodes,
                               np=np_func,
                               schedulers=schedulers,
                               max_nodes=max(nodes),
                               compile_command=compile_command,
                               wd=base + "lassen/",
                               tmpl=tmpl)

        def lulesh_np_func(nodes):
            return {1: 8, 2: 27, 4: 64, 8: 125, 16: 343}[nodes]

        compile_command = self.modules_load + '; make'
        self.group += \
            manager.BenchGroup(Miniapp, prog=("lulesh2.0",),
                               size_param=("-i 300 -c 10 -b 3",),
                               size=(1,),
                               nodes=nodes,
                               schedulers=schedulers,
                               np=lulesh_np_func,
                               wd=base + "lulesh2.0.3/",
                               compile_command=compile_command,
                               tmpl=tmpl)

        self.mpiexec = 'mpirun_rsh'
        self.mpiexec_np = '-np'
        self.mpiexec_hostfile = '-hostfile {}'

        self.preload = 'LD_PRELOAD={}'

        self.lib = manager.Lib('mvapich',
                               compile_pre=self.modules_load,
                               compile_flags='')

        self.env['OMP_NUM_THREADS'] = '1'
        self.env['INTERFERENCE_LOCALID'] = 'MV2_COMM_WORLD_LOCAL_RANK'
        self.env['INTERFERENCE_HACK'] = 'true'

        self.prefix = 'INTERFERENCE'

        self.affinities = ("0-23",)

        self.runs = (i for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = self.env['HOME'] + '/hostfiles'

        super().__init__(args)

    def get_nodelist(self):
        p = sp.run('scontrol show hostnames'.split(),
                   stdout=sp.PIPE)
        if p.returncode:
            raise Exception("Failed to get hosts")

        return list(p.stdout.decode('UTF-8').splitlines())

    def format_command(self, context):
        mpiline = self.mpiexec_hostfile.format(context.hostfile.path)
        parameters = " ".join([mpiline,
                               self.mpiexec_np, str(context.bench.np),
                               '-ssh',
                               '-export-all'])
        command = "{} ; taskset 0xFFFFFFFF {} {} {} ./{}"
        lib = self.preload.format(self.get_lib())
        return command.format(self.modules_load, self.mpiexec, parameters,
                              lib, context.bench.name)

    def correct_guess():
        if 'taurusi' in socket.gethostname():
            return True
        return False
