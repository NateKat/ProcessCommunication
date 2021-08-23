from communication_proc import CommunicationProc
from numpysocket import NumpySocket
import numpy as np
from decorators import timer, ThrottleDecorator
from logger import create_logger

logger = create_logger()


class VecGenServer(CommunicationProc):
    call_times_in_seconds = ThrottleDecorator

    def __init__(self, ip: str, port: int, noisy: bool = False):
        super().__init__(ip, port)
        self.noisy = noisy

    def run(self):
        self.np_socket = NumpySocket(self.noisy)
        logger.debug("starting server, waiting for client")
        self.np_socket.startServer(self.ip, self.port)

        self.send_data()
        logger.info("closing connection")
        try:
            self.np_socket.close()
        except OSError:
            logger.error("client already disconnected")

    def data_vector_gen(self, seed=100, vector_size=50):
        """
        Generator of normal (uniform Gaussian distribution) vector
        :param seed: seed for random
        :param vector_size: vector size: (1 x vector_size)
        :return: yields the next vector for each call
        """
        np.random.RandomState(seed)
        while True:
            yield np.random.normal(size=vector_size)

    def send_data(self) -> None:
        while True:
            try:
                _, time = self.execute_times(1000)
                logger.debug(f"Send frequency is {1000 / time:.2f}[Hz]")
            except (ConnectionResetError, ConnectionAbortedError):
                logger.error("client disconnected")
                break

    @timer
    def execute_times(self, iterations: int) -> None:
        for i in range(iterations):
            self.send_vector(self.data_vector_gen().__next__())

    @call_times_in_seconds(1000, 1)
    def send_vector(self, vector):
        self.np_socket.send(vector)
