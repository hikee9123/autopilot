#!/usr/bin/env python3
import json
import os
import time

import select
import subprocess
import threading
import time
import socket
import fcntl
import struct
from threading import Thread
from cereal import messaging
from openpilot.common.realtime import Ratekeeper
import time

CAMERA_SPEED_FACTOR = 1.05


class Port:
  BROADCAST_PORT = 2899
  RECEIVE_PORT = 2843
  LOCATION_PORT = BROADCAST_PORT


class NaviServer:
  def __init__(self):
    self.json_road_limit = None
    self.active = 0
    self.last_updated = 0
    self.last_updated_active = 0
    self.last_exception = None
    self.lock = threading.Lock()
    self.remote_addr = None

    self.remote_gps_addr = None
    self.last_time_location = 0

    broadcast = Thread(target=self.broadcast_thread, args=[])
    broadcast.daemon = True
    broadcast.start()


    self.gps_sm = messaging.SubMaster(['gpsLocationExternal'])
    self.gps_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    self.location = None

    self.gps_event = threading.Event()
    gps_thread = Thread(target=self.gps_thread, args=[])
    gps_thread.daemon = True
    gps_thread.start()

  def gps_thread(self):
    rk = Ratekeeper(3.0, print_delay_threshold=None)
    while True:
      self.gps_timer()
      rk.keep_time()

  def gps_timer(self):
    try:
      if self.remote_gps_addr is not None:
        self.gps_sm.update(0)
        if self.gps_sm.updated['gpsLocationExternal']:
          self.location = self.gps_sm['gpsLocationExternal']

        if self.location is not None:
          json_location = json.dumps({"location": [
            self.location.latitude,
            self.location.longitude,
            self.location.altitude,
            self.location.speed,
            self.location.bearingDeg,
            self.location.accuracy,
            self.location.unixTimestampMillis,
            # self.location.source,
            # self.location.vNED,
            self.location.verticalAccuracy,
            self.location.bearingAccuracyDeg,
            self.location.speedAccuracy,
          ]})

          address = (self.remote_gps_addr[0], Port.LOCATION_PORT)
          self.gps_socket.sendto(json_location.encode(), address)

    except:
      self.remote_gps_addr = None

  def get_broadcast_address(self):
    try:
      with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        ip = fcntl.ioctl(
          s.fileno(),
          0x8919,
          struct.pack('256s', 'wlan0'.encode('utf-8'))
        )[20:24]
        return socket.inet_ntoa(ip)
    except:
      return None

  """
  def broadcast_thread(self):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
      try:        
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
          try:
            broadcast_address = '255.255.255.255'
            message = 'EON:ROAD_LIMIT_SERVICE:v1'
            address = (broadcast_address, Port.BROADCAST_PORT)
            rt = sock.sendto(message.encode('utf-8'), address )
            print(f"Send : {rt} = {message} {address}") 

          except Exception as e:
            print(f"Send error occurred: {e}")


          self.frame += 1
          time.sleep(5.)
      except Exception as e:
        print(f"socket error occurred: {e}")  
  """




  def broadcast_thread(self):
    broadcast_address = None
    frame = 0

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
      try:
        #sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:

          try:

            if broadcast_address is None or frame % 10 == 0:
              broadcast_address = self.get_broadcast_address()

            if broadcast_address is not None and self.remote_addr is None:
              print('broadcast', broadcast_address)

              msg = 'EON:ROAD_LIMIT_SERVICE:v1'.encode()
              for i in range(1, 255):
                ip_tuple = socket.inet_aton(broadcast_address)
                new_ip = ip_tuple[:-1] + bytes([i])
                address = (socket.inet_ntoa(new_ip), Port.BROADCAST_PORT)
                sock.sendto(msg, address)
          except:
            pass

          time.sleep(5.)
          frame += 1

      except:
        pass


  def send_sdp(self, sock):
    try:
      sock.sendto('EON:ROAD_LIMIT_SERVICE:v1'.encode(), (self.remote_addr[0], Port.BROADCAST_PORT))
    except:
      pass

  def udp_recv(self, sock):
    ret = False
    try:
      ready = select.select([sock], [], [], 1.)
      ret = bool(ready[0])
      if ret:
        data, self.remote_addr = sock.recvfrom(2048)
        json_obj = json.loads(data.decode())
        
        #print(f"udp_recv={json_obj}")
        if 'cmd' in json_obj:
          try:
            os.system(json_obj['cmd'])
            ret = False
          except:
            pass

        if 'request_gps' in json_obj:
          try:
            if json_obj['request_gps'] == 1:
              self.remote_gps_addr = self.remote_addr
            else:
              self.remote_gps_addr = None
            ret = False
          except:
            pass

        if 'echo' in json_obj:
          try:
            echo = json.dumps(json_obj["echo"])
            sock.sendto(echo.encode(), (self.remote_addr[0], Port.BROADCAST_PORT))
            ret = False
          except:
            pass

        if 'echo_cmd' in json_obj:
          try:
            result = subprocess.run(json_obj['echo_cmd'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            echo = json.dumps({"echo_cmd": json_obj['echo_cmd'], "result": result.stdout})
            sock.sendto(echo.encode(), (self.remote_addr[0], Port.BROADCAST_PORT))
            ret = False
          except:
            pass

        try:
          self.lock.acquire()
          try:
            if 'active' in json_obj:
              self.active = json_obj['active']
              self.last_updated_active = time.monotonic()
          except:
            pass

          if 'road_limit' in json_obj:
            self.json_road_limit = json_obj['road_limit']
            self.last_updated = time.monotonic()

        finally:
          self.lock.release()

    except:

      try:
        self.lock.acquire()
        self.json_road_limit = None
      finally:
        self.lock.release()

    return ret

  def check(self):
    now = time.monotonic()
    if now - self.last_updated > 6.:
      try:
        self.lock.acquire()
        self.json_road_limit = None
      finally:
        self.lock.release()

    if now - self.last_updated_active > 6.:
      self.active = 0
      self.remote_addr = None

  def get_limit_val(self, key, default=None):
    return self.get_json_val(self.json_road_limit, key, default)

  def get_json_val(self, json, key, default=None):

    try:
      if json is None:
        return default

      if key in json:
        return json[key]

    except:
      pass

    return default


def main():

  pm = messaging.PubMaster(['naviCustom']) 

  server = NaviServer() 
  with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    try:
      sock.bind(('0.0.0.0', Port.RECEIVE_PORT))
      sock.setblocking(False)

      test_dist = 0
      while True:
        server.udp_recv(sock)

        dat = messaging.new_message('naviCustom')
        dat.naviCustom.naviData = {
          "active": server.active,
          "roadLimitSpeed": server.get_limit_val("road_limit_speed", 0),
          "isHighway": server.get_limit_val("is_highway", False),
          "camType": server.get_limit_val("cam_type", 0),
          "camLimitSpeedLeftDist": server.get_limit_val("cam_limit_speed_left_dist", 0),
          "camLimitSpeed": server.get_limit_val("cam_limit_speed", 0),
          "sectionLimitSpeed": server.get_limit_val("section_limit_speed", 0),
          "sectionLeftDist": server.get_limit_val("section_left_dist", 0),
          "sectionAvgSpeed": server.get_limit_val("section_avg_speed", 0),
          "sectionLeftTime": server.get_limit_val("section_left_time", 0),
          "sectionAdjustSpeed": server.get_limit_val("section_adjust_speed", False),
          "camSpeedFactor": server.get_limit_val("cam_speed_factor", CAMERA_SPEED_FACTOR),
          "currentRoadName": server.get_limit_val("current_road_name", ""),
          "isNda2": server.get_limit_val("is_nda2", False),
          "cntIdx": test_dist,
        }

        pm.send('naviCustom', dat )

        test_dist += 1
        if test_dist >= 10:
          test_dist = 0


        server.send_sdp(sock)
        server.check()

        #time.sleep(0.1)
    except Exception as e:
      server.last_exception = e





if __name__ == "__main__":
  main()
