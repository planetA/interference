import os
import socket

import manager

from .npb import Npb

import math

class PlanetaOS(manager.Machine):
    def __init__(self, args):
        self.env = os.environ.copy()
        base = self.env['HOME'] + "/research/projects/ffmk/measurements/interference-bench/"

        cpu_per_node = 4

        def np_square(nodes, oversub):
            np = nodes * oversub * cpu_per_node
            return math.floor(math.sqrt(np))**2

        def np_power2(nodes, oversub):
            return nodes * oversub * cpu_per_node

        def np_func(nodes, oversub):
            return nodes * oversub * cpu_per_node

        def compile_command(wd, prog, nodes, oversub, size):
            # A HACK
            if prog in ("bt", "sp"):
                np = np_square(nodes, oversub)
            elif prog in ("is", "cg",):
                np = np_power2(nodes, oversub)
            else:
                np = np_func(nodes, oversub)
            # HACK END

            return 'cd {} ;' \
                ' make {} NPROCS={} CLASS={}'.format(wd, prog, np, size)

        common_params = {
            'nodes': (1,),
            'schedulers': ("cfs", "pinned_cyclic"),
            'affinity': ("2-3", "1,3"),
            'oversub': (1, 2, 4),
            'compile_command': compile_command,
            'size': ('W', 'S',),
            'distribution' : 'blocked',
        }

        mz_params = {
            'wd': base + "/NPB3.3.1-MZ/NPB3.3-MZ-MPI/"
        }

        npb_params = {
            'wd': base + "/NPB3.3.1/NPB3.3-MPI/"
        }

        self.group = \
            manager.BenchGroup(Npb, **common_params, **mz_params,
                               np=np_func,
                               prog=("bt-mz", "sp-mz"))


        self.group += \
            manager.BenchGroup(Npb, **common_params, **npb_params,
                               np=np_func,
                               prog=("ep", "lu", "mg"))

        self.group += \
            manager.BenchGroup(Npb, **common_params, **npb_params,
                               np=np_power2,
                               prog=("is", "cg",))

        self.group += \
            manager.BenchGroup(Npb, **common_params, **npb_params,
                               np=np_power2,
                               prog=("ft",))

        self.group += \
            manager.BenchGroup(Npb, **common_params, **npb_params,
                               np=np_square,
                               prog=("bt", "sp"))

        self.mpiexec = 'mpirun'
        self.mpiexec_np = '-np'
        self.mpiexec_hostfile = '-hostfile {}'

        self.preload = '-x LD_PRELOAD={}'

        self.lib = manager.Lib('openmpi')

        self.env['INTERFERENCE_LOCALID'] = 'OMPI_COMM_WORLD_LOCAL_RANK'
        self.env['INTERFERENCE_LOCAL_SIZE'] = 'OMPI_COMM_WORLD_LOCAL_SIZE'

        self.prefix = 'INTERFERENCE'


        self.runs = (i for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = self.env['HOME'] + '/hostfiles'

        super().__init__(args)

    def get_nodelist(self):
        return [socket.gethostname()]

    def format_command(self, context):
        parameters = " ".join([self.mpiexec_hostfile.format(context.hostfile.path),
                               self.mpiexec_np, str(context.bench.np),
                               self.preload.format(self.get_lib()),
                               '-oversubscribe',
                               '--bind-to none'])
        return "{} {} ./bin/{}".format(self.mpiexec, parameters, context.bench.name)

    def correct_guess():
        if socket.gethostname() == 'planeta-os':
            return True
        return False
