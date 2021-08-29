# Process Communication
### About
Two processes will communicate over a socket. (Randomly generated) vectors from the first process will be sent to the second process. These "data" vectors should be accumulated in the second process in a matrix. Some simple statistics will be computed (across the "temporal" dimension). Results are saved to a file

## Installation
### venv (optional)
Run:
```
$ python -m venv .venv
$ source .venv/bin/activate
```

### Install
From within this git repo, run:
```
$ pip install -r requirements.txt
```

### Instructions how to run
```
usage: main.py [-h] [-n] [-r VECTORS_TO_RECEIVE]
```

optional arguments:

  -h, --help            show this help message and exit

  -n, --noisy-mode      Vectors are randomly dropped (mimicking packet loss)

  -r VECTORS_TO_RECEIVE, --vectors-to-receive VECTORS_TO_RECEIVE:
                        Number of vectors to accumulate, (default 20) [thousands]

### Design and performance notes
1. Communication rate is close to 1000[Hz] but not accurate enough to spot a dropped vector by calculating the rate on the receiving side. One of the steps taken to optimize the communication rate was adding a Producer - Consumer pattern to split the accumulation and processing of the data.
2. Noise detection is implemented by adding packet sequence number in each header, thus allowing the receiving side to detect missing packets and also to adjust rate calculation accordingly.
3. NumpySocket class is based on  [Numpy Socket package v0.2.0](https://github.com/sabjorn/NumpySocket) originally written by [@sabjorn](https://github.com/sabjorn/). Changes include a modified header, frequency and noise detection, typing deceleration and changed styling
