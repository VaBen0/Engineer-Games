# import the necessary packages
from imutils.video import VideoStream
import imutils
import time
import cv2

# define names of each possible ArUco tag OpenCV supports
ARUCO_DICT = cv2.aruco.DICT_4X4_50
# load the ArUCo dictionary and grab the ArUCo parameters
arucoDict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_50)
arucoParams=cv2.aruco.DetectorParameters()
# initialize the video stream and allow the camera sensor to warm up
print("[INFO] starting video stream...")
#vs = VideoStream(src=0).start()
vs = VideoStream("http://192.168.4.1:81/stream").start()
#vs = VideoStream(src=0).start() 
time.sleep(2.0)
old_ids=[0,0]
i=0
# loop over the frames from the video stream
while True:
	# grab the frame from the threaded video stream 
	frame = vs.read()
	if frame is None:
		continue
	frame = imutils.resize(frame, width=1000)

	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
	gray_enhanced = clahe.apply(gray)
	gray_filtered = cv2.medianBlur(gray_enhanced, 3)
	# detect ArUco markers in the input frame
	(corners, ids, rejected) = cv2.aruco.detectMarkers(gray_filtered, arucoDict, parameters=arucoParams)

	# verify *at least* one ArUco marker was detected
	if len(corners) > 0:
		# flatten the ArUco IDs list
		ids = ids.flatten()
		i+=1
		if i==10:
			i=0
			# loop over the detected ArUCo corners
			for (markerCorner, markerID) in zip(corners, ids):
				# extract the marker corners (which are always returned
				# in top-left, top-right, bottom-right, and bottom-left
				# order)
				corners = markerCorner.reshape((4, 2))
				(topLeft, topRight, bottomRight, bottomLeft) = corners
	
				# convert each of the (x, y)-coordinate pairs to integers
				topRight = (int(topRight[0]), int(topRight[1]))
				bottomRight = (int(bottomRight[0]), int(bottomRight[1]))
				bottomLeft = (int(bottomLeft[0]), int(bottomLeft[1]))
				topLeft = (int(topLeft[0]), int(topLeft[1]))
	
				# draw the bounding box of the ArUCo detection
				cv2.line(frame, topLeft, topRight, (0, 255, 0), 2)
				cv2.line(frame, topRight, bottomRight, (0, 255, 0), 2)
				cv2.line(frame, bottomRight, bottomLeft, (0, 255, 0), 2)
				cv2.line(frame, bottomLeft, topLeft, (0, 255, 0), 2)
	
				# compute and draw the center (x, y)-coordinates of the
				# ArUco marker
				cX = int((topLeft[0] + bottomRight[0]) / 2.0)
				cY = int((topLeft[1] + bottomRight[1]) / 2.0)
				cv2.circle(frame, (cX, cY), 4, (0, 0, 255), -1)
	
				#draw the ArUco marker ID on the frame
				cv2.putText(frame, str(markerID),
					(topLeft[0], topLeft[1] - 15),
					cv2.FONT_HERSHEY_SIMPLEX,
					0.5, (0, 255, 0), 2)
		if (old_ids[0]!=ids[0]):
			print(ids)
			old_ids=ids
	# show the output frame
	cv2.imshow("ArUco detector", frame)
	key = cv2.waitKey(1) & 0xFF

	# if the 'space' key was pressed, break from the loop
	if key == ord(" "):
		break
# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()