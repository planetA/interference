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
            manager.BenchGroup(Npb, progs = ("bt-mz",),
                               sizes = ("W", "S"),
                               np = (2, 4),
                               wd = base + "NPB3.3.1-MZ/NPB3.3-MZ-MPI/") + \
            manager.BenchGroup(Npb, progs = ("sp-mz",),
                               sizes = ("W", "S"),
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

        self.preload = '-x LD_PRELOAD={}'.format(self.get_interference_path())

        self.prefix = 'INTERFERENCE'
        self.localid_var = 'OMPI_COMM_WORLD_LOCAL_RANK'

        self.schedulers = (("cfs",), ("pinned",))
        self.affinities = (("2-3",), ("1,3",))

        self.nodes = ((1,),)

        self.runs = ((i,) for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = os.environ['HOME'] + '/hostfiles'

        super(PlanetaOS, self).__init__(args)

    def get_nodelist(self):
        return [socket.gethostname()]

    def format_command(self, bench, nodes):
        parameters = " ".join([self.mpiexec_hostfile.format(self.hostfile.path),
                               self.mpiexec_np, str(bench.np),
                               self.preload,
                               '-oversubscribe',
                               '--bind-to none'])
        return "{} {} ./bin/{}".format(self.mpiexec, parameters, bench.name)

    def augment_env(self, env, bench, sched, affinity):
        pass

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-o',
                        help='Where to dump all runtimes.',
                        type=str,
                        dest='out',
                        required=True)
    parser.add_argument('--cache',
                        help='Cache compilation results, use cache if possible.',
                        action='store_true',
                        default=False)
    return parser.parse_args()

def create_machine(args):
    return PlanetaOS(args)

def main():
    args = parse_args()

    machine = create_machine(args)

    machine.compile()

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
