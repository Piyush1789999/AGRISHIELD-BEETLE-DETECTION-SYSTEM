import streamlit as st
import cv2
import numpy as np
import requests
import time
import sys

# Safely handle conditional system properties for local vs cloud
winsound = None
if sys.platform == "win32":
    try:
        import winsound
    except ImportError:
        pass

# ==========================================
# CONFIGURATIONS & API DETAILS
# ==========================================
API_KEY = "bEwRar9f5aInZJxMVNUN"
MODEL_ID = "beetle-2kes2/1"
URL = f"https://detect.roboflow.com/{MODEL_ID}"

TELEGRAM_TOKEN = "your_bot_token"
CHAT_ID = "your_chat_id"

st.set_page_config(page_title="AgriShield Live Scanner", layout="centered")

st.title("🪲 AgriShield Beetle Detection System")
st.write("Real-time crop monitoring and risk management.")

confidence_threshold = st.sidebar.slider("Confidence Threshold", 0.1, 1.0, 0.3, 0.05)

def run_detection(image_bytes):
    try:
        r = requests.post(
            URL,
            files={"file": image_bytes},
            params={"api_key": API_KEY, "confidence": confidence_threshold},
            timeout=15
        )
        return r.json().get("predictions", [])
    except Exception as e:
        st.error(f"API Error: {e}")
        return []

def send_alert(beetle_count):
    msg = f"🪲 AGRISHIELD ALERT!\n{beetle_count} beetle(s) detected!\nImmediate crop inspection needed."
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(telegram_url, data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except:
        pass

# UI Selector
input_source = st.radio("Choose Input Source:", ("Webcam Live Scan", "Upload Image File"))

if input_source == "Webcam Live Scan":
    img_file = st.camera_input("Take a snapshot to scan the crop environment")
    
    if img_file is not None:
        bytes_data = img_file.getvalue()
        file_bytes = np.frombuffer(bytes_data, np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        with st.spinner("Analyzing image frames..."):
            predictions = run_detection(bytes_data)
            
        beetle_count = 0
        for p in predictions:
            if p["class"].lower() in ["beetle", "longhorn", "lucanidae"]:
                beetle_count += 1
                x, y, bw, bh = p["x"], p["y"], p["width"], p["height"]
                x1, y1 = int(x - bw / 2), int(y - bh / 2)
                x2, y2 = int(x + bw / 2), int(y + bh / 2)
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 80), 3)
                label = f"{p['class'].upper()} {p['confidence']:.0%}"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 80), 2)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        st.image(frame_rgb, channels="RGB", use_column_width=True)
        
        if beetle_count > 0:
            st.error(f"🚨 ALERT: {beetle_count} Beetle(s) Detected! Sending alerts to farmer.")
            send_alert(beetle_count)
            st.components.v1.html(
                '<audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg" type="audio/ogg"></audio>',
                height=0
            )
        else:
            st.success("✅ Environment Clear: No target pests detected.")

elif input_source == "Upload Image File":
    uploaded_file = st.file_uploader("Choose a crop image...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        bytes_data = uploaded_file.read()
        file_bytes = np.frombuffer(bytes_data, np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        with st.spinner("Processing analysis..."):
            predictions = run_detection(bytes_data)
            
        beetle_count = 0
        for p in predictions:
            if p["class"].lower() in ["beetle", "longhorn", "lucanidae"]:
                beetle_count += 1
                x, y, bw, bh = p["x"], p["y"], p["width"], p["height"]
                x1, y1 = int(x - bw / 2), int(y - bh / 2)
                x2, y2 = int(x + bw / 2), int(y + bh / 2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 80), 3)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        st.image(frame_rgb, channels="RGB", use_column_width=True)
        
        if beetle_count > 0:
            st.error(f"🚨 ALERT: {beetle_count} Beetle(s) Detected!")
            send_alert(beetle_count)
        else:
            st.success("✅ Environment Clear.")
