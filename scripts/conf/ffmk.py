import os
import socket
import math
import subprocess as sp

import manager

from .npb import Npb


class Ffmk(manager.Machine):
    def __init__(self, args):
        base = os.environ['HOME'] + '/interference-bench/'

        cpu_per_node = 8
        nodes = (1, 2, 4)
        schedulers = ("cfs", "pinned")
        affinity = ("4-11",)

        def m(x, y):
            z = x.copy()
            z.update(y)
            return z

        self.modules_load = '. {}/mini.env'.format(base)

        def compile_command(wd, prog, nodes, oversub, size):
            # A HACK
            if prog in ("bt", "sp"):
                np = np_square(nodes, oversub)
            elif prog in ("is", "cg",):
                np = np_power2(nodes, oversub)
            else:
                np = np_func(nodes, oversub)
            # HACK END

            return self.modules_load + '; cd {} ;' \
                ' make {} NPROCS={} CLASS={}'.format(wd, prog, np, size)

        def np_func(nodes, oversub):
            return nodes * oversub * cpu_per_node

        common_params = {
            'compile_command': compile_command,
            'schedulers': schedulers,
            'oversub': (2, 4),
            'nodes': nodes,
            'affinity' : affinity,
            'size': ('B', 'C',),
        }

        mz_params = {
            'wd': base + "/NPB3.3.1-MZ/NPB3.3-MZ-MPI/"
        }

        self.group = \
            manager.BenchGroup(Npb, **m(m(common_params, mz_params),
                                        {'np': np_func,
                                         'prog': ("bt-mz", "sp-mz")}))

        npb_params = {
            'wd': base + "/NPB3.3.1/NPB3.3-MPI/"
        }

        self.group += \
            manager.BenchGroup(Npb, **m(m(common_params, npb_params),
                                        {'np': np_func,
                                         'prog': ("ep", "lu", "mg")}))

        def np_power2(nodes, oversub):
            return nodes * oversub * cpu_per_node

        self.group += \
            manager.BenchGroup(Npb, **m(m(common_params, npb_params),
                                        {'np': np_power2,
                                         'prog': ("is", "cg",)}))

        self.group += \
            manager.BenchGroup(Npb, **m(m(common_params, npb_params),
                                          {'np': np_power2,
                                           'prog': ("ft",)}))

        def np_square(nodes, oversub):
            np = nodes * oversub * cpu_per_node
            return math.floor(math.sqrt(np))**2

        self.group += \
            manager.BenchGroup(Npb, **m(m(common_params, npb_params),
                                        {'np': np_square,
                                         'prog': ("bt", "sp")}))

        self.mpiexec = 'mpirun'
        self.mpiexec_np = '-np'
        self.mpiexec_hostfile = '-hosts {}'

        self.preload = '-env LD_PRELOAD {}'

        self.lib = manager.Lib('mvapich',
                               compile_pre=self.modules_load,
                               compile_flags='-Dfortran=OFF -Dtest=ON')

        self.env = os.environ.copy()
        self.env['OMP_NUM_THREADS'] = '1'
        self.env['INTERFERENCE_LOCALID'] = 'MV2_COMM_WORLD_LOCAL_RANK'
        self.env['INTERFERENCE_HACK'] = 'true'
        self.env['INTERFERENCE_PERF'] = 'instructions,cache_references,cache_misses,migrations,page_faults,context_switches'

        self.prefix = 'INTERFERENCE'

        self.runs = (i for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()

        super().__init__(args)

    def get_nodelist(self):
        return 'ffmk-n1 ffmk-n2 ffmk-n3 ffmk-n4'.split()

    def create_context(self, machine, cfg):
        return manager.Context(machine, cfg)

    def format_command(self, context):
        nodestr = ",".join(self.nodelist[:context.bench.nodes])
        parameters = " ".join([self.mpiexec_hostfile.format(nodestr),
                               self.mpiexec_np, str(context.bench.np)])
        command = "{} ; taskset 0xFFFFFFFF {} {} {} ./bin/{}"
        return command.format(self.modules_load, self.mpiexec, parameters,
                              self.preload.format(self.get_lib()),
                              context.bench.name)

    def correct_guess():
        if 'ffmk-n' in socket.gethostname():
            return True
        return False
