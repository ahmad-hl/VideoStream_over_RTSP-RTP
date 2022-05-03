from util.ivfreader import IVFReader
import numpy as np
from util import yuv2
from util.wrapper import Decoder, VPXFRAMEDATA
import cv2, os, ctypes

class VideoStream:
	def __init__(self, filename):
		self.filename = filename
		VIDEO_DIR = 'videos/ivfvideos_1min/'

		self.reader = IVFReader(VIDEO_DIR + self.filename )
		self.numframes = self.reader.nFrames
		self.frameNum = 0
		self.dec = Decoder()


	def nextFrame(self):
		"""Get next frame."""
		frame_ = self.reader.get_next_frame()
		data = bytearray(frame_.framedata)
		self.frameNum = frame_.nr
		print('-' * 10 + "\nNext Frame (#" + str(frame_.nr) + ") size:" + str(frame_.size) + "\n" + '-' * 10)

		pkt = np.frombuffer(data, dtype=np.uint8)

		# Decode the frame
		vpdata = VPXFRAMEDATA()
		vpdata.buf = pkt.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
		vpdata.len = len(pkt)
		fr = self.dec.decode_frame_to_buf(vpdata.buf, vpdata.len)
		if fr.len > 0:
			ret, frame = yuv2.read(fr.buf, fr.width, fr.height)
			if ret:
				try:
					# cv2.imshow("server frame", frame)
					# cv2.waitKey(1)
					print('')
				except Exception as ex:
					print('Exception : ',ex)
					pass

			self.dec.free_data(fr)

		return data

	def frameNbr(self):
		"""Get frame number."""
		return self.frameNum

