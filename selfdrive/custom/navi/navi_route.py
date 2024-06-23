#!/usr/bin/env python3
import threading


import cereal.messaging as messaging
from cereal import log
from openpilot.common.realtime import Ratekeeper
from openpilot.common.swaglog import cloudlog

REROUTE_DISTANCE = 25
MANEUVER_TRANSITION_THRESHOLD = 10
REROUTE_COUNTER_MIN = 3


class RouteEngine:
  def __init__(self, sm, pm):
    self.sm = sm
    self.pm = pm



    self.route = None
    self.route_geometry = None


    self.ui_pid = None


     

  def update(self):
    self.sm.update(0)

    if self.sm.updated["managerState"]:
      ui_pid = [p.pid for p in self.sm["managerState"].processes if p.name == "ui" and p.running]
      if ui_pid:
        if self.ui_pid and self.ui_pid != ui_pid[0]:
          cloudlog.warning("UI restarting, sending route")
          threading.Timer(5.0, self.send_route).start()
        self.ui_pid = ui_pid[0]
    try:
      self.send_instruction()
    except Exception:
      cloudlog.exception("navd.failed_to_compute")



  def send_instruction(self):
    msg = messaging.new_message('navInstruction', valid=True)
    
    naviData = self.sm["naviCustom"].naviData
    if naviData.active:
      if naviData.camLimitSpeed:
        msg.navInstruction.speedLimit = naviData.camLimitSpeed / 3.6
        msg.navInstruction.speedLimitSign = log.NavInstruction.SpeedLimitSign.vienna        
      elif naviData.roadLimitSpeed:
        msg.navInstruction.speedLimit = naviData.roadLimitSpeed / 3.6
        msg.navInstruction.speedLimitSign = log.NavInstruction.SpeedLimitSign.mutcd
    else:
      naviData = None
      msg.valid = False
      self.pm.send('navInstruction', msg)
      return

    # Current instruction
    msg.navInstruction.maneuverDistance = 0

    # All instructions
    maneuvers = []
    msg.navInstruction.allManeuvers = maneuvers

    # Compute total remaining time and distance
    # Add up totals for future steps
    msg.navInstruction.distanceRemaining = 0
    msg.navInstruction.timeRemaining = 0
    msg.navInstruction.timeRemainingTypical = 0

    # Speed limit
    if naviData is not None:
      pass

    self.pm.send('navInstruction', msg)


  def send_route(self):
    coords = []

    if self.route is not None:
      for path in self.route_geometry:
        coords += [c.as_dict() for c in path]

    msg = messaging.new_message('navRoute', valid=True)
    msg.navRoute.coordinates = coords
    self.pm.send('navRoute', msg)



def main():
  pm = messaging.PubMaster(['navInstruction', 'navRoute'])
  sm = messaging.SubMaster(['liveLocationKalman', 'managerState','naviCustom'])

  rk = Ratekeeper(1.0)
  route_engine = RouteEngine(sm, pm)
  while True:
    route_engine.update()
    rk.keep_time()


if __name__ == "__main__":
  main()
