class Filter(object):
    def __init__(self, filter_str):
        self.params = dict(map(lambda x: x.split('='), filter_str.split(':')))
        for k in self.params:
            self.params[k] = self.params[k].split(',')

    def skip(self, bench):
        for k in self.params:
            if k in bench.__dict__:
                present = False
                for v in self.params[k]:
                    val = type(bench.__dict__[k])(v)
                    if val == bench.__dict__[k]:
                        present = True
                        break
                if not present:
                    return True
        return  False

    def create_filter(filter_str):
        return Filter(filter_str)

class EmptyFilter(Filter):
    def __init__(self):
        pass

    def skip(self, bench):
        return False
