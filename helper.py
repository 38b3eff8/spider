import time


def log_time():
    d = {}

    def set_d():
        t = time.localtime(time.time())
        dt = d
        for index in range(5):
            if not dt.get(t[index]):
                dt[t[index]] = {}
            dt = dt[t[index]]

        if dt.get(t[5]) is None:
            dt[t[5]] = 0
        else:
            dt[t[5]] += 1
        return d

    return set_d


def print_d(d, t=None):
    if t is None:
        t = time.localtime(time.time())

    print('{0}-{1}-{2}'.format(t[0], t[1], t[2]))
    print('\t{0}:{1}:{2} -> {3}'.format(t[3], t[4], t[5], d[t[0]][t[1]][t[2]][t[3]][t[4]].get(t[5] - 1)))


'''
set_d = log_time()

for item in range(1000000):
    print_d(set_d(), time.localtime(time.time()))
'''
