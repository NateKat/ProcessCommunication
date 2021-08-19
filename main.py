import numpy as np
import multiprocessing as mp
import logging
import socket

logger = mp.log_to_stderr(logging.DEBUG)


def data_vector_gen(seed=100, vector_size=50):
    """
    Generator of normal (uniform Gaussian distribution) vector
    :param seed: seed for random
    :param vector_size: vector size: (1 x vector_size)
    :return: yields the next vector for each call
    """
    np.random.RandomState(seed)
    while True:
        yield np.random.normal(size=vector_size)


class Analyser(mp.Process):
    def __init__(self, socket_obj):
        mp.Process.__init__(self)
        self.socket = socket_obj

    def run(self):
        self.socket.bind(('', 9090))
        self.socket.listen(5)
        logger.debug("Server listening")
        print("Server listening!")


class Generator(mp.Process):
    def __init__(self, socket_obj):
        mp.Process.__init__(self)
        self.socket = socket_obj

    def run(self):
        while True:
            client, address = self.socket.accept()
            logger.debug("{u} connected".format(u=address))
            client.send("OK")
            print("client sent")
            client.close()


if __name__ == '__main__':

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    p1 = mp.Process(target=Generator, args=(server_socket,))
    p2 = mp.Process(target=Analyser, args=(server_socket,))

    p1.start()
    p2.start()

    # starting Processes here parallel by using start function.
    p1.join()
    # this join() will wait until the calc_square() function is finished.
    p2.join()
    # this join() will wait unit the calc_cube() function is finished.
    print("Successes!")
