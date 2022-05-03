from util.ivfreader import IVFReader
import numpy as np
import cv2, os, ctypes
from util import yuv2
from util.wrapper import Decoder, VPXFRAMEDATA

VIDEO_DIR = '../videos/ivfvideos_1min/'
FRAMES_DIR = '../videos/recframes/'

reader_176_144 = IVFReader(VIDEO_DIR+'/res_176_144.ivf')
reader_352_288 = IVFReader(VIDEO_DIR+'/res_352_288.ivf')
reader_480_270 = IVFReader(VIDEO_DIR+'/res_480_270.ivf')
reader_504_376 = IVFReader(VIDEO_DIR+'/res_504_376.ivf')
reader_640_360 = IVFReader(VIDEO_DIR+'/res_640_360.ivf')
reader_854_480 = IVFReader(VIDEO_DIR+'/res_854_480.ivf')
reader_960_540 = IVFReader(VIDEO_DIR+'/res_960_540.ivf')
reader_1280_720 = IVFReader(VIDEO_DIR+'/res_1280_720.ivf')
reader_1920_1080 = IVFReader(VIDEO_DIR+'/res_1920_1080.ivf')

print([reader_176_144.nFrames, reader_352_288.nFrames, reader_504_376.nFrames, reader_640_360.nFrames, reader_854_480.nFrames, reader_960_540.nFrames, reader_1280_720.nFrames, reader_1920_1080.nFrames])
reader = IVFReader(VIDEO_DIR+'/res_1920_1080.ivf')
numframes = reader.nFrames
# reader.print_header()

dec = Decoder()

frame_no=0
while frame_no< numframes:
    frame = reader.get_next_frame()
    print([frame.nr,frame.size,frame.ts])
    data_in = bytearray(frame.framedata)
    pkt  = np.frombuffer(data_in, dtype=np.uint8)

    # Decode the frame
    vpdata = VPXFRAMEDATA()
    vpdata.buf = pkt.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
    vpdata.len = len(pkt)
    fr = dec.decode_frame_to_buf(vpdata.buf, vpdata.len)
    if fr.len > 0:
        ret, frame = yuv2.read(fr.buf, fr.width, fr.height)
        if ret:
            try:
                cur_dir = os.getcwd()
                recframesDir = os.path.join(cur_dir, FRAMES_DIR)
                cv2.imwrite(recframesDir + '/' + str(frame_no) + '.jpg', frame,
                             [cv2.IMWRITE_JPEG_QUALITY, 100])
                cv2.imshow("frame", frame)
                cv2.waitKey(1)
            except:
                pass

        dec.free_data(fr)

    frame_no += 1
