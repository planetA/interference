import os
import tempfile
from stat import *

class Context:
    class File:
        def __init__(self, context, field, directory, prefix):
            if not hasattr(context, field):
                setattr(context,field, [])
            if not os.path.exists(directory):
                os.makedirs(directory)

            (self.fd, self.path) \
                = tempfile.mkstemp(prefix=prefix+'.', dir = directory, text=True)
            self.f = open(self.path, "w")
            self.directory = directory

            getattr(context,field).append(self)

    def create_file(self, directory, prefix):
        return self.File(self, 'files', directory, prefix)

    def create_script(self, directory, prefix):
        f = self.File(self, 'scripts', directory, prefix)
        os.chmod(f.path, S_IRUSR | S_IXUSR | S_IWUSR)
        return f

    def __init__(self, machine, cfg):
        self.machine = machine
        (self.run, self.bench, self.env, self.affinity) = cfg

    def __enter__(self):
        if hasattr(self, 'files'):
            for f in self.files:
                f.f.flush()

        if hasattr(self, 'scripts'):
            for f in self.scripts:
                f.f.close()
                os.close(f.fd)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not hasattr(self, 'files'):
            return

        for f in self.files:
            if not f.f.closed:
                f.f.close()
            if os.path.exists(f.path):
                os.remove(f.path)
