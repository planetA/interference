import pickle
import os

class Cache:
    def __init__(self, machine):
        self.machine = machine
        name = self.name()
        if not os.path.isfile(name) or not self.machine.args.cache:
            self.compiled = dict()
            return
        with open(name, 'rb') as cache:
            self.compiled = pickle.load(cache)

    def name(self):
        return '.{}.pkl'.format(self.machine.suffix)

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
        name = self.name()
        with open(name, 'wb') as cache:
            pickle.dump(self.compiled, cache, pickle.HIGHEST_PROTOCOL)
