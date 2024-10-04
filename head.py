import cv2
import numpy as np
import pyfirmata
import socket
import json
import threading
import time
from cvzone.FaceDetectionModule import FaceDetector
from cvzone.HandTrackingModule import HandDetector

# Camera setup
cap = cv2.VideoCapture(0)
ws, hs = 1280, 720
cap.set(3, ws)
cap.set(4, hs)

if not cap.isOpened():
    print("Camera couldn't Access!!!")
    exit()

# Arduino setup
port = "/dev/cu.usbmodemF412FA64031C2"  # Change this to your Arduino port
board = pyfirmata.Arduino(port)
servo_pinX = board.get_pin('d:9:s')  # pin 9 Arduino
servo_pinY = board.get_pin('d:10:s')  # pin 10 Arduino

# Detectors
face_detector = FaceDetector()
hand_detector = HandDetector(detectionCon=0.8, maxHands=1)

# Global variables
servoPos = [90, 60]  # initial servo position
last_data_time = 0
current_state = "HAND_TRACKING"
face_tracking_start_time = 0
last_stable_position = [90, 60]

def map_servo_angle(value, in_min, in_max, out_min, out_max):
    return int(np.interp(value, [in_min, in_max], [out_min, out_max]))

def listen_socket():
    global servoPos, last_data_time, current_state, last_stable_position
    s = socket.socket()
    s.bind(('127.0.0.1', 7892))
    s.listen(1)
    while True:
        conn, addr = s.accept()
        data = conn.recv(1024).decode()
        print(f"Received data: {data}")
        try:
            jsonData = json.loads(data)
            servoX = jsonData.get('servoX', servoPos[0])
            servoY = jsonData.get('servoY', servoPos[1])
            
            servoX = map_servo_angle(servoX, 0, 180, 10, 170)
            servoY = map_servo_angle(servoY, 0, 180, 170, 10)  # 170° is towards the sky
            
            servoPos[0] = servoX
            servoPos[1] = servoY
            
            servo_pinX.write(servoPos[0])
            servo_pinY.write(servoPos[1])
            
            last_data_time = time.time()
            current_state = "EXTERNAL_CONTROL"
            
        except json.JSONDecodeError:
            print("Invalid JSON data received")
        conn.close()

threading.Thread(target=listen_socket, daemon=True).start()

while True:
    success, img = cap.read()
    
    if current_state == "HAND_TRACKING":
        hands, img = hand_detector.findHands(img)
        if hands:
            hand = hands[0]
            fingers = hand_detector.fingersUp(hand)
            if sum(fingers) == 5:  # All fingers are up (open palm)
                current_state = "FACE_TRACKING"
                face_tracking_start_time = time.time()
        
    elif current_state == "FACE_TRACKING":
        img, bboxs = face_detector.findFaces(img, draw=False)
        if bboxs:
            fx, fy = bboxs[0]["center"][0], bboxs[0]["center"][1]
            servoX = map_servo_angle(fx, 0, ws, 170, 10)
            servoY = map_servo_angle(fy, 0, hs, 10, 170)  # 10° is towards the sky for face tracking
            
            servoPos[0] = servoX
            servoPos[1] = servoY
            
            servo_pinX.write(servoPos[0])
            servo_pinY.write(servoPos[1])
            
            cv2.circle(img, (fx, fy), 80, (0, 0, 255), 2)
            cv2.putText(img, "FACE TRACKING", (850, 50), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 3)
        
        if time.time() - face_tracking_start_time > 8:
            current_state = "HAND_TRACKING"
            last_stable_position = servoPos.copy()
        
    elif current_state == "EXTERNAL_CONTROL":
        cv2.putText(img, "EXTERNAL CONTROL", (850, 50), cv2.FONT_HERSHEY_PLAIN, 3, (0, 255, 0), 3)
        if time.time() - last_data_time > 5:
            current_state = "HAND_TRACKING"
            servoPos = last_stable_position.copy()
            servo_pinX.write(servoPos[0])
            servo_pinY.write(servoPos[1])
    
    cv2.putText(img, f'State: {current_state}', (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
    cv2.putText(img, f'Servo X: {int(servoPos[0])} deg', (50, 100), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
    cv2.putText(img, f'Servo Y: {int(servoPos[1])} deg', (50, 150), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)

    cv2.imshow("Image", img)
    cv2.waitKey(1)