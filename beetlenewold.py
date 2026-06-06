import cv2
import numpy as np
import requests
import time
import os
import sys
import serial
import winsound
import threading 

# ==========================================
# CONFIGURATIONS & API DETAILS
# ==========================================
API_KEY = "bEwRar9f5aInZJxMVNUN"
MODEL_ID = "beetle-2kes2/1"
URL = f"https://detect.roboflow.com/{MODEL_ID}"

TELEGRAM_TOKEN = "your_bot_token"
CHAT_ID = "your_chat_id"

last_alert_time = 0
ALERT_COOLDOWN = 30

# ==========================================
# ARDUINO SERIAL INITIALIZATION
# ==========================================
arduino = None
try:
    arduino = serial.Serial('COM12', 9600, timeout=1)
    time.sleep(2)  # Allow time for Arduino to initialize
    print(">>> Arduino connected successfully!")
except Exception as e:
    print(f">>> Arduino not connected: {e}")


def play_alarm_tone():
    try:
        winsound.Beep(2200, 3500)
    except Exception as e:
        print("\a")
def trigger_hardware_audio_signal():
    threading.Thread(target=play_alarm_tone, daemon=True).start()


def send_alert(beetle_count):
    msg = f"🪲 AGRISHIELD ALERT!\n{beetle_count} beetle(s) detected!\nImmediate crop inspection needed."
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except:
        pass

def run_detection(image):
    _, img_encoded = cv2.imencode('.jpg', image)
    try:
        r = requests.post(
            URL,
            files={"file": img_encoded.tobytes()},
            params={"api_key": API_KEY, "confidence": 0.3},
            timeout=15
        )
        data = r.json()
        return data.get("predictions", [])
    except Exception as e:
        print("API Error:", e)
        return []

