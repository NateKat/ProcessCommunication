from communication_proc import CommunicationProc
from numpysocket import NumpySocket
import numpy as np
from decorators import timer, ThrottleDecorator
import asyncio
import typing
from logger import create_logger

logger = create_logger()


class VecGenServer(CommunicationProc):
    call_times_in_seconds = ThrottleDecorator

    def __init__(self, ip: str, port: int, noisy: bool = False):
        super().__init__(ip, port)
        self.noisy = noisy
        self.loop: typing.Optional[asyncio.AbstractEventLoop] = None

    def run(self):
        self.np_socket = NumpySocket(self.noisy)
        logger.debug("starting server, waiting for client")
        self.np_socket.startServer(self.ip, self.port)
        self.loop = asyncio.get_event_loop()

        self.loop.create_task(self.np_socket.emulate_noise())
        self.loop.run_until_complete(self.send_data())
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
        gen = np.random.default_rng(seed)
        while True:
            yield gen.normal(size=vector_size)

    async def send_data(self) -> None:
        while True:
            try:
                ret, time = self.execute_times(1000)
                await ret
                logger.debug(f"Send frequency is {1000 / time:.2f}[Hz]")
            except (ConnectionResetError, ConnectionAbortedError):
                logger.error("client disconnected")
                break

    @timer
    async def execute_times(self, iterations: int) -> None:
        for i, vec in enumerate(self.data_vector_gen()):
            await asyncio.sleep(0)  # zero time Preemption
            self.send_vector(vec)
            if i == iterations:
                break

    @call_times_in_seconds(1000, 1)
    def send_vector(self, vector):
        self.np_socket.send(vector)
