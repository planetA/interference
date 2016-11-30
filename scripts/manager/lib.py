class Lib:
    def __init__(self, name='default',
                 compile_flags = '-Dtest=ON -Dfortran=ON',
                 compile_pre = ""):
        self.compile_pre = compile_pre
        self.compile_flags = compile_flags
        self.name = name
        self.prefix = 'INTERFERENCE'
