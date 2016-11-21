#/bin/bash

BASE=$(dirname $0)

export PYTHONPATH=$PYTHONPATH:$BASE/../scripts/:$BASE/../

python3 $BASE/args.py