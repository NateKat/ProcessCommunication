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


class CommunicationProc(mp.Process):
    def __init__(self, ip='127.0.0.1', port=12345):
        super().__init__()
        self.ip = ip
        self.port = port


class AnalyseClient(CommunicationProc):
    def __init__(self, ip, port):
        super().__init__(ip, port)

    def run(self):
        print("client sent 1")
        client_socket = socket.socket()

        client_socket.connect((self.ip, self.port))

        # receive data from the server
        while True:
            data = client_socket.recv(1024)
            if data:
                print(data)
            else:
                break
        # close the connection
        client_socket.close()
        print("client sent 2")


class VecGenServer(CommunicationProc):
    def __init__(self, ip, port):
        super().__init__(ip, port)

    def run(self):
        #  server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket = socket.socket()
        server_socket.bind((self.ip, self.port))
        server_socket.listen(1)  # one connection allowed

        logger.debug("Server listening")
        print("Server listening!")

        c, address = server_socket.accept()
        logger.debug("{u} connected".format(u=address))
        c.send('OK'.encode())
        c.close()


if __name__ == '__main__':
    default_ip, default_port = '127.0.0.1', 50066

    ps = VecGenServer(default_ip, default_port)
    pc = AnalyseClient(default_ip, default_port)

    ps.start()
    pc.start()

    pc.join()
    ps.join()
    print("Successes!")
