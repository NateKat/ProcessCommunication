from communication_proc import CommunicationProc
import numpy as np
from numpysocket import NumpySocket
from decorators import timer, ThrottleDecorator
from time import sleep
import json
import asyncio
from logger import create_logger

logger = create_logger()


class AnalyseClient(CommunicationProc):
    call_times_in_seconds = ThrottleDecorator

    def __init__(self, ip, port, num_of_vectors_k, rows_in_matrix=100):
        super().__init__(ip, port)
        self._receive_rates = []
        self._rows_in_matrix = rows_in_matrix
        self._num_of_vectors_k = num_of_vectors_k
        self._data_dict = self.init_data_dict()

    @property
    def current_freq(self) -> float:
        return self._receive_rates[-1] if self._receive_rates else 0

    def init_data_dict(self) -> dict:
        data = dict()
        data['communication'] = dict.fromkeys(['rates', 'analytics'])
        data['communication']['rates'] = self._receive_rates  # a series of rates of data acquisition [Hz]: list
        data['matrices'] = []  # list of dicts fromkeys(['matrix', 'mean', 'standard deviation'])
        return data

    def run(self) -> None:
        self.np_socket = NumpySocket()
        while True:
            try:
                self.np_socket.start_client(self.ip, self.port)
                logger.debug("connected to server")
                break
            except ConnectionRefusedError:
                logger.warning(f'Connection failed, make sure `server` is running.')
                sleep(1)
                continue

        asyncio.run(self.get_incoming_data())
        try:
            self.np_socket.close()
        except OSError:
            logger.error("server already disconnected")
        self.finalize_and_save_data()

    async def get_incoming_data(self, num_producers: int = 1, num_consumers: int = 4) -> None:
        queue = asyncio.Queue()

        # Fire up producers and consumers
        logger.debug(f"Starting: {num_producers} producers, {num_consumers} consumers")
        producers = [asyncio.create_task(self.producer(queue)) for _ in range(num_producers)]
        consumers = [asyncio.create_task(self.consumer(queue)) for _ in range(num_consumers)]

        await asyncio.gather(*producers)  # wait for the producers to finish
        logger.debug(f"Producers done")
        await queue.join()  # wait for the remaining tasks to be processed

        # Cancel the consumers, which are now idle
        for c in consumers:
            c.cancel()

    @timer
    def get_batch_frames(self, num_of_matrices: int) -> list:
        return [self.get_frames_in_matrix() for _ in range(num_of_matrices)]

    async def producer(self, queue: asyncio.queues.Queue, matrix_batch_size: int = 10) -> None:
        num_of_vectors = self._rows_in_matrix * matrix_batch_size
        for _ in range(self._num_of_vectors_k):
            frames_list, time = self.get_batch_frames(matrix_batch_size)
            self._receive_rates.append(self.np_socket.calculate_frequency(num_of_vectors, time))
            logger.info(f"Receive frequency: {self.current_freq:.2f}[Hz]")
            for matrix in frames_list:
                await queue.put(matrix)

    async def consumer(self, queue: asyncio.queues.Queue) -> None:
        while True:
            token = await queue.get()
            self.save_matrix(token)
            queue.task_done()
            await asyncio.sleep(0.1)

    def finalize_and_save_data(self) -> None:
        keys = ['mean', 'standard deviation']
        values = list(self.matrix_analytics(np.array(self._receive_rates)))
        self._data_dict['communication']['analytics'] = dict(zip(keys, values))
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(self._data_dict, f, ensure_ascii=False, indent=4)

    def receive_vector(self) -> bytearray:
        return self.np_socket.receive_vector_frame(1024)

    def frames_to_matrix(self, l_frames: list) -> np.ndarray:
        return np.vstack([self.np_socket.frame_to_vector(frame) for frame in l_frames])

    def get_frames_in_matrix(self) -> list:
        return [self.receive_vector() for _ in range(self._rows_in_matrix)]

    def matrix_analytics(self, matrix: np.ndarray) -> tuple:
        return np.mean(matrix, axis=0), np.std(matrix, axis=0)

    def save_matrix(self, l_frames: list) -> None:
        matrix = self.frames_to_matrix(l_frames)
        logger.debug(f"matrix received: {matrix}")
        keys = ['matrix', 'mean', 'standard deviation']
        values = [arr.tolist() for arr in [matrix, *self.matrix_analytics(matrix)]]
        self._data_dict['matrices'].append(dict(zip(keys, values)))
