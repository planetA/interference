import manager

class Mvapich(manager.Lib):
    def __init__(self, **kwargs):
        if 'compile_flags' not in kwargs:
            kwargs['compile_flags'] = '-Dtest=OFF -Dfortran=OFF'
        if 'mpiexec' not in kwargs:
            mpiexec = 'mpirun'
        else:
            mpiexec = kwargs['mpiexec']

        super().__init__(name='openmpi', **kwargs)
        if mpiexec == 'mpirun':
            self.mpiexec = 'mpirun'
            self.mpiexec_param = ''
            self.mpiexec_np = '-np'
            self.mpiexec_hostfile = '-hosts {}'

            self.preload = '-env LD_PRELOAD {}'
        elif mpiexec == 'mpirun_rsh':
            self.mpiexec = 'mpirun_rsh'
            self.mpiexec_param = '-ssh -export-all'
            self.mpiexec_np = '-np'
            self.mpiexec_hostfile = '-hostfile {}'
            self.preload = 'LD_PRELOAD={}'
        elif mpiexec == 'srun':
            self.mpiexec = 'srun'
            self.mpiexec_param = '--mpi=pmi2 --overcommit --cpu_bind=none -N {}'
            self.mpiexec_np = '-n'
            self.mpiexec_hostfile = '-w {}'
            self.preload = '--task-prolog={}'
        else:
            raise Exception('Unknown launcher requested: {}'.format(kwargs['mpiexec']))

    def format_command(self, context):
        context.env['OMP_NUM_THREADS'] = '1'
        context.env['INTERFERENCE_HACK'] = 'true'

        if self.mpiexec == 'srun':
            mpiexec_param = self.mpiexec_param.format(context.bench.nodes)
            preload = self.preload.format(context.prologue.path)
            context.env['INTERFERENCE_LOCALID'] = 'SLURM_LOCALID'
            # context.env['INTERFERENCE_LOCAL_SIZE'] = ''
        else:
            context.env['INTERFERENCE_LOCALID'] = 'MV2_COMM_WORLD_LOCAL_RANK'
            context.env['INTERFERENCE_LOCAL_SIZE'] = 'MV2_COMM_WORLD_LOCAL_SIZE'
            mpiexec_param = self.mpiexec_param
            preload = self.preload.format(context.machine.get_lib())
        hostfile = self.mpiexec_hostfile.format(context.nodestr)
        parameters = " ".join([hostfile, self.mpiexec_np,
                               str(context.bench.np),
                               mpiexec_param])
        command = "{} ; taskset 0xFFFFFFFF {} {} {} ./bin/{}"
        return command.format(context.machine.modules_load, self.mpiexec, parameters,
                              preload, context.bench.name)
