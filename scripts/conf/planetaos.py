import os
import socket

import manager

from .npb import Npb


class PlanetaOS(manager.Machine):
    def __init__(self, args):
        base = "/home/desertfox/research/projects/ffmk/interference-bench/"

        common_params = {
            'nodes': (1,),
            'schedulers': ("cfs", "pinned"),
            'affinity': ("2-3", "1,3"),
        }
        self.group = \
            manager.BenchGroup(Npb, prog=("bt-mz", "sp-mz"),
                               size=("S",),
                               np=(2, 4),
                               **common_params,
                               wd=base + "NPB3.3.1-MZ/NPB3.3-MZ-MPI/") + \
            manager.BenchGroup(Npb, prog=("bt-mz", "sp-mz"),
                               size=("W",),
                               np=(2, 4, 8),
                               **common_params,
                               wd=base + "NPB3.3.1-MZ/NPB3.3-MZ-MPI/") + \
            manager.BenchGroup(Npb,
                               prog=("bt", "sp"),
                               size=("W", "S"),
                               np=(4, 9),
                               **common_params,
                               wd=base + "/NPB3.3.1/NPB3.3-MPI/") + \
            manager.BenchGroup(Npb,
                               prog=("cg", "ep", "ft",
                                     "is", "lu", "mg"),
                               size=("W", "S"),
                               np=(2, 4, 8),
                               **common_params,
                               wd=base + "/NPB3.3.1/NPB3.3-MPI/")

        self.mpiexec = 'mpirun'
        self.mpiexec_np = '-np'
        self.mpiexec_hostfile = '-hostfile {}'

        self.preload = '-x LD_PRELOAD={}'

        self.lib = manager.Lib('openmpi')

        self.env = os.environ.copy()
        self.env['INTERFERENCE_LOCALID'] = 'OMPI_COMM_WORLD_LOCAL_RANK'

        self.prefix = 'INTERFERENCE'


        self.runs = (i for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = self.env['HOME'] + '/hostfiles'

        super(PlanetaOS, self).__init__(args)

    def get_nodelist(self):
        return [socket.gethostname()]

    def format_command(self, context):
        parameters = " ".join([self.mpiexec_hostfile.format(self.hostfile.path),
                               self.mpiexec_np, str(context.bench.np),
                               self.preload.format(self.get_lib()),
                               '-oversubscribe',
                               '--bind-to none'])
        return "{} {} ./bin/{}".format(self.mpiexec, parameters, context.bench.name)

    def correct_guess():
        if socket.gethostname() == 'planeta-os':
            return True
        return False
