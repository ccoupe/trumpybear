# Constants and Enums for TrumpyBear app
import enum 
from enum import IntEnum

class Role(IntEnum): 
  unknown = 0
  owner = 1
  friend = 2
  relative = 3
  aquaintance = 4
  player = 5
  unwanted = 6

class State(enum.Enum): 
  initialized = 0
  starting = 1
  waitname = 2
  waitface = 3
  waitside = 4
  waitfront = 5
  waitrecog = 6
  role_dispatch = 7
  four_qs = 8
  aborting = 9
  waitrange = 10


class Event(enum.Enum):
  start = 0   # from mqtt (hubitat)
  reply = 1   # tts from mycroft
  pict = 2    # from mqttcamera
  recog = 3   # from face_recognition server
  watchdog = 5 # timer fired
  ranger = 6   # from autoranger device
  abort = 7   # from mqtt (hubitat)
  motion = 8  # from the camera
