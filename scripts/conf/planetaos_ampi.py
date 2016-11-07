import os
import socket

import manager

from .miniapp import Miniapp


class PlanetaOS_AMPI(manager.Machine):
    def __init__(self, args):
        base = "/home/desertfox/research/projects/ffmk/interference-bench/"
        nodes = (1,)

        tmpl = './bin/charmrun +p{np} ./bin/{prog}' \
            ' ++nodelist {hostfile} +vp{vp} {size} ++local'
        self.group = \
            manager.BenchGroup(Miniapp, prog=("CoMD-ampi",),
                               size=("-i 2 -j 1 -k 1",),
                               vp=(2,),
                               np=(1, 2),
                               nodes=nodes,
                               wd=base + "CoMD-1.1/",
                               tmpl=tmpl) + \
            manager.BenchGroup(Miniapp, prog=("CoMD-ampi",),
                               size=("-i 2 -j 2 -k 1",),
                               vp=(4,),
                               np=(1, 2, 4),
                               nodes=nodes,
                               wd=base + "CoMD-1.1/",
                               tmpl=tmpl) + \
            manager.BenchGroup(Miniapp, prog=("CoMD-ampi",),
                               size=("-i 2 -j 2 -k 2",),
                               vp=(8,),
                               np=(2, 4),
                               nodes=nodes,
                               wd=base + "CoMD-1.1/",
                               tmpl=tmpl)

        self.preload = 'LD_PRELOAD={}'

        self.env = os.environ.copy()

        charm_path = self.env['HOME'] + '/research/projects/ffmk/charm/netlrts-linux-x86_64-gfortran-gcc/'
        self.env['PATH'] = self.env['PATH'] + ":" + charm_path + "bin"
        old_ld = self.env['LD_LIBRARY_PATH'] + \
            ':' if 'LD_LIBRARY_PATH' in self.env else ''

        self.lib = manager.Lib('charm', '-Dtest=ON -Dfortran=ON -DMPI_CC_COMPILER=ampicc'
                               ' -Dwrapper=OFF'
                               ' -DMPI_CXX_COMPILER=ampicxx -DMPI_CXX_INCLUDE_PATH={path}/include/'
                               ' -DMPI_C_INCLUDE_PATH={path}/../include/'.format(path=charm_path))

        self.prefix = 'INTERFERENCE'

        self.schedulers = ("cfs",)
        self.affinities = ("2-3", "1,3")

        self.runs = (i for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = self.env['HOME'] + '/hostfiles'

        super().__init__(args)

        self.env['LD_LIBRARY_PATH'] = old_ld + self.get_lib_path()
        print(self.env['LD_LIBRARY_PATH'])

    def get_nodelist(self):
        return list(map(lambda x: 'host ' + str(x), (socket.gethostname())))

    def format_command(self, context):
        command = " ".join(
            [context.bench.name.format(hostfile=context.hostfile.path)])
        print(command)
        return command

    def correct_guess():
        if socket.gethostname() == 'planeta-os':
            return True
        return False
