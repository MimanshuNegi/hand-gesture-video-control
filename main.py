import cv2
import mediapipe as mp
import time
from yt_dlp import YoutubeDL
import vlc
import threading

# Function to draw buttons on the frame
def draw_button(frame, text, position, size=(200, 50), bg_color=(255, 255, 255), text_color=(0, 0, 0)):
    cv2.rectangle(frame, position, (position[0] + size[0], position[1] + size[1]), bg_color, -1)
    cv2.putText(frame, text, (position[0] + 10, position[1] + size[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)

# Class for recognizing hand gestures using MediaPipe
class HandGestureRecognition:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.5)
        self.mp_drawing = mp.solutions.drawing_utils
        self.last_gesture = None
        self.last_gesture_time = 0
        self.cooldown_period = 2  # 2 seconds cooldown for gesture recognition
        self.previous_positions = None  # To track positions for swipe gestures

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
                
                # Check for volume up gesture
                elif (landmarks[8].y < landmarks[6].y and  
                      landmarks[12].y < landmarks[10].y and  
                      landmarks[16].y > landmarks[14].y and  
                      landmarks[20].y > landmarks[18].y):
                    gesture = "volume_up"
                
                # Check for volume down gesture
                elif (landmarks[8].y < landmarks[6].y and  
                      landmarks[12].y > landmarks[10].y and  
                      landmarks[16].y > landmarks[14].y and  
                      landmarks[20].y > landmarks[18].y):
                    gesture = "volume_down"

                # Check for swipe gestures
                elif (abs(landmarks[8].x - landmarks[4].x) < 0.05 and
                      abs(landmarks[8].y - landmarks[4].y) < 0.05):
                    if self.previous_positions:
                        if landmarks[8].x < self.previous_positions[8].x:
                            gesture = "ahead"
                        elif landmarks[8].x > self.previous_positions[8].x:
                            gesture = "behind"
                    self.previous_positions = {8: landmarks[8], 4: landmarks[4]} 
                else:
                    self.previous_positions = None

        # Cooldown logic
        current_time = time.time()
        if gesture and (gesture != self.last_gesture or current_time - self.last_gesture_time >= self.cooldown_period):
            self.last_gesture_time = current_time
            self.last_gesture = gesture
            return gesture  # Return the recognized gesture
        return None  # No gesture detected or cooldown limit reached

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
        if gesture == "play" and self.is_paused:
            self.is_paused = False
            print("Gesture: play")
            self.player.play()
        elif gesture == "pause" and not self.is_paused:
            self.is_paused = True
            print("Gesture: pause")
            self.player.pause()
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
                print("Error: Failed to read frame from webcam.")
                break

            # Resize frame for better alignment
            frame = cv2.resize(frame, (1280, 720))

            gesture = self.hand_recognition.detect_gestures(frame)

            # Draw buttons on the frame
            button_height = 50
            button_width = 200
            draw_button(frame, "Play", (100, 10), (button_width, button_height))  # Play button
            draw_button(frame, "Pause", (320, 10), (button_width, button_height))  # Pause button
            draw_button(frame, "Volume Up", (540, 10), (button_width, button_height))  # Volume Up button
            draw_button(frame, "Volume Down", (760, 10), (button_width, button_height))  # Volume Down button
            
            if gesture:
                self.handle_gesture(gesture)

            cv2.imshow('Hand Gesture Video Control', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    video_url = 'https://youtu.be/cPkGC6jjeXM?si=s1QQmaz6orpISU8G'  # Youtube link here

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
