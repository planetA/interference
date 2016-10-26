import os
import pickle
import subprocess
import itertools
import tempfile
import subprocess as sp

class Machine:
    class Hostfile:
        def __init__(self, machine, nodes):
            if not os.path.exists(machine.hostfile_dir):
                os.makedirs(machine.hostfile_dir)

            (fd,
             self.path) = tempfile.mkstemp(prefix='hostfile.',
                                           dir = machine.hostfile_dir, text=True)
            self.hostfile = open(self.path, "w")
            self.hostfile.write("\n".join(machine.nodelist[:nodes])+'\n')
            self.hostfile.flush()

        def __enter__(self):
            return self.hostfile

        def __exit__(self, exc_type, exc_value, traceback):
            self.hostfile.close()
            if os.path.exists(self.path):
                os.remove(self.path)

    def __init__(self, args):
        self.args = args

        self.env = os.environ.copy()
        self.env['INTERFERENCE_PREFIX'] = self.prefix
        self.env['INTERFERENCE_LOCALID'] = self.localid_var

    def get_script_path(self):
        return os.path.dirname(os.path.realpath(__file__))

    def get_interference_path(self):
        return self.get_script_path() + "/../../lib/libinterference.so"


    def configurations(self):
        confs = tuple(sum(x, ()) for x in
                      itertools.product(self.benchmarks,
                                        self.schedulers,
                                        self.nodes,
                                        self.affinities,
                                        self.runs))
        res = list()
        for (bench, sched, nodes, affinity, run) in confs:
            env = self.env.copy()
            env['INTERFERENCE_AFFINITY'] = affinity
            env['INTERFERENCE_SCHED'] = sched
            self.augment_env(env, bench, sched, affinity)
            res.append((bench, nodes, env, sched, affinity, run))
        return res

    class Cache:
        def __init__(self, machine):
            self.machine = machine
            name = '.{}.pkl'.format(type(self.machine).__name__)
            if not os.path.isfile(name) or not self.machine.args.cache:
                self.compiled = dict()
                return
            with open(name, 'rb') as cache:
                self.compiled = pickle.load(cache)

        def __contains__(self, key):
            return key in self.compiled

        def add(self, key):
            self.compiled[key] = key.fail
            self.__save()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.__save()

        def __save(self):
            if not self.machine.args.cache:
                return
            name = '.{}.pkl'.format(type(self.machine).__name__)
            with open(name, 'wb') as cache:
                pickle.dump(self.compiled, cache, 0)
                            #pickle.HIGHEST_PROTOCOL)


    def compile(self):
        """ Compile benchmarks """

        with self.Cache(self) as cache:
            env = self.env.copy()

            # execute compilation command
            for b_l in self.benchmarks:
                b = b_l[0]
                if b in cache:
                    b_l[0].fail = cache.compiled[b]
                    continue
                b.compile(env)

                cache.add(b)

    def create_hostfile(self, nodes):
        self.hostfile = self.Hostfile(self, nodes)
        return self.hostfile

    def run_benchmarks(self, runtimes_log):
        print('-'*62)
        for cfg in self.configurations():
            (bench, nodes, env, sched, affinity, run) = cfg

            if bench.fail:
                continue

            with self.create_hostfile(nodes) as hostfile:
                command = self.format_command(bench, nodes)
                print("Run ", bench.name, nodes, {i : env[i] for i in filter(lambda k : 'INTERFERENCE' in k, env.keys())})
                print(command)
                p = sp.Popen(command, stdout = sp.PIPE, stderr = sp.STDOUT,
                             cwd = bench.wd, env = env, shell = True)
                out = p.stdout.read().decode('UTF-8')
                err = p.stdout.read().decode('UTF-8')
                p.communicate()

                if (p.returncode):
                    print("Error")
                    print("".join(out))
                    print("".join(err))
                    print(p.returncode)
                    continue

                results = list(filter(lambda x : self.prefix in x, out.splitlines()))
                if len(results) == 0:
                    print("Failed to get profiling data")
                    print("".join(out))
                    print("".join(err))
                    continue
                for l in results:
                    row = {k.strip() : v.strip()
                           for (k,v) in
                            map(lambda x : x.split(':'),
                                filter(lambda x : ':' in x,
                                       l.split(',')))}
                    print(row)
                    runtimes_log.writerow([bench.name,
                                           nodes,
                                           bench.np,
                                           bench.size,
                                           run,
                                           sched,
                                           affinity,
                                           row['CPU'],
                                           row['RANK'],
                                           row['NODE'],
                                           row['ITER'],
                                           row['UTIME'],
                                           row['WTIME']])

                print('='*40)
                continue