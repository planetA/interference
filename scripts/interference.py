#!/usr/bin/env python3

from argparse import ArgumentParser

from manager import *

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--machine',
                        help='Which configuration use to run benchmarks',
                        default='guess')
    parser.add_argument('--mpi',
                        help='Which mpi library to work with',
                        default='default')
    parser.set_defaults(comm=None)

    commands = parser.add_subparsers(help='Choose mode of operation', dest='comm')

    run_parser = commands.add_parser('run',
                                     help='Compile and run all benchmarks')
    run_parser.add_argument('-o',
                            help='Where to dump all runtimes.',
                            type=str,
                            dest='out',
                            required=True)
    run_parser.add_argument('--cache',
                            help='Cache compilation results, use cache if possible.',
                            action='store_true',
                            default=False)
    run_parser.add_argument('--filter',
                            help='String which specfies which subset of benchmarks to run',
                            type=Filter.create_filter,
                            default=EmptyFilter(),
                            dest='filter')
    run_parser.add_argument('--writer',
                            help='Output format.',
                            default='csv',
                            choices=[CsvWriter, JsonWriter],
                            type=Writer.create_writer)
    run_parser.add_argument('--run-order',
                            help='Benchmarks of the same group should run consecutively or interleaving each other.',
                            default='interleave',
                            choices=['interleave', 'consecutive'],
                            dest='run_order',
                            type=str)

    compile_parser = \
        commands.add_parser('prepare',
                            help='Prepare libinterference for a specific MPI library')

    args = parser.parse_args()
    if args.comm is None:
        parser.print_help()
        raise Exception('No command has been chosen')

    return args


def create_machine(args):
    print(args.machine)
    if args.machine == 'guess':
        from conf.planetaos import PlanetaOS
        from conf.taurus import Taurus
        if PlanetaOS.correct_guess():
            return PlanetaOS(args)
        elif Taurus.correct_guess():
            return Taurus(args)
    elif args.machine == 'planeta':
        from conf.planetaos import PlanetaOS
        return PlanetaOS(args)
    elif args.machine == 'taurus':
        from conf.taurus import Taurus
        return Taurus(args)
    elif args.machine == 'planeta-ampi':
        from conf.planeta_ampi import PlanetaOS_AMPI
        return PlanetaOS_AMPI(args)
    elif args.machine == 'taurus-mini':
        from conf.taurus_mini import Taurus_Mini
        return Taurus_Mini(args)
    elif args.machine == 'taurus-ampi':
        from conf.taurus_ampi import Taurus_AMPI
        return Taurus_AMPI(args)
    elif args.machine == 'taurus-rsrv':
        from conf.taurus_rsrv import Taurus_Rsrv
        return Taurus_Rsrv(args)
    elif args.machine == 'ffmk':
        from conf.ffmk import Ffmk
        return Ffmk(args)
    elif args.machine == 'cosel':
        from conf.cosel import Cosel
        return Cosel(args)

    raise Exception("Failed to identify the machine." +
                    " Probably you need to create a new configuration")


def main():
    args = parse_args()

    machine = create_machine(args)

    if args.comm == 'prepare':
        machine.compile_libs()
    elif args.comm == 'run':
        machine.compile_benchmarks()

        with args.writer(args.out) as runtimes_log:
            machine.run_benchmarks(runtimes_log)


if __name__ == '__main__':
    main()
