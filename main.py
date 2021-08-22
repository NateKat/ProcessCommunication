from app import run, init
import sys
import logging


def main():
    init(sys.argv[1:])
    run()


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    main()
