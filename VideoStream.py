import struct
class VideoStream:
	def __init__(self, filename):
		self.filename = filename
		try:
			self.file = open(filename, 'rb')
			print('-'*60 +  "\nVideo file : |" + filename +  "| read\n" + '-'*60)
		except:
			print("read " + filename + " error")
			raise IOError
		self.frameNum = 0

	def nextFrame(self):
		"""Get next frame."""
		data = self.file.read(5)  # Get the framelength from the first 5 bits
		if data:
			framelength = int(data)

			# Read the current frame
			data = self.file.read(framelength)

			self.frameNum += 1
			print('-' * 10 + "\nNext Frame (#" + str(self.frameNum) + ") length:" + str(framelength) + "\n" + '-' * 10)

		return data

	def frameNbr(self):
		"""Get frame number."""
		return self.frameNum

