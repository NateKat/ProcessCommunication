import numpy as np
import multiprocessing as mp
import logging
from numpysocket import NumpySocket
from time import sleep
from ratelimit import limits, RateLimitException

logger = mp.log_to_stderr(logging.INFO)


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


class CommunicationProc(mp.Process):
    def __init__(self, ip='127.0.0.1', port=12345):
        super().__init__()
        self.ip = ip
        self.port = port
        self.np_socket = None


class AnalyseClient(CommunicationProc):
    def __init__(self, ip, port):
        super().__init__(ip, port)

    def run(self):
        self.np_socket = NumpySocket()
        while True:
            try:
                self.np_socket.startClient(self.ip, self.port)
                logger.debug("connected to server")
                break
            except ConnectionRefusedError:
                logger.warning(f'Connection failed, make sure `server` is running.')
                sleep(1)
                continue

        for i in range(10):
            self.data_handler()

        try:
            self.np_socket.close()
        except OSError:
            logging.error("server already disconnected")

    def data_handler(self):
        matrix = self.stack_matrix()
        mean, std = self.matrix_analytics(matrix)

    def stack_matrix(self, mat_col=100):
        matrix = self.np_socket.receive(socket_buffer_size=16)  # buffer size must be smaller than vector size
        for i in range(mat_col - 1):
            frame = self.np_socket.receive(socket_buffer_size=16)  # buffer size must be smaller than vector size
            logger.debug("array received:")
            logger.debug(frame)
            matrix = np.vstack((matrix, frame))
        logger.debug(matrix)
        return matrix

    def matrix_analytics(self, matrix):
        r1 = np.mean(matrix, axis=0)
        r2 = np.std(matrix, axis=0)
        return r1, r2


class VecGenServer(CommunicationProc):
    def __init__(self, ip, port):
        super().__init__(ip, port)

    def run(self):
        self.np_socket = NumpySocket()
        logger.debug("starting server, waiting for client")
        self.np_socket.startServer(self.ip, self.port)

        self.send_data()
        logger.info("closing connection")
        try:
            self.np_socket.close()
        except OSError:
            logging.error("client already disconnected")

    def send_data(self):
        for vec in data_vector_gen(vector_size=5):
            logger.debug("sending numpy array:")
            logger.debug(vec)
            try:
                self.send_vector(vec)
            except RateLimitException:
                continue
            except (ConnectionResetError, ConnectionAbortedError):
                logging.error("client disconnected")
                break

    @limits(calls=1, period=0.001)
    def send_vector(self, vector):
        self.np_socket.send(vector)


if __name__ == '__main__':
    default_ip, default_port = '127.0.0.1', 50066

    ps = VecGenServer(default_ip, default_port)
    pc = AnalyseClient(default_ip, default_port)

    ps.start()
    pc.start()

    pc.join()
    ps.join()
    print("Successes!")
