# coding: utf-8

import sys
import ConfigParser
import signal
import time
import httplib
import json
import picamera
import pygame.mixer
import RPi.GPIO as GPIO
from datetime import datetime
from gcloud import storage
from gcloud.storage import Blob

configfile = ConfigParser.SafeConfigParser()
configfile.read("./config/config.ini")

UPLOAD_BUCKET = configfile.get("gcs","upload_bucket") 
PROJECT_ID = configfile.get("gcs","project_id")
UPLOAD_FILE = configfile.get("gcs","upload_file")
OUTPUT_FILE = configfile.get("gcs","output_file")

SENSOR_PIN = int(configfile.get("sensor","pin"))
INTERVAL = float(configfile.get("sensor","interval"))
SHUTTER_DISTANCE_MIN = int(configfile.get("sensor","shutter_distance_min"))
SHUTTER_DISTANCE_MAX = int(configfile.get("sensor","shutter_distance_max"))

VERTICAL = int(configfile.get("camera","vertical"))
HORIZONTAL = int(configfile.get("camera","horizontal"))
BRIGHTNESS = int(configfile.get("camera","brightness"))
CONTRAST = int(configfile.get("camera","contrast"))
SHARPNESS = int(configfile.get("camera","sharpness"))

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

    def __init__(self,pin):
        self.pin = pin
    
    def readValue(self):
        now = 0
        GPIO.setup(self.pin, GPIO.OUT)   # 出力指定
        GPIO.output(self.pin, 0)   # ピンの出力を0Vにする
        usleep(2)
        GPIO.output(self.pin, 1)   # ピンの出力を3.3Vにする
        usleep(5)
        GPIO.output(self.pin, 0)   # ピンの出力を0Vにする
        now = datetime.now()
        # ピンの電圧状態読み取る
        GPIO.setup(self.pin, GPIO.IN)  # 入力指定
        while GPIO.input(self.pin) == 0:
            continue
        start = time.time()
        cnt = 0
        while GPIO.input(self.pin) == 1:
            # cnt = cnt + 1
            continue
        end = time.time()
        distance = ((end - start) * 1000000) / 29 / 2
        distance = distance > 400 and 400 or distance  # 最大距離
        distance_val = int(round(distance, 0))
#        print "cnt %s  distance  %.3f cm" % (cnt, distance)

        now_jst = now.strftime("%Y-%m-%d %H:%M:%S.%f")
        now_unixtime = now.strftime("%s.%f")

        value = {
          "type": "sensor_data",
          "attributes": {
            "jst": now_jst,
            "time": now_unixtime,
            "distance": distance_val
          }
        }
        return value

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

client = storage.Client(project=PROJECT_ID)
bucket = client.get_bucket(UPLOAD_BUCKET)


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
    sensor = Sensor_SEN136B5B(SENSOR_PIN)
    led = Redled(21)
    GPIO.setup(18, GPIO.IN)
    GPIO.add_event_detect(18, GPIO.RISING, callback=myCallBack, bouncetime=200)

    with picamera.PiCamera() as camera:
        camera.resolution = (VERTICAL, HORIZONTAL)
        camera.brightness = BRIGHTNESS
        camera.contrast = CONTRAST
        camera.sharpness = SHARPNESS
        camera.start_preview()

        while True:
            print flag
            if flag == 1:
                value = sensor.readValue()
                led.ledctl('on',1,0)
                distance = int(value['attributes']['distance'])
                print distance
                ## ある範囲に入ったら
                if SHUTTER_DISTANCE_MIN <= distance <= SHUTTER_DISTANCE_MAX:
                    # LED 点滅
                    led.ledctl('blink2',3,0.25)
                    led.ledctl('blink1',3,0.25)
                    pygame.mixer.init()
                    pygame.mixer.music.load('sound/meka_ge_cam08.mp3')
                    pygame.mixer.music.play(1) # loop count
                    camera.capture(UPLOAD_FILE)
                    time.sleep(1)   
                    pygame.mixer.music.stop()  #停止
                    led.ledctl('off',3,0)
                    print "ok  %d <=  %d  <= %d" % (SHUTTER_DISTANCE_MIN,distance,SHUTTER_DISTANCE_MAX)
                    outputfile = OUTPUT_FILE + datetime.now().strftime("%Y%m%d%H%M%S%f") + ".jpg"
                    print outputfile
                    time.sleep(5)     
                    blob = Blob(outputfile, bucket)
                    with open(UPLOAD_FILE, 'rb') as my_file:
                        blob.upload_from_file(my_file)
            else:
                led.ledctl('off',3,0)
                    

            time.sleep(INTERVAL)

except KeyboardInterrupt:
    print "keyboardInterrupt"
finally:
    GPIO.cleanup()
