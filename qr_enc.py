import ctypes
import itertools
import io

import png

N = 10


def resize(l):
    return list(itertools.chain(*(itertools.repeat(x, N) for x in l)))


def encode_string(link):
    qr = ctypes.CDLL('./libqrencode.so')

    qr.QRcode_encodeString.argtypes = (
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int
    )

    class QRcode(ctypes.Structure):
        _fields_ = [
            ("version", ctypes.c_int),
            ("width", ctypes.c_int),
            ("data", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    qr.QRcode_encodeString.restype = ctypes.POINTER(QRcode)
    link = 'aaa'
    data = qr.QRcode_encodeString(ctypes.cast(link, ctypes.c_char_p), 4, 2, 2, 1)
    width = data.contents.width
    res = [
        [0 if data.contents.data[x*width + y] & 1 else 255 for x in range(width)]
    for y in range(width)]
    res = resize(resize(row) for row in res)
    buf = io.BytesIO()
    png.Writer(width*N, width*N, greyscale=True).write(buf, res)
    buf.seek(0)
    return buf

if __name__ == '__main__':

    print(encode_string("abc"))