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

        nodes = (1, 2, 4, 8, 16)
        cpu_per_node = 24
        oversub_param = {'oversub': (1,),
                         'schedulers': ("cfs", "pinned")}
        fullsub_param = {'oversub': (2, 4),
                         'schedulers': ("cfs")}

        def np_func(nodes, oversub):
            return nodes * cpu_per_node

        def comd_size_param(size, nodes, oversub):
            np = np_func(nodes, oversub)
            # Ensure that f has at least 3 groups
            domains = Miniapp.partition(np, 3)
            problem_size = '-x 200 -y 200 -z 200'
            decomposition = '-i {} -j {} -k {} '.format(*domains)
            return decomposition + problem_size

        self.modules_load = 'source {}/mini.env'.format(base)
        compile_command = self.modules_load + '; cd ../src-mpi ; make'
        tmpl = './{prog} {size_param}'
        comd_param = {
            'prog': ("CoMD-mpi",),
            'size': (1,),
            'np': np_func,
            'nodes': nodes,
            'affinity': ("0-23",),
            'size_param': comd_size_param,
            'wd': base + "CoMD/bin",
            'compile_command': compile_command,
            'tmpl': tmpl}
        self.group = \
            manager.BenchGroup(Miniapp, **comd_param, **fullsub_param) + \
            manager.BenchGroup(Miniapp, **comd_param, **oversub_param)

        compile_command = self.modules_load + '; make lassen_mpi'

        def lassen_size_param(size, nodes, max_nodes, oversub):
            np = np_func(nodes, oversub)
            # Ensure that f has at least 3 groups
            domains = Miniapp.partition(np, 3)
            decomposition = '{} {} {}'.format(*domains)
            global_zones = ' {}'.format(cpu_per_node * max_nodes * size) * 3
            return "default {} {}".format(decomposition, global_zones)

        lassen_param = {
            'prog': ("lassen_mpi",),
            'size_param': lassen_size_param,
            'size': (1,),
            'affinity': ("0-23",),
            'nodes': nodes,
            'np': np_func,
            'max_nodes': max(nodes),
            'compile_command': compile_command,
            'wd': base + "lassen/",
            'tmpl': tmpl
        }
        self.group += \
            manager.BenchGroup(Miniapp, **lassen_param, **oversub_param) + \
            manager.BenchGroup(Miniapp, **lassen_param, **fullsub_param)

        def lulesh_np_func(nodes):
            return {1: 8, 2: 27, 4: 64, 8: 125, 16: 343}[nodes]

        compile_command = self.modules_load + '; make'
        lulesh_param = {
            'prog': ("lulesh2.0",),
            'size_param': ("-i 300 -c 10 -b 3",),
            'size': (1,),
            'affinity': ("0-23",),
            'nodes': nodes,
            'np': lulesh_np_func,
            'wd': base + "lulesh2.0.3/",
            'compile_command': compile_command,
            'tmpl': tmpl
        }
        self.group += \
            manager.BenchGroup(Miniapp, **lulesh_param, **oversub_param) + \
            manager.BenchGroup(Miniapp, **lulesh_param, **fullsub_param)

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
