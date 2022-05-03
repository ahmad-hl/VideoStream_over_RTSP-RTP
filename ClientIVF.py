from tkinter import *
from tkinter import messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
import numpy as np
from RtpPacket import RtpPacket
from util import yuv2
from util.wrapper import Decoder, VPXFRAMEDATA
import cv2, os, ctypes
import shutil

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3

	counter = 0
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.rtpSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.dec = Decoder()
		os.makedirs('videos/recframes', exist_ok=True)

	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=1, column=0, padx=2, pady=2)

		# Create Play button
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)

		# Create Pause button
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)

		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)

		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5)

	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)

	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)
		self.master.destroy() # Close the gui window
		shutil.rmtree('videos/recframes')
		rate = float(self.counter/self.frameNbr)
		print('-'*60 + "\nRTP Packet Loss Rate :" + str(rate) +"\n" + '-'*60)
		sys.exit(0)

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)

	def playMovie(self):
		"""Play button handler."""
		if self.state == self.READY:
			# Create a new thread to listen for RTP packets
			print("Playing Movie")
			threading.Thread(target=self.listenRtp).start()
			self.playEvent = threading.Event()
			self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)

	def listenRtp(self):
		data_out = bytearray()
		while True:
			try:
				data,addr = self.rtpSocket.recvfrom(1600)

				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					print("||Received Rtp Packet #" + str(rtpPacket.seqNum()) + "|| ")
					currFrameNbr = rtpPacket.seqNum()

					if currFrameNbr > self.frameNbr:  # Discard the late packet
						print("[[Received Frame #" + str(self.frameNbr) + "]] ")
						print('-' * 60)
						frame = self.vp8decode_frame(data_out)
						cur_dir = os.getcwd()
						recframesDir = os.path.join(cur_dir, 'videos/recframes')
						cv2.imwrite(recframesDir + '/' + str(self.frameNbr ) + '.jpg', frame,
									[cv2.IMWRITE_JPEG_QUALITY, 100])
						self.updateMovie(recframesDir + '/' + str(self.frameNbr ) + '.jpg')
						data_out = bytearray()
						data_out.extend(rtpPacket.getPayload())
						self.frameNbr = currFrameNbr
					else:
						data_out.extend(rtpPacket.getPayload())

			except Exception as ex:
				# Stop listening upon requesting PAUSE or TEARDOWN
				print("Didn`t receive data! ", ex )
				if self.playEvent.isSet():
					break

				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break
	def vp8decode_frame(self, rtpPayload):
		pkt = np.frombuffer(rtpPayload, dtype=np.uint8)
		# Decode the frame
		vpdata = VPXFRAMEDATA()
		vpdata.buf = pkt.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
		vpdata.len = len(pkt)
		fr = self.dec.decode_frame_to_buf(vpdata.buf, vpdata.len)
		if fr.len > 0:
			ret, frame = yuv2.read(fr.buf, fr.width, fr.height)
			if ret:
				return frame
			self.dec.free_data(fr)

		return None

	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		try:
			photo = ImageTk.PhotoImage(Image.open(imageFile)) #stuck here !!!!!!
		except:
			print("photo error")
			print('-'*60)
			traceback.print_exc(file=sys.stdout)
			print('-'*60)

		self.label.configure(image = photo, height=720)
		self.label.image = photo

	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)

	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""

		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			threading.Thread(target=self.recvRtspReply).start()
			# Update RTSP sequence number.
			self.rtspSeq = 1

			# Write the RTSP request to be sent.
			request = "SETUP " + str(self.fileName) + "\n" + str(self.rtspSeq) + "\n" + " RTSP/1.0 RTP/UDP " + str(self.rtpPort)

			self.rtspSocket.send(request.encode('utf-8'))
			# Keep track of the sent request.
			self.requestSent = self.SETUP

		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update RTSP sequence number.
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			request = "PLAY " + "\n" + str(self.rtspSeq)

			self.rtspSocket.send(request.encode('utf-8'))
			print('-'*60 + "\nPLAY request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			self.requestSent = self.PLAY

		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP sequence number.
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			request = "PAUSE " + "\n" + str(self.rtspSeq)
			self.rtspSocket.send(request.encode('utf-8'))
			print('-'*60 + "\nPAUSE request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			self.requestSent = self.PAUSE

		# Resume request


		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update RTSP sequence number.
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			request = "TEARDOWN " + "\n" + str(self.rtspSeq)
			self.rtspSocket.send(request.encode('utf-8'))
			print('-'*60 + "\nTEARDOWN request sent to Server...\n" + '-'*60)
			# Keep track of the sent request.
			self.requestSent = self.TEARDOWN

		else:
			return


	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)

			if reply:
				self.parseRtspReply(reply)

			# Close the RTSP socket upon requesting Teardown
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break

	def parseRtspReply(self, data):
		print("Parsing Received Rtsp data...")

		"""Parse the RTSP reply from the server."""
		lines = data.decode('utf-8').split('\n')
		seqNum = int(lines[1].split(' ')[1])

		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session

			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200:
					if self.requestSent == self.SETUP:
						# Update RTSP state.
						print("Updating RTSP state...")
						# self.state = ...
						self.state = self.READY
						# Open RTP port.
						print("Setting Up RtpPort for Video Stream")
						self.openRtpPort()

					elif self.requestSent == self.PLAY:
						 self.state = self.PLAYING
						 print('-'*60 + "\nClient is PLAYING...\n" + '-'*60)
					elif self.requestSent == self.PAUSE:
						 self.state = self.READY

						# The play thread exits. A new thread is created on resume.
						 self.playEvent.set()

					elif self.requestSent == self.TEARDOWN:
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1

	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""

		# Create a new datagram socket to receive RTP packets from the server
		# self.rtpSocket = ...

		# Set the timeout value of the socket to 0.5sec
		self.rtpSocket.settimeout(0.5)
		try:
			#self.rtpSocket.connect(self.serverAddr,self.rtpPort)
			self.rtpSocket.bind((self.serverAddr,self.rtpPort))   # WATCH OUT THE ADDRESS FORMAT!!!!!  rtpPort# should be bigger than 1024
			#self.rtpSocket.listen(5)
			print("Bind RtpPort Success")

		except:
			messagebox.showwarning('Connection Failed', 'Connection to rtpServer failed...')


	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		self.pauseMovie()
		if messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
		else: # When the user presses cancel, resume playing.
			#self.playMovie()
			print("Playing Movie")
			threading.Thread(target=self.listenRtp).start()
			#self.playEvent = threading.Event()
			#self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)
