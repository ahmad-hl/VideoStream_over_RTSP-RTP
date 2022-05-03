import sys
from tkinter import Tk
from ClientIVF import Client

if __name__ == "__main__":
	try:
		serverAddr = sys.argv[1]
		serverPort = sys.argv[2]
		rtpPort = sys.argv[3]
		fileName = sys.argv[4]
	except:
		print("[Usage: ClientLauncher.py Server_name Server_port RTP_port Video_file]\n")
		serverAddr = '127.0.0.1'
		serverPort = 1025
		rtpPort = 5008
		fileName = 'res_176_144.ivf'

	root = Tk()
	# Create a new client
	app = Client(root,serverAddr,serverPort,rtpPort,fileName)
	app.master.title("RTPClient")
	root.mainloop()
