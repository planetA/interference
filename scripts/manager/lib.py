class Lib:
    def __init__(self, name='default', **kwargs):
        if 'name' not in kwargs:
            self.name = 'default'
        else:
            self.name = kwargs['name']

        if 'compile_pre' not in kwargs:
            self.compile_pre = ''
        else:
            self.compile_pre = kwargs['compile_pre']

        if 'compile_flags' not in kwargs:
            self.compile_flags = '-Dtest=ON -Dfortran=ON'
        else:
            self.compile_flags = kwargs['compile_flags']

        self.prefix = 'INTERFERENCE'
