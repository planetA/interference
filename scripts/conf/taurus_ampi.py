import os
import socket
import subprocess as sp

import manager

from .miniapp import Miniapp


class Taurus_AMPI(manager.Machine):
    def __init__(self, args):
        self.env = os.environ.copy()

        nodes = (1,)

        base = self.env['HOME'] + "/interference-bench/"
        schedulers = ("cfs",)

        tmpl = './charmrun +p{np} ++mpiexec ++remote-shell {script} ' \
               './{prog} +vp{size} {size_param} ++verbose'
        self.group = \
            manager.BenchGroup(Miniapp, prog=("CoMD-ampi",),
                               size_param=("-i 2 -j 1 -k 1",),
                               size=(2,),
                               np=(1, 2),
                               schedulers=schedulers,
                               nodes=nodes,
                               wd=base + "CoMD-1.1/bin/",
                               tmpl=tmpl) + \
            manager.BenchGroup(Miniapp, prog=("CoMD-ampi",),
                               size_param=("-i 2 -j 2 -k 1",),
                               size=(4,),
                               np=(1, 2),
                               schedulers=schedulers,
                               nodes=nodes,
                               wd=base + "CoMD-1.1/bin/",
                               tmpl=tmpl) + \
            manager.BenchGroup(Miniapp, prog=("CoMD-ampi",),
                               size_param=("-i 2 -j 2 -k 2",),
                               size=(8,),
                               np=(2, 4),
                               schedulers=schedulers,
                               nodes=nodes,
                               wd=base + "CoMD-1.1/bin/",
                               tmpl=tmpl)

        self.group = \
            manager.BenchGroup(Miniapp, prog=("lassen_mpi",),
                               size_param=("default 2 2 2 200 200 200",),
                               size=(8,),
                               np=(1, 2),
                               schedulers=schedulers,
                               nodes=nodes,
                               wd=base + "Lassen-1.0/",
                               tmpl=tmpl)

        self.group = \
            manager.BenchGroup(Miniapp, prog=("lulesh2.0",),
                               size_param=("-i 300 -c 10 -b 3",),
                               size=(8,),
                               np=(2,),
                               schedulers=schedulers,
                               nodes=nodes,
                               wd=base + "Lulesh-2.0/",
                               tmpl=tmpl)

        charm_path = self.env['HOME'] + \
            '/ampi/charm/verbs-linux-x86_64-gfortran-gcc/'
        self.env['PATH'] = self.env['PATH'] + ":" + charm_path + "bin"

        self.lib = manager.Lib('charm', '-Dtest=ON -Dfortran=ON -DMPI_CC_COMPILER=ampicc'
                               ' -Dwrapper=OFF'
                               ' -DMPI_CXX_COMPILER=ampicxx'
                               ' -DMPI_CXX_INCLUDE_PATH={path}/include/'
                               ' -DMPI_CXX_LIBRARIES={path}/lib/'
                               ' -DMPI_C_LIBRARIES={path}/lib/'
                               ' -DMPI_C_INCLUDE_PATH={path}/include/'.format(path=charm_path))

        self.prefix = 'INTERFERENCE'

        self.affinities = ("2-3", "1,3")

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

        return list(p.stdout.decode('UTF-8').splitlines())

    def format_command(self, context):
        command = " ".join([context.bench.name.format(script=context.script.path)])
        print(command)
        return command

    def correct_guess():
        if 'taurusi' in socket.gethostname():
            return True
        return False

    def create_context(self, machine, cfg):
        return self.Context(self, cfg)

    class Context(manager.Context):
        def __enter__(self):
            self.script = self.create_script(self.machine.hostfile_dir, 'script')
            self.script.f.write("\n".join(
                ['#!/bin/bash -f',
                 'shift',
                 'exec srun -N {nodes} -n $*'.format(nodes=self.nodes)])+'\n')

            return super().__enter__()
