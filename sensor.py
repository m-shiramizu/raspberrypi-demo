# coding: utf-8

import sys
import signal
import ConfigParser
import time
import httplib
import json
import RPi.GPIO as GPIO
from datetime import datetime

configfile = ConfigParser.SafeConfigParser()
configfile.read("./config/sensor.ini")

SUBDOMAIN = configfile.get("iot_board","subdomain")  
API_TOKEN = configfile.get("iot_board","api_token")  # APIトークン
SENSOR_PIN = int(configfile.get("sensor","pin"))  # センサーのGPIO番号
INTERVAL = float(configfile.get("sensor","interval"))  # 測定間隔（秒）

# マイクロ秒sleep
usleep = lambda x: time.sleep(x / 1000000.0)



def signalhandler(num, frame):
    """
    UNIXシグナルのハンドラ
    引数は2つ・番号とフレームオブジェクト
    """
    print 'func(): %d, %s' % (num, str(frame))  # ここではSIGINTの数値がnumに入る
    sys.exit()

signal.signal(signal.SIGINT, signalhandler)
# GPIO指定をGPIO番号で行う
GPIO.setmode(GPIO.BCM)

class Sensor_SEN136B5B:
    """ 
    センサー  
    """

    def readValue(self):
        # GPIO指定をGPIO番号で行う
        GPIO.setmode(GPIO.BCM)
        now = 0
        GPIO.setup(SENSOR_PIN, GPIO.OUT)   # 出力指定
        GPIO.output(SENSOR_PIN, 0)   # ピンの出力を0Vにする
        usleep(2)
        GPIO.output(SENSOR_PIN, 1)   # ピンの出力を3.3Vにする
        usleep(5)
        GPIO.output(SENSOR_PIN, 0)   # ピンの出力を0Vにする

        now = datetime.now()

        # ピンの電圧状態読み取る
        GPIO.setup(SENSOR_PIN, GPIO.IN)  # 入力指定
        while GPIO.input(SENSOR_PIN) == 0:
            continue
        start = time.time()

        while GPIO.input(SENSOR_PIN) == 1:
            continue
        end = time.time()

        distance = ((end - start) * 1000000) / 29 / 2
        distance = distance > 400 and 400 or distance  # 最大距離
        distance_val = int(round(distance, 0))
#        print "cnt %s  distance  %.3f cm" % (cnt, distance)

        now_jst = now.strftime("%Y-%m-%d %H:%M:%S.%f")
        now_unixtime = now.strftime("%s.%f")

        logs = [
            {
                "type": "sensor_data",
                "attributes": {
                    "jst": now_jst,
                    "time": now_unixtime,
                    "distance": distance_val
                }
            }
        ]
        return logs

    # IotボードへへのPOST
    def registToKintone(self, subdomain, logs, apiToken):
        request = {"api_token": apiToken, "logs": logs}
        requestJson = json.dumps(request)
        headers = {"Content-Type": "application/json"}

        try:
            connect = httplib.HTTPSConnection(subdomain + ":443")
            connect.request("POST", "", requestJson, headers)
            response = connect.getresponse()
            print response
            return response
        except Exception as e:
            print(e)
            return None

class Redled:
  """
  LED
  """

  # LED点滅パターン

  ledPat = {
    "on":     (1, 1, 1, 1),
    "off":    (0, 0, 0, 0),
    "blink1": (0, 1, 0, 1),
    "blink2": (0, 0, 0, 1)
  }

  def __init__(self,pin):
      self.pin = pin
      
  def ledctl(self,led_pattern,times,wait_time):
      GPIO.setup(self.pin, GPIO.OUT)
      for var in range(0, times):
          for num in range(0, len(self.ledPat)):
              GPIO.output(self.pin, self.ledPat[led_pattern][num])
              if wait_time != 0: time.sleep(wait_time)


# high
def myCallBack(channel):
    global flag
    if channel == 18:
        if flag == 0:
            flag = 1
            print "on %s" % flag
        else:
            flag = 0
            print "off %s" % flag

try:
    flag = 0
    sensor = Sensor_SEN136B5B()
    led = Redled(21)
    GPIO.setup(18, GPIO.IN)
    GPIO.add_event_detect(18, GPIO.RISING, callback=myCallBack, bouncetime=200)
    while True:
        values = sensor.readValue()
#        print flag
        if flag == 1:
            led.ledctl('on',1,0)
            resp = sensor.registToKintone(SUBDOMAIN, values, API_TOKEN)
            print "post: %s distance: %s cm" % (resp.reason, values[0]['attributes']['distance'])
        else:
            led.ledctl('off',3,0)
            print "distance: %s cm" % (values[0]['attributes']['distance'])
        time.sleep(INTERVAL)
except KeyboardInterrupt:
    print "keyboardInterrupt"

finally:
    GPIO.cleanup()
