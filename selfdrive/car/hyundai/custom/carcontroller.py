from cereal import car

from openpilot.selfdrive.car.hyundai.values import HyundaiFlags, Buttons, CAR
from openpilot.selfdrive.car.hyundai.hyundaican import create_lkas11
from openpilot.selfdrive.car.hyundai.custom.hyundaican import hyundai_lkas11, create_clu11, create_hda_mfc, create_mdps12
from openpilot.selfdrive.car.hyundai.custom.navicontrol  import NaviControl

VisualAlert = car.CarControl.HUDControl.VisualAlert

class CarControllerCustom:
  def __init__(self, CP):
    self.CP = CP
    self.car_fingerprint = CP.carFingerprint    
    self.NC = NaviControl( CP)
    self.resume_cnt = 0
    self.time_left = 0
    self.time_right = 0



  def process_hud_alert(self, enabled, hud_control):
    sys_warning = (hud_control.visualAlert in (VisualAlert.steerRequired, VisualAlert.ldw))

    left = hud_control.leftLaneVisible 
    right = hud_control.rightLaneVisible

    if left:
      self.time_left = 50
    elif self.time_left:
      self.time_left -= 1

    if self.time_left:
      left = True

    if right:
      self.time_right = 50
    elif self.time_right:
      self.time_right -= 1

    if self.time_right:
      right = True

    # initialize to no line visible
    # TODO: this is not accurate for all cars
    sys_state = 1
    if left and right or sys_warning:  # HUD alert only display when LKAS status is active
      sys_state = 3 if enabled or sys_warning else 4
    elif left:
      sys_state = 5
    elif right:
      sys_state = 6

    # initialize to no warnings
    left_lane_warning = 0
    right_lane_warning = 0
    if hud_control.leftLaneDepart:
      left_lane_warning = 1 if self.car_fingerprint in (CAR.GENESIS_G90, CAR.GENESIS_G80) else 2
    if hud_control.rightLaneDepart:
      right_lane_warning = 1 if self.car_fingerprint in (CAR.GENESIS_G90, CAR.GENESIS_G80) else 2

    return sys_warning, sys_state, left_lane_warning, right_lane_warning



  def custom_lkas11(self, can_sends, packer, frame, apply_steer, steer_req, CS, CC ):
    hud_control = CC.hudControl
    left_lane = hud_control.leftLaneVisible, 
    right_lane = hud_control.rightLaneVisible
    enable = CC.enabled

    # Hold torque with induced temporary fault when cutting the actuation bit
    torque_fault = CC.latActive and not steer_req

     # HUD messages
    sys_warning, sys_state, left_lane_depart, right_lane_depart = self.process_hud_alert( enable,  hud_control )

    if CS.customCS.slow_engage < 1:
      slow_engage = max(0, CS.customCS.slow_engage )
      CS.customCS.slow_engage += 0.01
      if slow_engage < 1:
        apply_torque = apply_steer * slow_engage
        apply_steer = int(round(float(apply_torque)))


      
    can_sends.append( create_lkas11(packer, frame, self.CP, apply_steer, steer_req,
                                    torque_fault, CS.lkas11, sys_warning, sys_state, enable,
                                    left_lane, right_lane,
                                    left_lane_depart, right_lane_depart) )


    if not self.CP.openpilotLongitudinalControl:
      can_sends.append( create_mdps12( packer, frame, CS.customCS.mdps12 ) )  # 100 Hz send mdps12 to LKAS to prevent LKAS error
      self.create_button_messages( packer, can_sends, CC, CS, frame )  #custom

  




  # 20 Hz LFA MFA message
  def custom_hda_mfc(self, can_sends, packer, CS,  CC ):
    can_sends.append( create_hda_mfc( packer, CS, CC ) )



  def create_button_messages(self, packer, can_sends, CC: car.CarControl, CS: car.CarState, frame: int):
    if CC.cruiseControl.cancel:
      can_sends.append(create_clu11( packer, frame, CS.clu11, Buttons.CANCEL, self.CP.carFingerprint))
    elif CS.customCS.acc_active:
      #custom 
      btn_signal = self.NC.update( CC, CS, frame )
      if btn_signal != None:
        can_sends.extend( [create_clu11( packer, self.resume_cnt, CS.clu11, btn_signal, self.CP.carFingerprint)] * 2 )
        self.resume_cnt += 1
      else:
        self.resume_cnt = 0
