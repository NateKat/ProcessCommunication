import numpy as np
import multiprocessing as mp
import logging
from numpysocket import NumpySocket
from time import sleep
from decorators import timer, ThrottleDecorator

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

        for i in range(20):
            self.data_handler()
        try:
            self.np_socket.close()
        except OSError:
            logger.error("server already disconnected")

    @timer
    def accumulate_frames(self, num_of_frames: int, frame_list: list) -> list:
        for i in range(num_of_frames):
            frame_list.append(self.np_socket.receive_vector_frame(16))
        return frame_list

    def frames_to_matrix(self, l_frames: list) -> np.ndarray:
        matrix = self.np_socket.frame_to_vector(l_frames[0])
        for i in range(1, len(l_frames)):
            np.vstack((matrix, self.np_socket.frame_to_vector(l_frames[i])))
        return matrix

    def data_handler(self, mat_col=100):  # each matrix should be 100 vectors long
        l_frames, time = self.accumulate_frames(mat_col, [])
        logger.info(f"Received {mat_col} vectors in {time}  seconds")
        matrix = self.frames_to_matrix(l_frames)
        logger.debug("matrix received:")
        logger.debug(matrix)
        mean, std = self.matrix_analytics(matrix)
        return matrix

    def matrix_analytics(self, matrix):
        r1 = np.mean(matrix, axis=0)
        r2 = np.std(matrix, axis=0)
        return r1, r2


class VecGenServer(CommunicationProc):
    call_times_in_seconds = ThrottleDecorator

    def __init__(self, ip, port):
        super().__init__(ip, port)

    def run(self):
        self.np_socket = NumpySocket()
        logger.debug("starting server, waiting for client")
        self.np_socket.startServer(self.ip, self.port)

        for _ in range(10):
            self.send_data()

        logger.info("closing connection")
        try:
            self.np_socket.close()
        except OSError:
            logger.error("client already disconnected")

    def send_data(self):
        while True:
            #logger.debug("sending numpy array:")
            #logger.debug(vec)
            try:
                _, time = self.send_vector(data_vector_gen().__next__())
                logger.info(f"sent 1000 vectors in {time!r}  seconds")
            except (ConnectionResetError, ConnectionAbortedError):
                logger.error("client disconnected")
                break

    @timer
    @call_times_in_seconds(1000, 1)
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
