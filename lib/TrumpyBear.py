#
#
from lib.Constants import Role
import os
class TrumpyBear:

  def __init__(self, settings, name, role=Role.unknown):
    self.name = name
    self.role = role
    self.log = settings.log
    self.front = None
    self.side = None
    self.name_to_role = {'cecil': Role.owner, 'linda': Role.player,
      'janice': Role.player, 'debby': Role.aquaintance, 'chip': Role.friend,
      'kerri': Role.friend, 'larry': Role.relative, 'laura': Role.relative}
    
  
  # big TODO
  def check_user(self, name):
    # compare name to the authorised users
    role = self.name_to_role.get(name, Role.unknown)
    self.log.info("TrumpyBear thinks %s is a %s", (name, role))
    return role
    
  # TODO save, name, front, side
  def save_user():
    print('back from save_user()')
    return
