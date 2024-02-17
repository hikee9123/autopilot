import crcmod
from cereal import car
from openpilot.selfdrive.car.hyundai.values import CAR, CHECKSUM, CAMERA_SCC_CAR



GearShifter = car.CarState.GearShifter
hyundai_checksum = crcmod.mkCrcFun(0x11D, initCrc=0xFD, rev=False, xorOut=0xdf)

# 100 Hz
def hyundai_lkas11(packer, frame, car_fingerprint, apply_steer, steer_req,
                  torque_fault, lkas11, sys_warning, sys_state, enabled,
                  left_lane, right_lane,
                  left_lane_depart, right_lane_depart):
  
  values = lkas11
  #values["CF_Lkas_LdwsSysState"] = sys_state

  values["CF_Lkas_MsgCount"] = frame % 0x10
  
  dat = packer.make_can_msg("LKAS11", 0, values)[2]

  if car_fingerprint in CHECKSUM["crc8"]:
    # CRC Checksum as seen on 2019 Hyundai Santa Fe
    dat = dat[:6] + dat[7:8]
    checksum = hyundai_checksum(dat)
  elif car_fingerprint in CHECKSUM["6B"]:
    # Checksum of first 6 Bytes, as seen on 2018 Kia Sorento
    checksum = sum(dat[:6]) % 256
  else:
    # Checksum of first 6 Bytes and last Byte as seen on 2018 Kia Stinger
    checksum = (sum(dat[:6]) + dat[7]) % 256

  values["CF_Lkas_Chksum"] = checksum

  return packer.make_can_msg("LKAS11", 0, values)


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
