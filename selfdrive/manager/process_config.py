import os
import json    #custom

from cereal import car
from openpilot.common.params import Params
from openpilot.system.hardware import PC, TICI
from openpilot.selfdrive.manager.process import PythonProcess, NativeProcess, DaemonProcess
from openpilot.selfdrive.athena.athenad import setNavDestination

WEBCAM = os.getenv("USE_WEBCAM") is not None

def driverview(started: bool, params: Params, CP: car.CarParams) -> bool:
  return started or params.get_bool("IsDriverViewEnabled")

def notcar(started: bool, params: Params, CP: car.CarParams) -> bool:
  return started and CP.notCar

def iscar(started: bool, params: Params, CP: car.CarParams) -> bool:
  return started and not CP.notCar

def logging(started, params, CP: car.CarParams) -> bool:
  run = params.get_bool( "EnableLogging" )
  #run = (not CP.notCar) or not params.get_bool("DisableLogging")
  return started and run

def ublox_available() -> bool:
  return os.path.exists('/dev/ttyHS0') and not os.path.exists('/persist/comma/use-quectel-gps')

def ublox(started, params, CP: car.CarParams) -> bool:
  use_ublox = ublox_available()
  if use_ublox != params.get_bool("UbloxAvailable"):
    params.put_bool("UbloxAvailable", use_ublox)
  return started and use_ublox

def qcomgps(started, params, CP: car.CarParams) -> bool:
  return started and not ublox_available()

def always_run(started, params, CP: car.CarParams) -> bool:
  return True

def only_onroad(started: bool, params, CP: car.CarParams) -> bool:
  return started

def only_offroad(started, params, CP: car.CarParams) -> bool:
  return not started

#custom
def UseExternalNaviRoutes()  -> bool:
  return Params().get_bool("UseExternalNaviRoutes")

def ExternalNaviType()  -> int:
  externalNaviType = 0  
  if UseExternalNaviRoutes():
    try:
      externalNaviType = int( Params().get('ExternalNaviType', encoding='utf8') )
    except Exception as e:
      print(f"ExternalNaviType error occurred: {e}")
      externalNaviType = 0

  return externalNaviType

def set_mapbox()  -> bool:
  if UseExternalNaviRoutes():
    mapbox_token = Params().get("MapboxToken", encoding='utf8')
    if mapbox_token is not None:
        os.environ['MAPBOX_TOKEN'] = mapbox_token
    else:
        print("Mapbox token is None. Please check your configuration.")
  
    print('1.environ (set_mapbox)  mapbox_token ={}'.format(mapbox_token) )


    #custom
    #setNavDestination( 36.85520956438799,  127.10113048553467, "KNJ", "음봉면 산동리 123-1" )
    destinations = [
      {
          "label": "home",
          "place_name": "Y-CITY",
          "latitude": 36.7973763270954,
          "longitude": 127.10827665676986,
          "place_details": "배방읍 광장로 210",
          "save_type": "favorite",
      },
      {
          "label": "work",
          "place_name": "KNJ",
          "latitude": 36.85520956438799,
          "longitude": 127.10113048553467,
          "place_details": "음봉면 산동리 123-1",
          "save_type": "favorite",
      },
      {
          "label": "recent",
          "place_name": "고향",
          "latitude": 37.064122032373774,
          "longitude": 127.80750423325486,
          "place_details": "충주시 동막고개길",
          "save_type": "favorite",
      },
      {
          "label": "recent",
          "place_name": "서울아산병원",
          "latitude": 37.5265455,
          "longitude": 127.1081223,
          "place_details": "송파구 올림픽로43길 88",
          "save_type": "favorite",
      },
    ]
    Params().put("NavPastDestinations", json.dumps(destinations) )    
  return True 



