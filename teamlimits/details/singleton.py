
# See Method 3 from https://stackoverflow.com/q/6760685/3023211
class Singleton(type):
    """
    A metaclass for singletons
    """
    __instances = {}

    def __call__(cls, *args, **kwds):
        if cls not in cls.__instances:
            cls.__instances[cls] = super(Singleton, cls).__call__(*args, **kwds)
        return cls.__instances[cls]

