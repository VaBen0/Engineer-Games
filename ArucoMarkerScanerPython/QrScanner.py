import cv2
import imutils
from imutils.video import VideoStream
import time

detector = cv2.QRCodeDetector()

vs = VideoStream(src=5).start() 
time.sleep(2.0) 

try:
    while True:
        frame = vs.read()
        if frame is None:
            print("[WARNING] No frame captured")
            continue

        frame = imutils.resize(frame, width=1000)

        data, bbox, _ = detector.detectAndDecode(frame)

        if data:
            #print(f"QR Code detected: {data}")
            a = data
            if bbox is not None:
                bbox = bbox.astype(int)
                cv2.polylines(frame, [bbox], True, (0, 255, 0), 2)
                cv2.putText(frame, data, (bbox[0][0][0], bbox[0][0][1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow("QR Code Scanner", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    vs.stop()
    cv2.destroyAllWindows()