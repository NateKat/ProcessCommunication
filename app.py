from generator_server import VecGenServer
from analyse_client import AnalyseClient
import argparse

parser = argparse.ArgumentParser(description='Two processes will communicate over a socket. (Randomly generated) '
                                             'vectors from the first process will be sent to the second process. These '
                                             '"data" vectors should be accumulated in the second process in a matrix. '
                                             'Some simple statistics will be computed (across the "temporal" dimension)'
                                             '. Results are saved to a file')
parser.add_argument('-n', '--noisy-mode', action='store_true', default=False, help="Vectors are randomly dropped "
                                                                                   "(mimicking packet loss)")
parser.add_argument('-r', '--vectors-to-receive', type=int, default=20, help="Number of vectors to "
                                                                             "accumulate [thousands]")


def run():
    default_ip, default_port = '127.0.0.1', 50066
    args = parser.parse_args()

    ps = VecGenServer(default_ip, default_port, args.noisy_mode)
    pc = AnalyseClient(default_ip, default_port, args.vectors_to_receive)

    ps.start()
    pc.start()

    pc.join()
    ps.join()
    print("Successes!")
