import time

_module_load_start = time.clock()

def _time_elapsed():
	return time.clock() - _module_load_start
