from communication_proc import CommunicationProc
import numpy as np
from numpysocket import NumpySocket
from decorators import timer, ThrottleDecorator
from time import sleep
import json
from logger import create_logger

logger = create_logger()


class AnalyseClient(CommunicationProc):
    call_times_in_seconds = ThrottleDecorator

    def __init__(self, ip, port, columns_in_matrix=100):
        super().__init__(ip, port)
        self.receive_rates = []
        self.columns_in_matrix = columns_in_matrix
        self.data_dict = self.init_data_dict()

    @property
    def current_freq(self) -> float:
        return self.receive_rates[-1] if self.receive_rates else 0

    def init_data_dict(self) -> dict:
        data = dict()
        data['communication'] = dict.fromkeys(['rates', 'analytics'])
        data['communication']['rates'] = self.receive_rates  # a series of rates of data acquisition [Hz]: list
        data['matrices'] = []  # list of dicts fromkeys(['matrix', 'mean', 'standard deviation'])
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
        self.finalize_and_save_data()

    def finalize_and_save_data(self):
        keys = ['mean', 'standard deviation']
        values = list(self.matrix_analytics(np.array(self.receive_rates)))
        self.data_dict['communication']['analytics'] = dict(zip(keys, values))
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(self.data_dict, f, ensure_ascii=False, indent=4)

    def data_handler(self):
        for i in range(10):
            self.matrix_handler()
        print(f"Receive frequency:{self.current_freq:.2f}[Hz]")

    @call_times_in_seconds(1000, 1)
    def receive_vector(self) -> bytearray:
        return self.np_socket.receive_vector_frame(16)

    @timer
    def accumulate_frames(self, num_of_frames: int) -> list:
        return [self.receive_vector() for _ in range(num_of_frames)]

    def frames_to_matrix(self, l_frames: list) -> np.ndarray:
        return np.vstack([self.np_socket.frame_to_vector(frame) for frame in l_frames])

    def get_matrix(self) -> np.ndarray:
        l_frames, time = self.accumulate_frames(self.columns_in_matrix)
        logger.debug(f"Received {self.columns_in_matrix} vectors in {time}  seconds")
        self.receive_rates.append(self.columns_in_matrix / time)
        matrix = self.frames_to_matrix(l_frames)
        logger.debug(f"matrix received: {matrix}")
        return matrix

    def matrix_analytics(self, matrix: np.ndarray) -> tuple:
        return np.mean(matrix, axis=0), np.std(matrix, axis=0)

    def save_matrix(self, matrix: np.ndarray) -> None:
        keys = ['matrix', 'mean', 'standard deviation']
        values = [arr.tolist() for arr in [matrix, *self.matrix_analytics(matrix)]]
        self.data_dict['matrices'].append(dict(zip(keys, values)))

    def matrix_handler(self) -> None:
        self.save_matrix(self.get_matrix())

