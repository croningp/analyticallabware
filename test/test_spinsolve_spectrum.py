import os
import struct
import time
import numpy as np

from memory_profiler import profile

HERE = os.path.abspath(os.path.dirname(__file__))
NMR_FOLDER = os.path.join(HERE, '163122-1D PROTON-Unknown')
NMR_FILE = os.path.join(NMR_FOLDER, 'data.1d')

fp = open('mem_profiler.log', 'w+')

@profile(precision=4, stream=fp)
def load_as_arrays():
    start_time = time.time()
    # read first eight bytes
    spectrum = []
    # unpack the data
    with open(NMR_FILE, 'rb') as fileobj:
        data = fileobj.read(4)
        while data:
            spectrum.extend(struct.unpack('<f', data))
            data = fileobj.read(4)
    end_data_time = time.time()
    # discard first 8 points and split data in 3 pieces
    fid = np.array(spectrum[len(spectrum[8:]) // 3 + 8:])
    # odd numbers - real part, even numbers - imaginary
    fid_complex = fid[::2] + fid[1::2] * -1j
    end_time = time.time()
    print('List extension data reading: ', end_data_time-start_time)
    print('Array creation: ', end_time-end_data_time)
    return fid_complex

@profile(precision=4, stream=fp)
def load_as_lists():
    # read first eight bytes
    spectrum = []
    # unpack the data
    with open(NMR_FILE, 'rb') as fileobj:
        data = fileobj.read(4)
        while data:
            spectrum.extend(struct.unpack('<f', data))
            data = fileobj.read(4)
    start_time = time.time()
    # discard first 8 points and split data in 3 pieces
    fid = spectrum[len(spectrum[8:]) // 3 + 8:]
    # fid_real = fid[::2]
    # fid_img = fid[1::2]
    fid_complex = []
    # for real, img in zip(fid_real, fid_img):
    for real, img in zip(fid[::2], fid[1::2]):
        fid_complex.append(complex(real, img))
    end_time = time.time()
    print('List creation: ', end_time-start_time)
    return fid_complex

@profile(precision=4, stream=fp)
def array_fromfile():
    start_time = time.time()
    spectrum = np.fromfile(NMR_FILE, dtype='<f')
    end_time = time.time()
    fid = spectrum[len(spectrum[8:]) // 3 + 8:]
    fid_complex = fid[::2] + fid[1::2] * 1j
    print('Reading array from file: ', end_time-start_time)
    return fid_complex

if __name__ == '__main__':
    load_as_arrays()
    load_as_lists()
    array_fromfile()
