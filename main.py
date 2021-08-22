from app import run, init
import sys


def main():
    init(sys.argv[1:])
    run()


if __name__ == '__main__':
    main()
