import functools
import time
from math import floor
import sys
from logger import create_logger

logger = create_logger()


def timer(func):
    """Print the runtime of the decorated function"""
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()
        value = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        logger.debug(f"Finished {func.__name__!r} in {run_time:.4f} secs")
        return value, run_time
    return wrapper_timer


class ThrottleDecorator(object):
    """
    Rate limit decorator class.
    """
    def __init__(self, calls=1000, period=1):
        """
        Instantiate a ThrottleDecorator with some sensible defaults.

        :param int calls: Maximum function invocations allowed within a time period. Must be a number greater than 0.
        :param float period: An upper bound time period (in seconds) before the rate limit resets. Must be a number
        greater than 0.
        """
        self.calls = max(1, min(sys.maxsize, floor(calls)))
        self.period = period
        self.clock = time.perf_counter

        # Initialise the decorator state.
        self.freq = self.period / self.calls
        self.num_calls = 0
        self.run_time = 0
        self.start = None

    def __call__(self, func):
        """
        Return a wrapped function that prevents further function invocations if
        previously called within a specified period of time.

        :param function func: The function to decorate.
        :return: Decorated function.
        :rtype: function
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """
            Extend the behaviour of the decorated function, forwarding function
            invocations previously called no sooner than a specified period of time.

            :param args: non-keyword variable length argument list to the decorated function.
            :param kwargs: key-worded variable length argument list to the decorated function.
            """
            if not self.start:
                self.start = self.clock()
            value = func(*args, **kwargs)
            self.num_calls += 1
            try:
                time.sleep(self.num_calls * self.freq - (self.clock() - self.start))
            except ValueError:
                pass  # Ignore unnecessary sleeping (negative time period)

            logger.debug(f"{func.__name__!r} ran in average of {(self.clock() - self.start) / self.num_calls:.3f} secs")
            return value
        return wrapper
