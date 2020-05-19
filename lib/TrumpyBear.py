#
#
from lib.Constants import Role
import json
import os
import shutil
from datetime import datetime
class TrumpyBear:

  def __init__(self, settings, name, role=Role.unknown):
    self.name = name
    self.role = role
    self.log = settings.log
    self.front_path = None
    self.face_path = None
    self.side_path = None
    self.db_path = settings.db_path
    # load the db
    np = os.path.join(self.db_path, 'names.json')
    if os.path.isfile(np):
      with open(os.path.join(self.db_path,'names.json'), 'r') as jf:
        self.name_to_role = json.load(jf)
    else:
      self.name_to_role = {'cecil': Role.owner, 'linda': Role.player,
        'janice': Role.player, 'debby': Role.aquaintance, 'chip': Role.friend,
        'kerri': Role.friend, 'larry': Role.relative, 'laura': Role.relative}
   
    self.respell = {"jamis": "janice", 'carrie': 'kerri', 'sea salt': 'cecil',
      'generous': 'janice', 'sisal': 'cecil', 'lynda': 'linda', 'sea': 'cecil',
      'seesaw': 'cecil', 'cfo': 'cecil', 'saints': 'cecil'}
    
  
  def check_user(self, st):
    # compare name to the current users
    role = Role.unknown
    words =  st.split(' ')
    for nm in words:
      nm = self.respell.get(nm, nm)
      role = self.name_to_role.get(nm, None)
      if role is not None:
        self.name = nm
        break

    if role == None:
      self.name = words[-1]
      self.log.info('new name: {}'.format(self.name))
      self.name_to_role[self.name] = Role.unknown
      self.role = Role.unknown
    else:
      self.role = role
    self.log.info("TrumpyBear thinks {} is a {}".format(self.name, self.role))
    return self.role
    
  def save_user(self):
    frontpath = os.path.join(self.db_path, self.name, 'front')
    facepath = os.path.join(self.db_path, self.name, 'face')
    sidepath = os.path.join(self.db_path, self.name, 'side')
    os.makedirs(frontpath, exist_ok=True)
    os.makedirs(facepath, exist_ok=True)
    os.makedirs(sidepath, exist_ok=True)
    with open(os.path.join(self.db_path,'names.json'), 'w') as jf:
      json.dump(self.name_to_role, jf)
    now = datetime.now()
    fn = now.strftime("%Y-%m-%d_%H-%M-%S.jpg")
    shutil.copyfile(self.front_path, os.path.join(frontpath, fn))
    if self.face_path is None:
      shutil.copyfile(self.front_path, os.path.join(facepath, fn))
    else:
      shutil.copyfile(self.face_path, os.path.join(facepath, fn))
    if self.side_path is not None:
      shutil.copyfile(self.side_path, os.path.join(sidepath, fn))
    self.log.info('pictures saved in {}'.format(self.db_path))
    return
    
