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
  getname = 2
  waitfr = 3
  waitrecog = 4
  waitsd = 5
  role_dispatch = 6

class Event(enum.Enum):
  start = 0
  reply = 1
  frpict = 2
  sdpict = 3
  recog = 4
