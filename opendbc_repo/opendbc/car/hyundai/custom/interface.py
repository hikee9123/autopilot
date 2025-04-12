from openpilot.common.params import Params




def get_hyundaiCommunity( ):
  params = Params()
  disengage_on_accelerator = params.get_bool("DisengageOnAccelerator")

  if not disengage_on_accelerator:
    return True

  return False
