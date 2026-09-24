# Gesture Music Controller

Control music playback and volume with hand gestures, using your webcam. No mouse, no keyboard, just your hand.

## Demo



## Features

- Open palm plays the music. Fist pauses it.
- Point with your index finger and move your hand up or down to set the volume.
- A live guide panel shows which gesture does what. Press H to hide it.
- Volume bar and slider track show your current level in real time.
- Works with two hands at once. Labels follow each hand so nothing overlaps.

## Tech Stack

Python, MediaPipe, OpenCV, pygame

## Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/gesture-music-controller.git
cd gesture-music-controller

# Create a virtual environment (Python 3.10 or 3.11 recommended)
python3.11 -m venv env
source env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Drop an mp3 file in the project folder and name it `music.mp3`.

## Usage

```bash
python hand_tracking.py
```

| Gesture | Action |
|---|---|
| Open palm | Play |
| Fist | Pause |
| Point with index finger, move hand up/down | Set volume |
| Press `q` | Quit |
| Press `h` | Show/hide the on-screen guide |

## Design Decisions

This is the part I actually want people to read. The gesture logic went through a few rounds of rework, and each round taught me something.

### Detecting if a finger is up

My first attempt compared the y-coordinate of the fingertip to the y-coordinate of the base of the finger. If the tip sat higher on screen, I called the finger extended.

This broke the moment the hand turned sideways. Point your hand at an angle and the tip and base end up at nearly the same height, even though the finger is fully extended.

The fix was to compare distances instead of heights. I measure how far the fingertip is from the wrist, and how far the middle joint is from the wrist. If the tip is farther away, the finger is extended. This holds true no matter which direction the hand is facing, because it's a straight line measurement, not a direction.

### The volume and fist conflict

My first volume control used the distance between thumb and index finger, like a pinch. Squeeze the fingers together, volume drops. Spread them apart, volume rises.

The problem showed up fast. Squeezing the fingers all the way down to hit zero volume looks almost exactly like making a fist. The app kept mistaking "volume at zero" for "fist," and would pause the music on its own.

I looked at how real AR and VR products deal with this, since headsets like Vision Pro and Quest run into the same kind of gesture overlap constantly. A few things came up. One study on pinch gestures found that fingers sitting near the pinch threshold cause the system to flicker between "pinching" and "not pinching." Their fix was a short delay, requiring the same reading to hold steady for about 100 milliseconds before the state actually switches. Another common approach is a state machine with a locked mode. You enter a mode with one clear gesture, and you leave it with another clear gesture. The app stops re-guessing your gesture every single frame once it's locked into a mode.

I used both. Pointing with just the index finger, with the other three fingers curled in, is the entry gesture for volume mode. Once that mode kicks in, the app ignores the rest of your fingers completely. It only tracks your index finger's height on screen. You can drop the volume to zero without the app ever thinking you made a fist. To leave volume mode, you open your hand fully or make a fist, and hold it for a few frames in a row so a stray twitch doesn't trigger an early exit.

### Why volume follows hand position, not pinch distance

After fixing the fist conflict, the pinch-based volume control still felt clumsy. Holding a steady, precise gap between two fingers in midair is hard to do.

So I dropped pinch distance and mapped volume straight to how high or low your index finger sits on screen. Move your hand up, volume goes up. Move it down, volume goes down. Once you switch out of the pointing gesture, whatever volume you landed on stays locked in. Nothing drifts after you let go.

### Making the controls obvious without a manual

Nobody wants to read a manual before trying a demo, especially if someone's watching over your shoulder in an interview. I added a small guide panel in the corner of the screen listing all three gestures. Whichever one you're currently doing lights up green. You learn the controls just by moving your hand and watching the screen react. Press H to hide the panel once you know what you're doing, or before recording a clean demo video.

## Future Ideas

- Swipe gestures for next/previous track
- A virtual object overlaid on the hand, moving toward an AR-style interaction
- Smoothing gesture detection across several frames to cut down on small jitters
