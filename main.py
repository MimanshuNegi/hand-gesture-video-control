import cv2
import mediapipe as mp
import threading
from yt_dlp import YoutubeDL
import vlc

# Class for recognizing hand gestures using MediaPipe
class HandGestureRecognition:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.5)
        self.mp_drawing = mp.solutions.drawing_utils
        self.previous_positions = None  # To track previous positions of landmarks for swipe gestures

    # Detect gestures from the frame
    def detect_gestures(self, frame):
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(image)
        gesture = None

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                landmarks = hand_landmarks.landmark
                
                # Check for play gesture (all fingers up)
                if all(landmarks[i].y < landmarks[i - 2].y for i in [8, 12, 16, 20]):  
                    gesture = "play"
                
                # Check for pause gesture (all fingers down)
                elif all(landmarks[i].y > landmarks[i - 2].y for i in [8, 12, 16, 20]): 
                    gesture = "pause"
                
                # Check for volume up gesture (index and middle finger up, ring and pinky down)
                elif (landmarks[8].y < landmarks[6].y and  
                      landmarks[12].y < landmarks[10].y and  
                      landmarks[16].y > landmarks[14].y and  
                      landmarks[20].y > landmarks[18].y):  
                    gesture = "volume_up"
                
                # Check for volume down gesture (index finger up, middle, ring, and pinky down)
                elif (landmarks[8].y < landmarks[6].y and  
                      landmarks[12].y > landmarks[10].y and  
                      landmarks[16].y > landmarks[14].y and  
                      landmarks[20].y > landmarks[18].y):  
                    gesture = "volume_down"
                
                # Check for swipe gestures (index finger and thumb joined)
                elif (abs(landmarks[8].x - landmarks[4].x) < 0.05 and
                      abs(landmarks[8].y - landmarks[4].y) < 0.05):
                    if self.previous_positions:
                        if landmarks[8].x < self.previous_positions[8].x:  # Move video forward 
                            gesture = "ahead"
                        elif landmarks[8].x > self.previous_positions[8].x: # Move video backward
                            gesture = "behind"
                    self.previous_positions = {8: landmarks[8], 4: landmarks[4]} 
                else:
                    self.previous_positions = None  # Reset the gesture

        return frame, gesture

# Class to handle video playback and gesture controls
class VideoPlayer:
    def __init__(self, video_url):
        self.video_url = video_url
        self.hand_recognition = HandGestureRecognition()
        self.is_paused = False

        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        media = self.instance.media_new(video_url)
        self.player.set_media(media)
        self.player.play()

    # Handle gestures and control video accordingly
    def handle_gesture(self, gesture):
        if gesture == "pause" and not self.is_paused:
            self.is_paused = True
            print("Gesture: pause")
            self.player.pause()
        elif gesture == "play" and self.is_paused:
            self.is_paused = False
            print("Gesture: play")
            self.player.play()
        elif gesture == "volume_up":
            print("Gesture: Volume Up")
            volume = self.player.audio_get_volume()
            self.player.audio_set_volume(min(volume + 10, 100))
        elif gesture == "volume_down":
            print("Gesture: Volume Down")
            volume = self.player.audio_get_volume()
            self.player.audio_set_volume(max(volume - 10, 0))
        elif gesture == "ahead":
            print("Gesture: Move Ahead")
            self.player.set_time(self.player.get_time() + 10000)  # Skip ahead by 10 seconds
        elif gesture == "behind":
            print("Gesture: Move Behind")
            self.player.set_time(self.player.get_time() - 10000)  # Skip back by 10 seconds

    # Capture video from the webcam and detect gestures
    def detect_gestures(self):
        cap = cv2.VideoCapture(0)  # Use the first webcam

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame, gesture = self.hand_recognition.detect_gestures(frame)
            cv2.imshow('Hand Gesture Recognition', frame)
            self.handle_gesture(gesture)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    video_url = 'https://youtu.be/cPkGC6jjeXM?si=s1QQmaz6orpISU8G'   # Youtube link here

    # Download the best format of the video
    ydl_opts = {'format': 'best'}
    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=False)
        video_url = info_dict['url']
    
    player = VideoPlayer(video_url)
    
    # Threading to use multiple processes simultaneously
    gesture_thread = threading.Thread(target=player.detect_gestures)
    gesture_thread.start()
    gesture_thread.join()
