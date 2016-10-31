import os
import socket
import subprocess as sp

import manager

from .npb import Npb

class PlanetaOS(manager.Machine):
    def __init__(self, args):
        base =  "/home/desertfox/research/projects/ffmk/interference-bench/"

        self.group = \
            manager.BenchGroup(Npb, progs = ("bt-mz", "sp-mz"),
                               sizes = ("S",),
                               np = (2, 4),
                               wd = base + "NPB3.3.1-MZ/NPB3.3-MZ-MPI/") + \
            manager.BenchGroup(Npb, progs = ("bt-mz", "sp-mz"),
                               sizes = ("W",),
                               np = (2, 4, 8),
                               wd = base + "NPB3.3.1-MZ/NPB3.3-MZ-MPI/") + \
            manager.BenchGroup(Npb,
                               progs = ("bt", "sp"),
                               sizes = ("W", "S"),
                               np = (4, 9),
                               wd = base + "/NPB3.3.1/NPB3.3-MPI/") + \
            manager.BenchGroup(Npb,
                               progs = ("cg", "ep", "ft",
                                        "is", "lu", "mg"),
                               sizes = ("W", "S"),
                               np = (2, 4, 8),
                               wd = base + "/NPB3.3.1/NPB3.3-MPI/")

        self.mpiexec = 'mpirun'
        self.mpiexec_np = '-np'
        self.mpiexec_hostfile = '-hostfile {}'

        self.preload = '-x LD_PRELOAD={}'

        self.known_libs = {
            'default' : manager.Lib('openmpi')
        }


        self.env = os.environ.copy()

        self.prefix = 'INTERFERENCE'
        self.localid_var = 'OMPI_COMM_WORLD_LOCAL_RANK'

        self.schedulers = (("cfs",), ("pinned",))
        self.affinities = (("2-3",), ("1,3",))

        self.nodes = ((1,),)

        self.runs = ((i,) for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = self.env['HOME'] + '/hostfiles'

        super(PlanetaOS, self).__init__(args)

    def get_nodelist(self):
        return [socket.gethostname()]

    def format_command(self, bench, nodes):
        parameters = " ".join([self.mpiexec_hostfile.format(self.hostfile.path),
                               self.mpiexec_np, str(bench.np),
                               self.preload.format(self.get_lib()),
                               '-oversubscribe',
                               '--bind-to none'])
        return "{} {} ./bin/{}".format(self.mpiexec, parameters, bench.name)

    def correct_guess():
        if socket.gethostname() == 'planeta-os':
            return True
        return False
