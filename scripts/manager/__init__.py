def m(x, y):
    z = x.copy()
    z.update(y)
    return z

from .machine import Machine
from .cache import Cache
from .benchmark import Benchmark, BenchGroup
from .lib import Lib
from .context import Context
from .writer import CsvWriter, JsonWriter, Writer
from .filter import Filter, EmptyFilter
