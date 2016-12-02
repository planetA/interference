import os
import socket
import math
import subprocess as sp

import manager

from .npb import Npb
from .mvapich import Mvapich


class Taurus(manager.Machine):
    def __init__(self, args):
        self.env = os.environ.copy()
        base = self.env['HOME'] + '/interference-bench/'

        cpu_per_node = 16
        nodes = (2, 4, 8, 16)
        schedulers = ("cfs", "pinned_cyclic", "fifo_cyclic")
        affinity = ("4-11,16-23",)

        self.modules_load = 'source {}/miniapps/mini.env'.format(base)

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
            'size': ('C', 'D',),
        }

        mz_params = {
            'wd': base + "/NPB3.3.1-MZ/NPB3.3-MZ-MPI/"
        }

        self.group = \
            manager.BenchGroup(Npb, **common_params, **mz_params,
                               np=np_func,
                               prog=("bt-mz", "sp-mz"))

        npb_params = {
            'wd': base + "/NPB3.3.1/NPB3.3-MPI/"
        }

        self.group += \
            manager.BenchGroup(Npb, **common_params, **npb_params,
                               np=np_func,
                               prog=("ep", "lu", "mg"))

        def np_power2(nodes, oversub):
            return nodes * oversub * cpu_per_node

        self.group += \
            manager.BenchGroup(Npb, **common_params, **npb_params,
                               np=np_power2,
                               prog=("is", "cg",))

        self.group += \
            manager.BenchGroup(Npb, **common_params, **npb_params,
                               np=np_power2,
                               prog=("ft",))

        def np_square(nodes, oversub):
            np = nodes * oversub * cpu_per_node
            return math.floor(math.sqrt(np))**2

        self.group += \
            manager.BenchGroup(Npb, **common_params, **npb_params,
                               np=np_square,
                               prog=("bt", "sp"))

        self.mpilib = Mvapich(mpiexec='srun',
                              compile_pre=self.modules_load)

        self.env['INTERFERENCE_PERF'] = 'instructions,cache_references,cache_misses,migrations,page_faults,context_switches'

        self.runs = (i for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = os.environ['HOME'] + '/hostfiles'

        super().__init__(args)

    def create_context(self, machine, cfg):
        class Context(manager.Context):
            def __enter__(self):
                self.hostfile = self.create_file(
                    self.machine.hostfile_dir, 'hostfile')
                self.hostfile.f.write(
                    "\n".join(self.machine.nodelist[:self.bench.nodes]) + '\n')

                self.nodestr = self.hostfile.path

                preload = 'echo export LD_PRELOAD={}'.format(machine.get_lib())
                self.prologue = self.create_script(
                    self.machine.hostfile_dir, 'prologue')
                self.prologue.f.write(
                    "\n".join(['#!/bin/bash',
                               preload]) + '\n')
                return super().__enter__()

        return Context(machine, cfg)

    def get_nodelist(self):
        p = sp.run('scontrol show hostnames'.split(),
                   stdout=sp.PIPE)
        if p.returncode:
            raise Exception("Failed to get hosts")

        return p.stdout.decode('UTF-8').splitlines()


    def correct_guess():
        if 'taurusi' in socket.gethostname():
            return True
        return False