procs = [
  DaemonProcess("manage_athenad", "selfdrive.athena.manage_athenad", "AthenadPid"),

  NativeProcess("camerad", "system/camerad", ["./camerad"], driverview),
  NativeProcess("logcatd", "system/logcatd", ["./logcatd"], only_onroad),
  NativeProcess("proclogd", "system/proclogd", ["./proclogd"], only_onroad),
  PythonProcess("logmessaged", "system.logmessaged", always_run),
  PythonProcess("micd", "system.micd", iscar),
  PythonProcess("timed", "system.timed", always_run, enabled=not PC),

  PythonProcess("dmonitoringmodeld", "selfdrive.modeld.dmonitoringmodeld", driverview, enabled=(not PC or WEBCAM)),
  NativeProcess("encoderd", "system/loggerd", ["./encoderd"], only_onroad),
  NativeProcess("stream_encoderd", "system/loggerd", ["./encoderd", "--stream"], notcar),
  NativeProcess("loggerd", "system/loggerd", ["./loggerd"], logging),
  NativeProcess("modeld", "selfdrive/modeld", ["./modeld"], only_onroad),
  NativeProcess("mapsd", "selfdrive/navd", ["./mapsd"], only_onroad),
  PythonProcess("navmodeld", "selfdrive.modeld.navmodeld", only_onroad),
  NativeProcess("sensord", "system/sensord", ["./sensord"], only_onroad, enabled=not PC),
  NativeProcess("ui", "selfdrive/ui", ["./ui"], always_run, watchdog_max_dt=(5 if not PC else None)),
  PythonProcess("soundd", "selfdrive.ui.soundd", only_onroad),
  NativeProcess("locationd", "selfdrive/locationd", ["./locationd"], only_onroad),
  NativeProcess("boardd", "selfdrive/boardd", ["./boardd"], always_run, enabled=False),
  PythonProcess("calibrationd", "selfdrive.locationd.calibrationd", only_onroad),
  PythonProcess("torqued", "selfdrive.locationd.torqued", only_onroad),
  PythonProcess("controlsd", "selfdrive.controls.controlsd", only_onroad),
  PythonProcess("deleter", "system.loggerd.deleter", always_run),
  PythonProcess("dmonitoringd", "selfdrive.monitoring.dmonitoringd", driverview, enabled=(not PC or WEBCAM)),
  PythonProcess("qcomgpsd", "system.qcomgpsd.qcomgpsd", qcomgps, enabled=TICI),
  PythonProcess("navd", "selfdrive.navd.navd", only_onroad, enabled=not UseExternalNaviRoutes() ),
  PythonProcess("pandad", "selfdrive.boardd.pandad", always_run),
  PythonProcess("paramsd", "selfdrive.locationd.paramsd", only_onroad),
  NativeProcess("ubloxd", "system/ubloxd", ["./ubloxd"], ublox, enabled=TICI),
  PythonProcess("pigeond", "system.ubloxd.pigeond", ublox, enabled=TICI),
  PythonProcess("plannerd", "selfdrive.controls.plannerd", only_onroad),
  PythonProcess("radard", "selfdrive.controls.radard", only_onroad),
  PythonProcess("thermald", "selfdrive.thermald.thermald", always_run),
  PythonProcess("tombstoned", "selfdrive.tombstoned", always_run, enabled=not PC),
  PythonProcess("updated", "selfdrive.updated.updated", only_offroad, enabled=not PC),
  #PythonProcess("uploader", "system.loggerd.uploader", always_run),
  PythonProcess("statsd", "selfdrive.statsd", always_run),

  #custom
  PythonProcess("navi_mappy", "selfdrive.custom.navi.navi_mappy", only_onroad, enabled =  (ExternalNaviType()==1) ),     # mappy
  PythonProcess("navi_controller", "selfdrive.custom.navi.navi_controller", only_onroad, enabled = (ExternalNaviType()==2) ), # NDA
  PythonProcess("navi_route", "selfdrive.custom.navi.navi_route", only_onroad, enabled= UseExternalNaviRoutes() ),


  # debug procs
  NativeProcess("bridge", "cereal/messaging", ["./bridge"], notcar),
  PythonProcess("webrtcd", "system.webrtc.webrtcd", notcar),
  PythonProcess("webjoystick", "tools.bodyteleop.web", notcar),
]

managed_processes = {p.name: p for p in procs}
