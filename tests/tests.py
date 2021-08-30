from generator_server import VecGenServer
from analyse_client import AnalyseClient
from logger import create_logger

logger = create_logger()


class Tests:
    pass


class Performance(Tests):
    def average_round_trip_time(self):
        """Check the average round trip time for single vector"""
        pass

    def min_round_trip_time(self):
        """Check the minimum round trip time for single vector"""
        pass

    def communication_rate_statistics(self):
        """Check the average and standard deviation of a series of data rates"""
        pass


class Functionality(Tests):
    def vecotr_difference(self):
        """Check that vectors are not the same"""
        pass

    def matrix_statistics(self):
        """Check that mean is close to zero for each matrix on the temporal axis.
        Check that standard deviation is close to 1 for each matrix on the temporal axis"""
        pass
