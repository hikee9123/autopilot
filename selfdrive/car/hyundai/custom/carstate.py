import copy

from cereal import car, log
from panda import ALTERNATIVE_EXPERIENCE
from openpilot.common.params import Params
from openpilot.common.conversions import Conversions as CV
from openpilot.selfdrive.controls.lib.events import Events
from openpilot.selfdrive.car.hyundai.values import CAR, Buttons
from openpilot.selfdrive.custom.params_json import read_json_file

import cereal.messaging as messaging

import openpilot.selfdrive.custom.loger as  trace1

EventName = car.CarEvent.EventName
LaneChangeState = log.LaneChangeState

class CarStateCustom():
  def __init__(self, CP, CS):
    self.CS = CS
    self.CP = CP
    self.params = Params()
    self.oldCruiseStateEnabled = False
    self.frame = 0
    self.acc_active = 0

    self.cruise_buttons_old = 0
    self.control_mode = 0
    self.clu_Vanz = 0
    self.is_highway = False


    self.timer_init = 500   # 5sec
    self.timer_resume = 500

    # cruise_speed_button
    self.old_acc_active = 0
    self.prev_acc_active = 0
    self.cruise_set_speed_kph = 0
    self.cruise_buttons_time = 0
    self.VSetDis = 0
    self.prev_cruise_btn = 0
    self.lead_distance = 0

    self.gapSet = 4
    self.timer_engaged = 0
    self.slow_engage = 1

    self.leftLaneTime = 50
    self.rightLaneTime = 50

    self.desiredCurvature = 0




    try:
      m_jsonobj = read_json_file("CustomParam")
      self.autoLaneChange = m_jsonobj["AutoLaneChange"]
      self.menu_debug = m_jsonobj["debug"]
    except Exception as e:
      self.autoLaneChange = 0
      self.menu_debug = 0
    
    self.lanechange_wait = 0
    self.controlsAllowed = 0

    self.laneChangeState = LaneChangeState.off
    #extern data
    self.NC = None    # NaviControl

    self.cars = []
    self.get_type_of_car( CP )


  def get_type_of_car( self, CP ):
    cars = []
    for _, member in CAR.__members__.items():
      cars.append(member.value)
    #cars.sort()
    self.cars = cars


  def get_can_parser( self, messages, CP ):
    messages += [
      ("TPMS11", 5),
    ]


  @staticmethod
  def get_cam_can_parser( messages, CP ):
    messages += [
      ("LFAHDA_MFC", 20),          
    ]



  def cruise_control_mode( self ):
    cruise_buttons = self.CS.prev_cruise_buttons
    if cruise_buttons == self.cruise_buttons_old:
       return
      
    self.cruise_buttons_old = cruise_buttons
    if cruise_buttons == (Buttons.RES_ACCEL): 
      self.control_mode += 1
    elif cruise_buttons == (Buttons.SET_DECEL):
      self.control_mode -= 1

    if self.control_mode < 0:
      self.control_mode = 0
    elif self.control_mode > 5:
      self.control_mode = 0

  def cruise_speed_button( self ):
    if self.prev_acc_active != self.acc_active:
      self.old_acc_active = self.prev_acc_active
      self.prev_acc_active = self.acc_active
      self.cruise_set_speed_kph = self.VSetDis

    set_speed_kph = self.cruise_set_speed_kph
    if not self.acc_active:
      return self.cruise_set_speed_kph

    cruise_buttons = self.CS.prev_cruise_buttons   #cruise_buttons[-1]
    if cruise_buttons in (Buttons.RES_ACCEL, Buttons.SET_DECEL):
      self.cruise_buttons_time += 1
    else:
      self.cruise_buttons_time = 0

    # long press should set scc speed with cluster scc number
    if self.cruise_buttons_time >= 55:
      self.cruise_set_speed_kph = self.VSetDis
      return self.cruise_set_speed_kph


    if self.prev_cruise_btn == cruise_buttons:
      return self.cruise_set_speed_kph

    self.prev_cruise_btn = cruise_buttons

    if cruise_buttons == (Buttons.RES_ACCEL): 
      set_speed_kph = self.VSetDis + 1
    elif cruise_buttons == (Buttons.SET_DECEL):
      if self.CS.out.gasPressed or not self.old_acc_active:
        set_speed_kph = self.clu_Vanz
      else:
        set_speed_kph = self.VSetDis - 1

    if set_speed_kph < 30:
      set_speed_kph = 30

    self.cruise_set_speed_kph = set_speed_kph
    return  set_speed_kph
  
  def set_cruise_speed( self, set_speed ):
    self.cruise_set_speed_kph = set_speed  

  def get_tpms(self, ret, unit, fl, fr, rl, rr):
    factor = 0.72519 if unit == 1 else 0.1 if unit == 2 else 1 # 0:psi, 1:kpa, 2:bar
    ret.unit = unit
    ret.fl = fl * factor
    ret.fr = fr * factor
    ret.rl = rl * factor
    ret.rr = rr * factor

  def send_carstatus( self, ret, cp, CS ):
    if self.menu_debug == 0:
      return


    carSCustom = car.CarState.CarSCustom.new_message()
    carSCustom.supportedCars = self.cars
    carSCustom.breakPos = self.brakePos
    carSCustom.leadDistance = self.lead_distance
    carSCustom.gapSet = self.gapSet
    carSCustom.electGearStep = cp.vl["ELECT_GEAR"]["Elect_Gear_Step"] # opkr
    self.get_tpms( carSCustom.tpms,
      cp.vl["TPMS11"]["UNIT"],
      cp.vl["TPMS11"]["PRESSURE_FL"],
      cp.vl["TPMS11"]["PRESSURE_FR"],
      cp.vl["TPMS11"]["PRESSURE_RL"],
      cp.vl["TPMS11"]["PRESSURE_RR"],
    )




    ret.carSCustom = carSCustom

    #log
    """
    trace1.printf1( 'MD={:.0f},{:.0f},{:.0f}'.format( self.control_mode,  CS.customCS.timer_init, self.controlsAllowed ) )
    trace1.printf2( 'Y={:5.1f}, X={:5.1f}, CV={:7.5f}'.format( self.NC.modelyDistance, self.NC.modelxDistance, self.desiredCurvature ) )

    if self.CP.openpilotLongitudinalControl:
      trace1.printf3( 'SW={:.0f},{:.0f},{:.0f} T={:.0f},{:.0f}'.format(
          cp.vl["CLU11"]["CF_Clu_CruiseSwState"], cp.vl["CLU11"]["CF_Clu_CruiseSwMain"], cp.vl["CLU11"]["CF_Clu_SldMainSW"],
          cp.vl["TCS13"]["ACCEnable"], cp.vl["TCS13"]["ACC_REQ"]
      ))
    """



  def auto_lene_change( self, ret ):
    if self.NC == None:
      self.lanechange_wait = 150
      return
    

    self.modelxDistance = self.NC.modelxDistance
    model_v2 = self.NC.sm['modelV2']
    self.desiredCurvature = model_v2.action.desiredCurvature 
    self.laneChangeState = model_v2.meta.laneChangeState
    if not self.autoLaneChange:
      return
    
    leftLaneVisible = 0
    rightLaneVisible = 0        
    if len(model_v2.laneLineProbs):
      if bool(model_v2.laneLineProbs[3] > 0.5):
        rightLaneVisible |= 2   
      if bool(model_v2.laneLineProbs[2] > 0.5):
        rightLaneVisible |= 1
      if bool(model_v2.laneLineProbs[1] > 0.5):
        leftLaneVisible |= 1
      if bool(model_v2.laneLineProbs[0] > 0.5):
        leftLaneVisible |= 2    

      if (leftLaneVisible & 2):
        self.leftLaneTime = 50
      if (rightLaneVisible & 2):
        self.rightLaneTime = 50

    if self.lanechange_wait > 0:
      self.lanechange_wait -= 1

    if self.leftLaneTime > 0:
      self.leftLaneTime -= 1

    if self.rightLaneTime > 0:
      self.rightLaneTime -= 1


    leftBlinker = ret.leftBlinker
    rightBlinker = ret.rightBlinker


    if self.laneChangeState == LaneChangeState.off:
      if leftBlinker and rightBlinker:
        self.lanechange_wait = 200
        ret.leftBlinker = False        
        ret.rightBlinker = False
      elif self.lanechange_wait < 50:
        self.lanechange_wait = 50
    elif self.laneChangeState == LaneChangeState.preLaneChange:
      if leftBlinker:
        if (self.leftLaneTime <= 0):
          pass
        elif self.lanechange_wait <= 1:
          ret.steeringTorque = self.CS.params.STEER_THRESHOLD  #150
          ret.steeringPressed = True
      elif rightBlinker:
        if (self.rightLaneTime <= 0):
          pass
        elif self.lanechange_wait <= 1:
          ret.steeringTorque = -self.CS.params.STEER_THRESHOLD
          ret.steeringPressed = True




  def update(self, ret, CS,  cp, cp_cruise, cp_cam ):
    if self.CP.openpilotLongitudinalControl:
      mainMode_ACC = cp.vl["TCS13"]["ACCEnable"] == 0
      self.acc_active = cp.vl["TCS13"]["ACC_REQ"] == 1

      self.lead_distance = 0
      self.gapSet = 4

    else:
      mainMode_ACC = cp_cruise.vl["SCC11"]["MainMode_ACC"] == 1
      self.acc_active = (cp_cruise.vl["SCC12"]['ACCMode'] != 0)
      if self.acc_active:
        ret.cruiseState.speed = self.cruise_speed_button() * CV.KPH_TO_MS
      else:
        ret.cruiseState.speed = 0

      self.lead_distance = cp_cruise.vl["SCC11"]["ACC_ObjDist"]
      self.gapSet = cp_cruise.vl["SCC11"]['TauGapSet']
      self.VSetDis = cp_cruise.vl["SCC11"]["VSetDis"]   # kph   크루즈 설정 속도.        
  
      if not mainMode_ACC:
        self.cruise_control_mode()

    # save the entire LFAHDA_MFC
    self.lfahda = copy.copy(cp_cam.vl["LFAHDA_MFC"])
    self.mdps12 = copy.copy(cp.vl["MDPS12"])

    ret.engineRpm = cp.vl["E_EMS11"]["N"] # opkr
    ret.brakeLightsDEPRECATED = bool( cp.vl["TCS13"]['BrakeLight'] )
    self.brakePos = cp.vl["E_EMS11"]["Brake_Pedal_Pos"] 
    self.is_highway = self.lfahda["HDA_Icon_State"] != 0.
    self.clu_Vanz = cp.vl["CLU11"]["CF_Clu_Vanz"]     # kph  현재 차량의 속도.
    

    if (self.NC != None) and any(ps.controlsAllowed for ps in self.NC.sm['pandaStates']):
      self.controlsAllowed = 1
    else:
      self.controlsAllowed = 0

    if self.timer_init > 0:
      self.timer_init -= 1
      ret.cruiseState.enabled = False
    elif not self.CP.openpilotLongitudinalControl:
      if not (CS.CP.alternativeExperience & ALTERNATIVE_EXPERIENCE.DISABLE_DISENGAGE_ON_GAS):
        pass
      elif self.acc_active:
        pass
      elif ret.parkingBrake:
        self.timer_engaged = 100
        self.oldCruiseStateEnabled = False
      elif ret.doorOpen:
        self.timer_engaged = 100
        self.oldCruiseStateEnabled = False
      elif ret.seatbeltUnlatched:
        self.timer_engaged = 100
        self.oldCruiseStateEnabled = False
      elif ret.gearShifter != car.CarState.GearShifter.drive:
        self.timer_engaged = 100
        self.oldCruiseStateEnabled = False
      elif not ret.cruiseState.available:
        self.slow_engage = 1
        self.timer_engaged = 0
        self.oldCruiseStateEnabled = True
      elif self.oldCruiseStateEnabled:
        ret.cruiseState.enabled = True
      elif (self.clu_Vanz < 10) or (abs(ret.steeringAngleDeg) > 3) or self.controlsAllowed == 0:
        self.timer_engaged = 50
      elif (self.timer_engaged <= 0):
        self.slow_engage = 0
        self.oldCruiseStateEnabled = True
        CS.cruise_buttons.append( Buttons.CANCEL )

    if self.timer_engaged:
      self.timer_engaged -= 1
    self.frame += 1
    if self.timer_init > 0:
      return

    self.auto_lene_change( ret )
    self.send_carstatus( ret, cp, CS )



  def create_events(self, ret_cs, CS, events):
    if self.timer_resume > 0:
        self.timer_resume -= 1

    v_ego_kph = self.clu_Vanz   # CS.cluster_speed
    if ret_cs.cruiseState.enabled or ret_cs.gasPressed:
      self.timer_resume = 50
    elif v_ego_kph <= 0.1 and  self.modelxDistance > 30:
      if self.timer_resume <= 0:
        events.add( EventName.chimeAtResume )
    else:
      self.timer_resume = 50

    return events
