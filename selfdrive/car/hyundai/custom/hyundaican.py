import crcmod
from cereal import car
from openpilot.selfdrive.car.hyundai.values import CAR, CHECKSUM, CAMERA_SCC_CAR



GearShifter = car.CarState.GearShifter
hyundai_checksum = crcmod.mkCrcFun(0x11D, initCrc=0xFD, rev=False, xorOut=0xdf)


def create_clu11(packer, frame, clu11, button, car_fingerprint):
  values = clu11
  #frame = (values["CF_Clu_AliveCnt1"] + 1)
  
  values["CF_Clu_CruiseSwState"] = button
  values["CF_Clu_AliveCnt1"] = frame % 0x10
  # send buttons to camera on camera-scc based cars
  bus = 2 if car_fingerprint in CAMERA_SCC_CAR else 0
  return packer.make_can_msg("CLU11", bus, values)



# 20 Hz 
def create_hda_mfc( packer, CS, CC ):
  values = CS.customCS.lfahda
  enabled = CC.enabled

  ldwSysState = 0
  if CC.hudControl.leftLaneVisible:
     ldwSysState += 1
  if CC.hudControl.rightLaneVisible:
     ldwSysState += 2

  # HDA_USM  2 normal   3 이상동작.
  # LFA_Icon_State   0 no_hda  1 white_hda  2 green_hda
  values["HDA_LdwSysState"] = ldwSysState
  values["HDA_Icon_Wheel"] = 1 if enabled else 0
  return packer.make_can_msg("LFAHDA_MFC", 0, values)

# 100 Hz
def create_mdps12(packer, frame, mdps12):
  values = mdps12
  values["CF_Mdps_ToiActive"] = 0      # 1:enable  0:normal
  values["CF_Mdps_ToiUnavail"] = 1     # 0
  values["CF_Mdps_MsgCount2"] = frame % 0x100
  values["CF_Mdps_Chksum2"] = 0

  dat = packer.make_can_msg("MDPS12", 2, values)[2]
  checksum = sum(dat) % 256
  values["CF_Mdps_Chksum2"] = checksum

  return packer.make_can_msg("MDPS12", 2, values)   # 0



def create_acc_commands(packer, CC, CS, accel, upper_jerk, idx, set_speed, stopping, use_fca):
  enabled = CC.enabled
  hud_control = CC.hudControl
  long_override = CC.cruiseControl.override

  lead_visible = hud_control.leadVisible
  gapSet = CS.customCS.gapSet

  commands = []

  scc11_values = {
    "MainMode_ACC": 1,
    "TauGapSet": gapSet,
    "VSetDis": set_speed if enabled else 0,
    "AliveCounterACC": idx % 0x10,
    "ObjValid": 1, # close lead makes controls tighter
    "ACC_ObjStatus": 1, # close lead makes controls tighter
    "ACC_ObjLatPos": 0,
    "ACC_ObjRelSpd": 0,
    "ACC_ObjDist": 1, # close lead makes controls tighter
    }
  commands.append(packer.make_can_msg("SCC11", 0, scc11_values))

  scc12_values = {
    "ACCMode": 2 if enabled and long_override else 1 if enabled else 0,
    "StopReq": 1 if stopping else 0,
    "aReqRaw": accel,
    "aReqValue": accel,  # stock ramps up and down respecting jerk limit until it reaches aReqRaw
    "CR_VSM_Alive": idx % 0xF,
  }

  # show AEB disabled indicator on dash with SCC12 if not sending FCA messages.
  # these signals also prevent a TCS fault on non-FCA cars with alpha longitudinal
  if not use_fca:
    scc12_values["CF_VSM_ConfMode"] = 1
    scc12_values["AEB_Status"] = 1  # 1  # AEB disabled

  scc12_dat = packer.make_can_msg("SCC12", 0, scc12_values)[2]
  scc12_values["CR_VSM_ChkSum"] = 0x10 - sum(sum(divmod(i, 16)) for i in scc12_dat) % 0x10

  commands.append(packer.make_can_msg("SCC12", 0, scc12_values))

  scc14_values = {
    "ComfortBandUpper": 0.0, # stock usually is 0 but sometimes uses higher values
    "ComfortBandLower": 0.0, # stock usually is 0 but sometimes uses higher values
    "JerkUpperLimit": upper_jerk, # stock usually is 1.0 but sometimes uses higher values
    "JerkLowerLimit": 5.0, # stock usually is 0.5 but sometimes uses higher values
    "ACCMode": 2 if enabled and long_override else 1 if enabled else 4, # stock will always be 4 instead of 0 after first disengage
    "ObjGap": 2 if lead_visible else 0, # 5: >30, m, 4: 25-30 m, 3: 20-25 m, 2: < 20 m, 0: no lead
  }
  commands.append(packer.make_can_msg("SCC14", 0, scc14_values))

  # Only send FCA11 on cars where it exists on the bus
  if use_fca:
    # note that some vehicles most likely have an alternate checksum/counter definition
    # https://github.com/commaai/opendbc/commit/9ddcdb22c4929baf310295e832668e6e7fcfa602
    fca11_values = {
      "CR_FCA_Alive": idx % 0xF,
      "PAINT1_Status": 1,
      "FCA_DrvSetStatus": 1,
      "FCA_Status": 1,  # AEB disabled
    }
    fca11_dat = packer.make_can_msg("FCA11", 0, fca11_values)[2]
    fca11_values["CR_FCA_ChkSum"] = hyundai_checksum(fca11_dat[:7])
    commands.append(packer.make_can_msg("FCA11", 0, fca11_values))

  return commands