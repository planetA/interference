import os
import socket
import subprocess as sp

import manager

from .npb import Npb


class Taurus(manager.Machine):
    def __init__(self, args):
        base = os.environ['HOME'] + '/interference-bench/'

        nodes = (1,)

        self.group = \
            manager.BenchGroup(Npb, progs=("bt-mz", "sp-mz"),
                               sizes=("S",),
                               np=(2, 4),
                               nodes=nodes,
                               wd=base + "NPB3.3.1-MZ/NPB3.3-MZ-MPI/") + \
            manager.BenchGroup(Npb, progs=("bt-mz", "sp-mz"),
                               sizes=("W",),
                               np=(2, 4, 8),
                               nodes=nodes,
                               wd=base + "NPB3.3.1-MZ/NPB3.3-MZ-MPI/") + \
            manager.BenchGroup(Npb,
                               progs=("bt", "sp"),
                               sizes=("W", "S"),
                               np=(4, 9),
                               nodes=nodes,
                               wd=base + "/NPB3.3.1/NPB3.3-MPI/") + \
            manager.BenchGroup(Npb,
                               progs=("cg", "ep", "ft",
                                      "is", "lu", "mg"),
                               sizes=("W", "S"),
                               np=(2, 4, 8),
                               nodes=nodes,
                               wd=base + "/NPB3.3.1/NPB3.3-MPI/")

        self.mpiexec = 'mpirun_rsh'
        self.mpiexec_np = '-np'
        self.mpiexec_hostfile = '-hostfile {}'

        self.preload = 'LD_PRELOAD={}'

        self.lib = manager.Lib('mvapich',
                               compile_pre='source ~/scr/pi/pi.env',
                               compile_flags='')

        self.env = os.environ.copy()
        self.env['OMP_NUM_THREADS'] = '1'
        self.env['INTERFERENCE_LOCALID'] = 'MV2_COMM_WORLD_LOCAL_RANK'
        self.env['INTERFERENCE_HACK'] = 'true'

        self.prefix = 'INTERFERENCE'

        self.schedulers = ("cfs", "pinned")
        self.affinities = ("2-3", "1,3")

        self.runs = (i for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = os.environ['HOME'] + '/hostfiles'

        super(Taurus, self).__init__(args)

    def get_nodelist(self):
        p = sp.run('scontrol show hostnames'.split(),
                   stdout=sp.PIPE)
        if p.returncode:
            raise Exception("Failed to get hosts")

        return p.stdout.decode('UTF-8').splitlines()

    def format_command(self, context):
        parameters = " ".join([self.mpiexec_hostfile.format(self.hostfile.path),
                               self.mpiexec_np, str(context.bench.np),
                               '-ssh',
                               '-export-all'])
        source = "source {}/scr/pi/pi.env".format(self.env['HOME'])
        command = "{} ; taskset 0xFFFFFFFF {} {} {} ./bin/{}"
        return command.format(source, self.mpiexec, parameters,
                              self.preload.format(self.get_lib()),
                              context.bench.name)

    def correct_guess():
        if 'taurusi' in socket.gethostname():
            return True
        return False
