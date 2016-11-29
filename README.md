# Interference

This project is a collection of scripts to run benchmarks on different
machines. The main goal is to have the shortest command possible to
rerun all the variation of benchmarks in a given set of nodes.

## How to use

There are two main commands to use when initial setup is done.

For example, you want to run benchmarks on taurus.

1. Compile preload library, which intercepts `MPI_Init` and `MPI_Finalize`

This step you need to do when you change the library:

    $ ./scripts/interference.py --machine taurus prepare taurus
    
Yes, you need to repeat "taurus" two times. Sorry for that.

2. Run the benchmarks

The command may look as follows:

    $ ./scripts/interference.py --machine taurus run --writer json -o runtimes-ffmk-c.log
    
I suggest to use json as output format currently, because it also is
able to store additional counters.

An alternative is to use csv, but two main counters you will get are
cpu time and wall clock time. Maybe this is enough.

This command first compiles all the benchmarks, then it run them one by one.

If you do not want to run all the benchmarks at once, you can apply filtering:

    $ ./scripts/interference.py --machine taurus run --writer json --filter prog=ep:nodes=2:size=C:oversub=2:schedulers=cfs -o runtimes-ffmk-c.log
    
Format is key1=v1,v2:key2=v3:...

## How to set things up

I recommend to put the project in home directory, so that the path is:

~/interference

Then put the benchmarks (this step probably has more significance)
into ~/interference-bench

You can download ~/interference-bench from erwin: ~mplaneta/interfence-bench

The benchmark directory contains all the benchmarks
