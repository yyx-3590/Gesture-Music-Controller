import cv2
import mediapipe as mp
import math
import pygame

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

pygame.mixer.init()
pygame.mixer.music.load("music.mp3")

is_playing = False
has_started = False
current_volume = 0.5

FINGER_JOINTS = {
    "index": (8, 6),
    "middle": (12, 10),
    "ring": (16, 14),
    "pinky": (20, 18),
}

INDEX_TIP = 8

VOLUME_ZONE_TOP = 0.15
VOLUME_ZONE_BOTTOM = 0.85

PERSISTENCE_FRAMES = 4

mode = "IDLE"
enter_counter = 0
exit_counter = 0

# Whether to show the on-screen instruction legend
# 是否显示屏幕上的操作指南面板
show_legend = True


def distance(p1, p2):
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def is_finger_up(hand_landmarks, tip_id, pip_id):
    wrist = hand_landmarks.landmark[0]
    tip = hand_landmarks.landmark[tip_id]
    pip = hand_landmarks.landmark[pip_id]
    return distance(wrist, tip) > distance(wrist, pip)


def get_hand_bounding_box(hand_landmarks, frame_width, frame_height):
    x_coords = [lm.x * frame_width for lm in hand_landmarks.landmark]
    y_coords = [lm.y * frame_height for lm in hand_landmarks.landmark]
    return min(x_coords), min(y_coords), max(x_coords), max(y_coords)


def calculate_volume_from_position(index_y):
    ratio = (index_y - VOLUME_ZONE_TOP) / (VOLUME_ZONE_BOTTOM - VOLUME_ZONE_TOP)
    volume = 1.0 - ratio
    return max(0.0, min(1.0, volume))


def draw_volume_bar(frame, volume, frame_height):
    bar_x, bar_y = 20, frame_height - 50
    bar_width, bar_height = 200, 25
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (255, 255, 255), 2)
    filled_width = int(bar_width * volume)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + filled_width, bar_y + bar_height), (0, 255, 0), -1)
    cv2.putText(
        frame, f"Volume: {int(volume * 100)}%", (bar_x, bar_y - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
    )


def draw_volume_zone(frame, frame_width, frame_height, index_y, active):
    zone_x = frame_width - 60
    top_px = int(VOLUME_ZONE_TOP * frame_height)
    bottom_px = int(VOLUME_ZONE_BOTTOM * frame_height)
    color = (0, 255, 255) if active else (120, 120, 120)
    cv2.line(frame, (zone_x, top_px), (zone_x, bottom_px), color, 3)
    cv2.putText(frame, "100%", (zone_x - 45, top_px + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    cv2.putText(frame, "0%", (zone_x - 35, bottom_px + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    if active:
        marker_y = int(max(top_px, min(bottom_px, index_y * frame_height)))
        cv2.circle(frame, (zone_x, marker_y), 8, (0, 255, 255), -1)


# Draw a legend in the top-left corner listing all available gestures.
# The gesture the user is currently performing is highlighted in green,
# so people can learn the controls just by watching the screen react -
# no need to read a README or memorize anything beforehand.
# 在画面左上角画一个操作指南面板，列出所有可用手势。
# 用户当前正在做的手势会高亮变绿，这样光看屏幕反应就能学会怎么操作，
# 不需要提前读文档或记住任何东西
def draw_gesture_legend(frame, active_item, visible):
    if not visible:
        # Show a small hint on how to bring the legend back
        # 显示一个小提示，告诉用户怎么把面板叫回来
        cv2.putText(frame, "Press H for help", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        return

    items = [
        ("open", "Open Palm  ->  Play"),
        ("fist", "Fist       ->  Pause"),
        ("point", "Point Up/Down (index only)  ->  Volume"),
    ]

    panel_x, panel_y = 15, 15
    panel_w, panel_h = 420, 100

    overlay = frame.copy()
    cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    cv2.putText(frame, "Gesture Guide  (H to hide)", (panel_x + 12, panel_y + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    for i, (key, text) in enumerate(items):
        line_y = panel_y + 45 + i * 22
        color = (0, 255, 0) if key == active_item else (180, 180, 180)
        thickness = 2 if key == active_item else 1
        cv2.putText(frame, text, (panel_x + 12, line_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness)


cap = cv2.VideoCapture(0)
while cap.isOpened():
    success, frame = cap.read()
    if not success:
        print("Failed to read from camera")
        break

    frame_height, frame_width, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    gesture_label = "No hand detected"
    show_zone = False
    current_index_y = 0.5
    active_legend_item = None

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        finger_status = {}
        for name, (tip_id, pip_id) in FINGER_JOINTS.items():
            finger_status[name] = is_finger_up(hand_landmarks, tip_id, pip_id)
        up_count = sum(finger_status.values())

        is_open_palm_shape = (up_count == 4)
        is_fist_shape = (up_count == 0)
        is_pointing_shape = (up_count == 1 and finger_status["index"])

        current_index_y = hand_landmarks.landmark[INDEX_TIP].y

        if is_open_palm_shape:
            active_legend_item = "open"
        elif is_fist_shape:
            active_legend_item = "fist"
        elif is_pointing_shape:
            active_legend_item = "point"

        if mode == "IDLE":
            enter_counter = enter_counter + 1 if is_pointing_shape else 0
            if enter_counter >= PERSISTENCE_FRAMES:
                mode = "ADJUSTING_VOLUME"
                enter_counter = 0
        elif mode == "ADJUSTING_VOLUME":
            exit_counter = exit_counter + 1 if not is_pointing_shape else 0
            if exit_counter >= PERSISTENCE_FRAMES:
                mode = "IDLE"
                exit_counter = 0

        if mode == "ADJUSTING_VOLUME":
            if is_pointing_shape:
                current_volume = calculate_volume_from_position(current_index_y)
                pygame.mixer.music.set_volume(current_volume)
                gesture_label = f"Adjusting volume: {int(current_volume * 100)}%"
            else:
                gesture_label = f"Volume locked at {int(current_volume * 100)}%"
            show_zone = True

        else:
            if is_open_palm_shape and not is_playing:
                if not has_started:
                    pygame.mixer.music.play(loops=-1)
                    has_started = True
                else:
                    pygame.mixer.music.unpause()
                is_playing = True
                gesture_label = "Open Palm - Playing"
            elif is_fist_shape and is_playing:
                pygame.mixer.music.pause()
                is_playing = False
                gesture_label = "Fist - Paused"
            else:
                if is_open_palm_shape:
                    gesture_label = "Open Palm"
                elif is_fist_shape:
                    gesture_label = "Fist"
                else:
                    gesture_label = "Unknown"

        min_x, min_y, max_x, max_y = get_hand_bounding_box(hand_landmarks, frame_width, frame_height)
        label_x = int(min_x)
        label_y = max(int(min_y) - 15, 20)
        (text_w, text_h), _ = cv2.getTextSize(gesture_label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(
            frame, (label_x, label_y - text_h - 8), (label_x + text_w + 10, label_y + 4),
            (0, 0, 0), -1
        )
        cv2.putText(
            frame, gesture_label, (label_x + 5, label_y - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
        )
    else:
        enter_counter = 0
        exit_counter = 0

    draw_volume_zone(frame, frame_width, frame_height, current_index_y, show_zone)
    draw_volume_bar(frame, current_volume, frame_height)
    draw_gesture_legend(frame, active_legend_item, show_legend)

    cv2.imshow('Hand Tracking', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('h'):
        show_legend = not show_legend

cap.release()
cv2.destroyAllWindows()