def draw_ui(display, w, h, beetle_count, frame_count, fps):
    top_overlay = display.copy()
    cv2.rectangle(top_overlay, (0, 0), (w, 90), (10, 10, 10), -1)
    cv2.addWeighted(top_overlay, 0.75, display, 0.25, 0, display)
    cv2.line(display, (0, 90), (w, 90), (0, 220, 100), 2)

    cv2.putText(display, "AGRI", (18, 65),
                cv2.FONT_HERSHEY_DUPLEX, 1.8, (0, 220, 100), 3)
    cv2.putText(display, "SHIELD", (130, 65),
                cv2.FONT_HERSHEY_DUPLEX, 1.8, (255, 255, 255), 3)

    if fps > 0:
        cv2.putText(display, f"FPS: {fps:.0f}", (w - 120, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 200, 255), 2)
    cv2.putText(display, f"Frame: {frame_count}", (w - 120, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (120, 120, 120), 1)

    bot_overlay = display.copy()
    if beetle_count > 0:
        cv2.rectangle(bot_overlay, (0, h - 80), (w, h), (0, 0, 160), -1)
        cv2.addWeighted(bot_overlay, 0.8, display, 0.2, 0, display)
        cv2.line(display, (0, h - 80), (w, h - 80), (0, 0, 255), 2)
        cv2.putText(display, "!! BEETLE ALERT - CROP DAMAGE RISK !!", (18, h - 45),
                    cv2.FONT_HERSHEY_DUPLEX, 0.78, (0, 60, 255), 2)
        cv2.putText(display, f"  {beetle_count} beetle(s) detected  |  Sending farmer alert...", (18, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
    else:
        cv2.rectangle(bot_overlay, (0, h - 80), (w, h), (10, 30, 10), -1)
        cv2.addWeighted(bot_overlay, 0.75, display, 0.25, 0, display)
        cv2.line(display, (0, h - 80), (w, h - 80), (0, 220, 100), 2)
        cv2.putText(display, "ALL CLEAR  -  No beetles detected", (18, h - 45),
                    cv2.FONT_HERSHEY_DUPLEX, 0.78, (0, 220, 100), 2)
        cv2.putText(display, "  Monitoring active...", (18, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (120, 120, 120), 1)

    badge_color = (0, 0, 200) if beetle_count > 0 else (0, 150, 60)
    cv2.rectangle(display, (w - 160, h - 78), (w, h - 1), badge_color, -1)
    cv2.putText(display, f"{beetle_count}", (w - 120, h - 28),
                cv2.FONT_HERSHEY_DUPLEX, 1.8, (255, 255, 255), 3)
    cv2.putText(display, "BEETLES", (w - 138, h - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)

    return display

def draw_detections(display, predictions, scale_x=1.0, scale_y=1.0):
    beetle_count = 0
    for p in predictions:
        x = p["x"] * scale_x
        y = p["y"] * scale_y
        bw = p["width"] * scale_x
        bh = p["height"] * scale_y

        x1 = int(x - bw / 2)
        y1 = int(y - bh / 2)
        x2 = int(x + bw / 2)
        y2 = int(y + bh / 2)

        cv2.rectangle(display, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), (0, 180, 60), 1)
        cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 80), 3)

        corner = 15
        thick = 3
        col = (0, 255, 80)
        cv2.line(display, (x1, y1), (x1 + corner, y1), col, thick)
        cv2.line(display, (x1, y1), (x1, y1 + corner), col, thick)
        cv2.line(display, (x2, y1), (x2 - corner, y1), col, thick)
        cv2.line(display, (x2, y1), (x2, y1 + corner), col, thick)
        cv2.line(display, (x1, y2), (x1 + corner, y2), col, thick)
        cv2.line(display, (x1, y2), (x1, y2 - corner), col, thick)
        cv2.line(display, (x2, y2), (x2 - corner, y2), col, thick)
        cv2.line(display, (x2, y2), (x2, y2 - corner), col, thick)

        label = f"{p['class'].upper()}  {p['confidence']:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        cv2.rectangle(display, (x1, y1 - th - 10), (x1 + tw + 12, y1), (0, 200, 60), -1)
        cv2.putText(display, label, (x1 + 6, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)

        if p["class"].lower() in ["beetle", "longhorn", "lucanidae"]:
            beetle_count += 1

    return display, beetle_count


def show_menu():
    print("\n")
    print("=" * 45)
    print("        AGRISHIELD - Beetle Detection")
    print("=" * 45)
    print("  [1]  Webcam / USB Camera (live feed)")
    print("  [2]  Upload Image (scan a photo)")
    print("  [3]  Stream URL (IP cam / Pi camera)")
    print("=" * 45)
    while True:
        choice = input("  Choose option (1/2/3): ").strip()
        if choice in ["1", "2", "3"]:
            return choice
        print("  Invalid. Enter 1, 2 or 3.")


def find_camera():
    for index in [0, 1, 2]:
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                print(f"Camera found at index {index}")
                return cap
        cap.release()
    return None


def camera_mode(cap):
    print("Live mode started. Press Q to quit.")

    frame_count = 0
    last_predictions = []
    prev_time = time.time()
    global last_alert_time

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera feed lost.")
            break

        if frame_count % 15 == 0:
            small = cv2.resize(frame, (640, 480))
            last_predictions = run_detection(small)
            print(f"Detected {len(last_predictions)} objects")

        display = frame.copy()
        h, w = frame.shape[:2]
        scale_x = w / 640.0
        scale_y = h / 480.0

        display, beetle_count = draw_detections(display, last_predictions, scale_x, scale_y)

        # ----------------------------------------------------
        # BUZZER INTERACTION HANDLING
        # ----------------------------------------------------
        if beetle_count > 0:
            if arduino:
                try:
                    arduino.write(b'1')
                except:
                    pass
            trigger_hardware_audio_signal()
        else:
            if arduino:
                try:
                    arduino.write(b'0')
                except:
                    pass

        if beetle_count > 0:
            now = time.time()
            if now - last_alert_time > ALERT_COOLDOWN:
                send_alert(beetle_count)
                last_alert_time = now

        curr_time = time.time()
        fps = 1 / (curr_time - prev_time + 0.001)
        prev_time = curr_time

        display = draw_ui(display, w, h, beetle_count, frame_count, fps)
        cv2.imshow("AgriShield", display)
        frame_count += 1

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


def image_mode():
    print("\n AGRISHIELD - Image Mode")
    print("Drag and drop an image into the terminal!")

    while True:
        path = input("\nEnter image path (or Q to quit): ").strip().strip('"')

        if path.lower() == 'q':
            break

        if not os.path.exists(path):
            print("File not found. Try again.")
            continue

        frame = cv2.imread(path)
        if frame is None:
            print("Could not read image. Use JPG or PNG.")
            continue

        print("Running beetle detection...")
        h, w = frame.shape[:2]

        small = cv2.resize(frame, (640, 480))
        predictions = run_detection(small)
        scale_x = w / 640.0
        scale_y = h / 480.0

        print(f"Detected {len(predictions)} object(s)")

        display = frame.copy()
        display, beetle_count = draw_detections(display, predictions, scale_x, scale_y)
        display = draw_ui(display, w, h, beetle_count, 1, 0)

        # ----------------------------------------------------
        # BUZZER IMAGE SCAN INTERACTION
        # ----------------------------------------------------
        if beetle_count > 0:
            if arduino:
                try:
                    arduino.write(b'1')
                except:
                    pass
            print(f"ALERT! {beetle_count} beetle(s) found!")
            send_alert(beetle_count)
            trigger_hardware_audio_signal()
        else:
            if arduino:
                try:
                    arduino.write(b'0')
                except:
                    pass
            print("All clear - no beetles detected")

        cv2.imshow("AgriShield - Image Mode", display)
        print("Press any key to scan another image, or Q to quit.")

        key = cv2.waitKey(0) & 0xFF
        if key == ord('q'):
            break

    cv2.destroyAllWindows()


def stream_mode():
    print("\n AGRISHIELD - Stream Mode")
    print("Examples:")
    print("  IP Webcam app (Android): http://192.168.x.x:8080/video")
    print("  Pi camera stream:        http://192.168.x.x:5000/stream")
    print("  RTSP camera:             rtsp://username:password@192.168.x.x/stream")

    url = input("\nEnter stream URL: ").strip()

    print("Connecting to stream...")
    cap = cv2.VideoCapture(url)

    if not cap.isOpened():
        print("Could not connect to stream. Check the URL and try again.")
        return

    print("Stream connected! Press Q to quit.")
    camera_mode(cap)


if __name__ == "__main__":
    choice = show_menu()

    if choice == "1":
        cap = find_camera()
        if cap is not None:
            camera_mode(cap)
        else:
            print("No camera found. Switching to image mode.")
            image_mode()

    elif choice == "2":
        image_mode()

    elif choice == "3":
        stream_mode()