#!/usr/bin/env python3

import socket
import manager
import subprocess as sp
import itertools
import os
import csv

from argparse import ArgumentParser

class Npb(manager.Benchmark):
    """ Class representing an npb benchmark """
    def __init__(self, prog, np, size, wd):
        super(Npb, self).__init__()

        self.prog = prog
        self.np = np
        self.size = size
        self.wd = wd

        self.compile_command = "make {} NPROCS={} CLASS={}".format(prog, np, size)

        self.name = "{}.{}.{}".format(self.prog, self.size, self.np)

    def __eq__(self, other):
        return ((self.prog == other.prog) and (self.np == self.np) and
                (self.size == other.size) and (self.wd == other.wd))

    def __hash__(self):
        return hash((self.prog, self.np, self.size, self.wd))

    def __str__(self):
        return "{}.{}.{} {}".format(self.prog, self.size, self.np, self.fail)


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

class Taurus(manager.Machine):
    def __init__(self, args):
        base = os.environ['HOME']+'/interference-bench/'

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

        self.mpiexec = 'mpirun_rsh'
        self.mpiexec_np = '-np'
        self.mpiexec_hostfile = '-hostfile {}'

        self.preload = 'LD_PRELOAD={}'

        self.known_libs = {
            'default' : manager.Lib('mvapich',
                                    compile_pre='source ~/scr/pi/pi.env',
                                    compile_flags='')
        }

        self.env = os.environ.copy()
        self.env['OMP_NUM_THREADS'] = '1'

        self.prefix = 'INTERFERENCE'
        self.localid_var = 'MV2_COMM_WORLD_LOCAL_RANK'

        self.schedulers = (("cfs",), ("pinned",))
        self.affinities = (("2-3",), ("1,3",))

        self.nodes = ((1,),)

        self.runs = ((i,) for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = os.environ['HOME'] + '/hostfiles'

        super(Taurus, self).__init__(args)

    def get_nodelist(self):
        p = sp.run('scontrol show hostnames'.split(),
                       stdout = sp.PIPE)
        if p.returncode:
            raise Exception("Failed to get hosts")

        return p.stdout.decode('UTF-8').splitlines()

    def format_command(self, bench, nodes):
        parameters = " ".join([self.mpiexec_hostfile.format(self.hostfile.path),
                               self.mpiexec_np, str(bench.np),
                               '-ssh',
                               '-export-all'])
        source = "source {}/scr/pi/pi.env".format(self.env['HOME'])
        return "{} ; taskset 0xFFFFFFFF {} {} {} ./bin/{}".format(source,
                                                                      self.mpiexec, parameters,
                                                                      self.preload.format(self.get_lib()), bench.name)

    def correct_guess():
        print(socket.gethostname())
        if 'taurusi' in socket.gethostname():
            return True
        return False

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--machine',
                        help='Which configuration use to run benchmarks',
                        default='guess')
    parser.add_argument('--mpi',
                        help='Which mpi library to work with',
                        default='default')
    parser.set_defaults(comm=None)

    commands = parser.add_subparsers(help = 'Choose mode of operation')

    run_parser = commands.add_parser('run', help='Compile and run all benchmarks')
    run_parser.add_argument('-o',
                            help='Where to dump all runtimes.',
                            type=str,
                            dest='out',
                            required=True)
    run_parser.add_argument('--cache',
                            help='Cache compilation results, use cache if possible.',
                            action='store_true',
                            default=False)
    run_parser.set_defaults(comm='run')

    compile_parser = \
      commands.add_parser('prepare',
       help='Prepare libinterference for a specific MPI library')
    compile_parser.add_argument('targets', nargs='*', default=['default'])
    compile_parser.set_defaults(comm='prepare')

    args = parser.parse_args()
    if args.comm is None:
        parser.print_help()
        raise Exception('No command has been chosen')

    return args

def create_machine(args):
    print(args.machine)
    if args.machine == 'guess':
        if PlanetaOS.correct_guess():
            return PlanetaOS(args)
        elif Taurus.correct_guess():
            return Taurus(args)
    elif args.machine == 'planeta':
        return PlanetaOS(args)
    elif args.machine == 'taurus':
        return PlanetaOS(args)

    raise Exception("Failed to identify the machine." +
                    " Probably you need to create a new configuration")

def main():
    args = parse_args()

    machine = create_machine(args)

    if args.comm == 'prepare':
        machine.compile_libs()
    elif args.comm == 'run':
        machine.compile_benchmarks()

        # with open('runtimes.log', 'w') as runtimes_log:
        with open(args.out, 'w') as runtimes_log:
            runtimes = csv.writer(runtimes_log)
            runtimes.writerow(['prog', 'nodes', 'np',
                               'size', 'run',
                               'sched', 'affinity', 'cpu',
                               'rank', 'node', 'iter',
                               'utime', 'wtime'])

            machine.run_benchmarks(runtimes)



if __name__ == '__main__':
    main()
