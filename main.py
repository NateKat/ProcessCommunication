import numpy as np
import multiprocessing as mp
import logging
from numpysocket import NumpySocket
from time import sleep

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


class CommunicationProc(mp.Process):
    def __init__(self, ip='127.0.0.1', port=12345):
        super().__init__()
        self.ip = ip
        self.port = port


class AnalyseClient(CommunicationProc):
    def __init__(self, ip, port):
        super().__init__(ip, port)

    def run(self):
        np_socket = NumpySocket()
        while True:
            try:
                np_socket.startClient(self.ip, self.port)
                logger.info("connected to server")
                break
            except ConnectionRefusedError:
                logger.warning(f'Connection failed, make sure `server` is running.')
                sleep(1)
                continue

        frame = np_socket.receive(socket_buffer_size=16)  # buffer size must be smaller than vector size
        logger.info("array received:")
        logger.info(frame)

        try:
            np_socket.close()
        except OSError:
            logging.error("server already disconnected")


class VecGenServer(CommunicationProc):
    def __init__(self, ip, port):
        super().__init__(ip, port)

    def run(self):
        np_socket = NumpySocket()

        logger.info("starting server, waiting for client")
        np_socket.startServer(self.port)

        for vec in data_vector_gen(vector_size=5):
            logger.info("sending numpy array:")
            logger.info(vec)
            try:
                np_socket.send(vec)
            except ConnectionResetError:
                logging.error("client disconnected")
                break
        logger.info("closing connection")
        try:
            np_socket.close()
        except OSError:
            logging.error("client already disconnected")


if __name__ == '__main__':
    default_ip, default_port = '127.0.0.1', 50066

    ps = VecGenServer(default_ip, default_port)
    pc = AnalyseClient(default_ip, default_port)

    ps.start()
    pc.start()

    pc.join()
    ps.join()
    print("Successes!")
