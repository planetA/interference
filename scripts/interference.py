#!/usr/bin/env python3

import csv

from argparse import ArgumentParser

from conf import *


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--machine',
                        help='Which configuration use to run benchmarks',
                        default='guess')
    parser.add_argument('--mpi',
                        help='Which mpi library to work with',
                        default='default')
    parser.set_defaults(comm=None)

    commands = parser.add_subparsers(help='Choose mode of operation')

    run_parser = commands.add_parser(
        'run', help='Compile and run all benchmarks')
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
    compile_parser.add_argument('target', default=['default'])
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
    elif args.machine == 'planeta-ampi':
        return PlanetaOS_AMPI(args)
    elif args.machine == 'taurus-mini':
        return Taurus_Mini(args)
    elif args.machine == 'taurus-ampi':
        return Taurus_AMPI(args)

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
