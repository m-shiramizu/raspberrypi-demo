# coding: utf-8

import signal
import sys
import time
import httplib
import json
import random

from datetime import datetime

param = sys.argv

INTERVAL = float(param[3])  # 測定間隔（秒）

SUBDOMAIN = param[1]  # URL
API_TOKEN = param[2]  # APIトークン


def signalhandler(num, frame):
    """
    UNIXシグナルのハンドラ
    引数は2つ・番号とフレームオブジェクト
    """
    print 'func(): %d, %s' % (num, str(frame))  # ここではSIGINTの数値がnumに入る
    sys.exit()


signal.signal(signal.SIGINT, signalhandler)


class Sensor:
    """ センサー  """
    # センサーの値読出し

    def readValue(self):
        now = datetime.now()
        now_jst = now.strftime("%Y-%m-%d %H:%M:%S.%f")
        now_unixtime = now.strftime("%s.%f")
        distance_val = int(random.randint(0, 50))
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

sensor = Sensor()

while True:
    values = sensor.readValue()
    print values
    resp = sensor.registToKintone(SUBDOMAIN, values, API_TOKEN)
    print "status : %s msg : %s reason : %s " % (resp.status, resp.msg, resp.reason)
    time.sleep(INTERVAL)
