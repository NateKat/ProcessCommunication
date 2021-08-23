from communication_proc import CommunicationProc
import numpy as np
from numpysocket import NumpySocket
from decorators import timer
from time import sleep
from logger import create_logger

logger = create_logger()


class AnalyseClient(CommunicationProc):
    def __init__(self, ip, port, columns_in_matrix=100):
        super().__init__(ip, port)
        self.receive_rates = []
        self.columns_in_matrix = columns_in_matrix
        self.data_dict = self.init_data_dict()

    @property
    def current_freq(self) -> float:
        return self.columns_in_matrix / float(self.receive_rates[-1]) if self.receive_rates else 0

    def init_data_dict(self) -> dict:
        data = dict()
        data['matrices'] = []  # list of dicts fromkeys(['matrix', 'mean', 'standard deviation'])
        data['communication'] = dict.fromkeys(['rates', 'analytics'])
        data['communication']['rates'] = []  # a series of rates of data acquisition [Hz]
        data['communication']['analytics'] = dict.fromkeys(['mean', 'standard deviation'])
        return data

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

    def data_handler(self):
        for i in range(10):
            self.matrix_handler()
        print(f"Receive frequency:{self.current_freq:.2f}[Hz]")

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

    def get_matrix(self) -> np.ndarray:
        l_frames, time = self.accumulate_frames(self.columns_in_matrix, [])
        logger.debug(f"Received {self.columns_in_matrix} vectors in {time}  seconds")
        self.receive_rates.append(time)
        matrix = self.frames_to_matrix(l_frames)
        logger.debug("matrix received:")
        logger.debug(matrix)
        return matrix

    def matrix_handler(self):
        matrix = self.get_matrix()
        mean, std = self.matrix_analytics(matrix)
        return matrix

    def matrix_analytics(self, matrix):
        r1 = np.mean(matrix, axis=0)
        r2 = np.std(matrix, axis=0)
        return r1, r2
