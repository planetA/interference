import os
import socket
import subprocess as sp

import manager

from .miniapp import Miniapp

class Taurus_AMPI(manager.Machine):
    def __init__(self, args):
        self.env = os.environ.copy()

        base =  self.env['HOME'] + "/interference-bench/"

        tmpl = './bin/charmrun +p{np} ++mpiexec ++remote-shell srun ' \
               './bin/{prog} ++nodelist {hostfile} +vp{vp} {size} ++verbose'
        self.group = \
            manager.BenchGroup(Miniapp, prog = ("CoMD-ampi",),
                               size = ("-i 2 -j 1 -k 1",),
                               vp = (2,),
                               np = (1, 2),
                               wd = base + "CoMD-1.1/",
                               tmpl = tmpl) + \
            manager.BenchGroup(Miniapp, prog = ("CoMD-ampi",),
                               size = ("-i 2 -j 2 -k 1",),
                               vp = (4,),
                               np = (1, 2, 4),
                               wd = base + "CoMD-1.1/",
                               tmpl = tmpl) + \
            manager.BenchGroup(Miniapp, prog = ("CoMD-ampi",),
                               size = ("-i 2 -j 2 -k 2",),
                               vp = (8,),
                               np = (2, 4),
                               wd = base + "CoMD-1.1/",
                               tmpl = tmpl)

        charm_path = self.env['HOME'] + '/ampi/charm/verbs-linux-x86_64-gfortran-gcc/'
        self.env['PATH'] = self.env['PATH'] + ":" + charm_path + "bin"

        self.lib = manager.Lib('charm', '-Dtest=ON -Dfortran=ON -DMPI_CC_COMPILER=ampicc' \
                               ' -Dwrapper=OFF' \
                               ' -DMPI_CXX_COMPILER=ampicxx' \
                               ' -DMPI_CXX_INCLUDE_PATH={path}/include/' \
                               ' -DMPI_CXX_LIBRARIES={path}/lib/' \
                               ' -DMPI_C_LIBRARIES={path}/lib/' \
                               ' -DMPI_C_INCLUDE_PATH={path}/include/'.format(path=charm_path))

        self.prefix = 'INTERFERENCE'

        self.schedulers = ("cfs")
        self.affinities = ("2-3", "1,3")

        self.nodes = (1,)

        self.runs = (i for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = self.env['HOME'] + '/hostfiles'

        super().__init__(args)

        old_ld = self.env['LD_LIBRARY_PATH'] + ':' if 'LD_LIBRARY_PATH' in self.env else ''
        self.env['LD_LIBRARY_PATH'] = old_ld + self.get_lib_path()
        print(self.env['LD_LIBRARY_PATH'])

    def get_nodelist(self):
        p = sp.run('scontrol show hostnames'.split(),
                       stdout = sp.PIPE)
        if p.returncode:
            raise Exception("Failed to get hosts")

        hostnames = p.stdout.decode('UTF-8').splitlines()
        return list(map(lambda x: 'host ' + str(x), hostnames))

    def format_command(self, bench, nodes):
        command = " ".join([bench.name.format(hostfile=self.hostfile.path)])
        print(command)
        return command

    def correct_guess():
        if 'taurusi' in socket.gethostname():
            return True
        return False
