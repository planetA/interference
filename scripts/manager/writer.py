import csv
import json

from . import m

class Writer:
    def __init__(self, filename):
        self.filename = filename

    def __enter__(self):
        self.log = open(self.filename, 'w')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.log.close()

    def create_writer(writer_type):
        if writer_type == "csv":
            return CsvWriter
        elif writer_type == "json":
            return JsonWriter
        else:
            raise Exception("Unknown writer type: {}" % (writer_type))

class CsvWriter(Writer):
    """CsvWriter expects certain output format for legacy reasons.
    Flexible writing should happen in JsonWriter.

    """
    def __init__(self, filename):
        super().__init__(filename)

    def __enter__(self):
        super().__enter__()
        self.csv = csv.writer(self.log)
        self.csv.writerow(['prog', 'nodes', 'np', 'size', 'oversub', 'run',
                           'sched', 'affinity', 'cpu', 'rank', 'node', 'iter',
                           'utime', 'wtime', 'stime'])
        return self

    def submit(self, run, bench, results):
        for l in results:
            row = {k.strip(): v.strip()
                   for (k, v) in
                   map(lambda x: x.split(':'),
                       filter(lambda x: ':' in x,
                              l.split(',')))}
            self.csv.writerow([bench.prog, bench.nodes, bench.np,
                               bench.size, bench.oversub, run,
                               bench.schedulers, bench.affinity,
                               row['CPU'], row['RANK'], row['NODE'],
                               row['ITER'],
                               row['UTIME'], row['WTIME'], row['STIME']])
        self.log.flush()

    def __repr__(self):
        return 'csv'

class JsonWriter(Writer):
    def __init__(self, filename, skiplist = ('wd', 'compile_command', 'tmpl')):
        super().__init__(filename)
        self.name = 'json'
        self.rows = list()
        self.skiplist = skiplist

    def submit(self, run, bench, results):
        lines = json.loads(results[0])
        for l in lines["INTERFERENCE"]:
            bench_dict = {k : v for (k,v) in bench.__dict__.items() if k not in self.skiplist}
            row = m({'run': run},
                    m(bench_dict, l))
            print(row)
            self.rows.append(row)

    def __exit__(self, exc_type, exc_value, traceback):
        json.dump(self.rows, self.log)
        super().__exit__(exc_type, exc_value, traceback)

    def __repr__(self):
        return 'json'
