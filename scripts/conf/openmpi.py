import manager

class OpenMPI(manager.Lib):
    def __init__(self, compile_flags='-Dfortran=ON -Dtest=ON'):
        super().__init__(name='openmpi', compile_flags=compile_flags)
        self.mpiexec = 'mpirun'
        self.mpiexec_np = '-np'
        self.mpiexec_hostfile = '-hostfile {}'

        self.preload = '-x LD_PRELOAD={}'

    def format_command(self, context):
        context.env['INTERFERENCE_LOCALID'] = 'OMPI_COMM_WORLD_LOCAL_RANK'
        context.env['INTERFERENCE_LOCAL_SIZE'] = 'OMPI_COMM_WORLD_LOCAL_SIZE'

        hostfile = self.mpiexec_hostfile.format(context.hostfile.path)
        preload = self.preload.format(context.machine.get_lib())
        parameters = " ".join([hostfile,
                               self.mpiexec_np, str(context.bench.np),
                               preload,
                               '-oversubscribe',
                               '--bind-to none'])
        return "{} {} ./bin/{}".format(self.mpiexec, parameters,
                                       context.bench.name)
