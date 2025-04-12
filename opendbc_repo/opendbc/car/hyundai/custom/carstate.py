import copy

from cereal import car, log
import cereal.messaging as messaging

from openpilot.common.params import Params
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.hyundai.values import Buttons


class CarStateCustom():
  def __init__(self, CP, CS):
    self.CS = CS
    self.CP = CP
    self.params = Params()

  @staticmethod
  def get_cam_can_parser( messages, CP ):
    messages += [
      ("LFAHDA_MFC", 20),
    ]

  def update(self, ret, CS,  cp, cp_cruise, cp_cam ):
    if self.CP.openpilotLongitudinalControl:
      mainMode_ACC = cp.vl["TCS13"]["ACCEnable"] == 0
      self.acc_active = cp.vl["TCS13"]["ACC_REQ"] == 1
    else:
      mainMode_ACC = cp_cruise.vl["SCC11"]["MainMode_ACC"] == 1
      self.acc_active = (cp_cruise.vl["SCC12"]['ACCMode'] != 0)
      if self.acc_active:
        ret.cruiseState.speed = self.VSetDis * CV.KPH_TO_MS
      else:
        ret.cruiseState.speed = 0

      self.lead_distance = cp_cruise.vl["SCC11"]["ACC_ObjDist"]
      self.gapSet = cp_cruise.vl["SCC11"]['TauGapSet']
      self.VSetDis = cp_cruise.vl["SCC11"]["VSetDis"]   # kph   크루즈 설정 속도.


      if self.acc_active:
        pass
      elif mainMode_ACC:
        ret.cruiseState.enabled = True

