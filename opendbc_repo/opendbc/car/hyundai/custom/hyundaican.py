from cereal import car
from opendbc.car.hyundai.values import CAR, CHECKSUM, CAMERA_SCC_CAR






# 100 Hz
def create_mdps12(packer, frame, mdps12):
  values = mdps12
  values["CF_Mdps_ToiActive"] = 0      # 1:enable  0:normal
  values["CF_Mdps_ToiUnavail"] = 1     # 0
  values["CF_Mdps_MsgCount2"] = frame % 0x100
  values["CF_Mdps_Chksum2"] = 0

  dat = packer.make_can_msg("MDPS12", 2, values)[1]
  checksum = sum(dat) % 256
  values["CF_Mdps_Chksum2"] = checksum

  return packer.make_can_msg("MDPS12", 2, values)   # 0
