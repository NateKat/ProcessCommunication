import socket
import numpy as np
import asyncio
from io import BytesIO
import time
from logger import create_logger

logger = create_logger()


class NumpySocket:
    def __init__(self, noisy: bool = False):
        self.address = 0
        self.port = 0
        self.client_connection = self.client_address = None
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._noisy = noisy
        self._gen = np.random.default_rng(seed=100)
        self._send_seq = 0
        self._recv_seq = 0
        self._vectors_dropped = 0
        self.data = bytearray()

    def __del__(self) -> None:
        try:
            self.client_connection.shutdown(socket.SHUT_WR)
            self._socket.shutdown(socket.SHUT_WR)
        except (AttributeError, OSError):
            pass
        except Exception as e:
            logger.error("error when deleting socket", e)

        self.close()

    def start_server(self, address: str, port: int) -> None:
        self.address = address
        self.port = port

        self._socket.bind((self.address, self.port))
        self._socket.listen(1)

        logger.debug("waiting for a connection")
        self.client_connection, self.client_address = self._socket.accept()
        logger.debug(f"connected to: {self.client_address[0]}")

    def start_client(self, address: str, port: int) -> None:
        self.address = address
        self.port = port
        try:
            self._socket.connect((self.address, self.port))
            logger.debug(f"Connected to {self.address} on port {self.port}")
        except socket.error as err:
            logger.error(f"Connection to {self.address} on port {self.port} failed")
            raise err

    def close(self) -> None:
        try:
            self.client_connection.close()
        except AttributeError:
            pass
        self.client_connection = self.client_address = None
        self._socket.close()

    def _pack_frame(self, frame: np.ndarray) -> bytearray:
        f = BytesIO()
        np.savez(f, frame=frame)
        packet_size = len(f.getvalue())
        header = f"{packet_size}SEQ{self._send_seq}:"
        header = bytes(header.encode())  # prepend length of array and sequence number

        self._send_seq += 1
        out = bytearray()
        out += header

        f.seek(0)
        out += f.read()
        return out

    def _unpack_frame(self, frame_buffer: bytearray) -> tuple:
        """
        Remove the header bytes from the front of frameBuffer
        leave any remaining bytes in the frameBuffer!
        :param frame_buffer:
        :return: tuple of  1. frame length: int 2. send sequence: int 3. frame: bytearray
        """
        header_str, _, frame_buffer = frame_buffer.partition(b':')
        length_str, _, send_seq = header_str.partition(b'SEQ')
        return int(length_str), int(send_seq), frame_buffer

    async def emulate_noise(self) -> None:
        if not self._noisy:
            return
        while True:
            s = self._gen.uniform(2, 3)
            start = time.perf_counter()
            await asyncio.sleep(s)
            self._send_seq += 1
            await asyncio.sleep(3 - (time.perf_counter() - start))

    def send(self, frame: np.ndarray) -> None:
        if not isinstance(frame, np.ndarray):
            raise TypeError("input frame is not a valid numpy array")

        out = self._pack_frame(frame)

        np_socket = self._socket
        if self.client_connection:
            np_socket = self.client_connection

        try:
            np_socket.sendall(out)
        except BrokenPipeError:
            logger.error("connection broken")
            raise

    def verify_packet_integrity(self, seq: int) -> None:
        if self._recv_seq == seq - 1:
            logger.warning("Dropped vector detected")
            self._vectors_dropped += 1
            self._recv_seq += 1
        elif self._recv_seq != seq:
            logger.error(f"Packet sequence is broken. Expected:{self._recv_seq} got:{seq}, fixing now")
            self._recv_seq = seq
            raise Exception
        self._recv_seq += 1

    def calculate_frequency(self, num_of_vectors: int, time_sec: float) -> float:
        freq = (num_of_vectors + self._vectors_dropped) / time_sec
        self._vectors_dropped = 0
        return freq

    def receive_vector_frame(self, socket_buffer_size: int = 4096) -> bytearray:
        np_socket = self._socket
        if self.client_connection:
            np_socket = self.client_connection

        while len(self.data) < socket_buffer_size:
            self.data += np_socket.recv(socket_buffer_size)

        length, seq, frame_buffer = self._unpack_frame(self.data)

        self.verify_packet_integrity(seq)
        self.data = frame_buffer[length:]

        return frame_buffer[:length]

    def frame_to_vector(self, frame_buffer: bytearray) -> np.ndarray:
        frame = np.load(BytesIO(frame_buffer))['frame']
        logger.debug("frame received")
        return frame
