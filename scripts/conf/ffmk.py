import os
import socket
import math
import subprocess as sp

import manager

from .npb import Npb
from .mvapich import Mvapich

class Ffmk(manager.Machine):
    def __init__(self, args):
        self.env = os.environ.copy()
        base = self.env['HOME'] + '/interference-bench/'

        cpu_per_node = 8
        nodes = (1, 2, 4)
        schedulers = ("cfs", "pinned_cyclic", "pinned_blocked", 'fifo_cyclic')
        affinity = ("0-7","4-7")

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
            'oversub': (1, 2, 4),
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

        self.mpilib = Mvapich(mpiexec='mpirun',
                              compile_pre=self.modules_load)

        self.env['INTERFERENCE_PERF'] = ','.join(['instructions',
                                                  'cache_references',
                                                  'page_faults',
                                                  'migrations',
                                                  'context_switches',
                                                  'cache_misses',])

        self.runs = (i for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()

        super().__init__(args)

    def get_nodelist(self):
        return 'ffmk-n1 ffmk-n2 ffmk-n3 ffmk-n4'.split()

    def create_context(self, machine, cfg):
        class FfmkContext(manager.Context):
            def __enter__(self):
                nodes = self.machine.nodelist[:self.bench.nodes]
                self.nodestr = ",".join(nodes)
                return super().__enter__()

        return FfmkContext(machine, cfg)

    def correct_guess():
        if 'ffmk-n' in socket.gethostname():
            return True
        return False
