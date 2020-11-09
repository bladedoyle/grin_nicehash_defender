#!/usr/bin/env python
  
# Copyright 2020 Blade M. Doyle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import sys
import uuid
import time
import json
import requests
import traceback
from datetime import datetime, timedelta

import hashlib
import hmac
import base64


## NiceHash settings - https://docs.nicehash.com/main/index.html
UPDATE_INTERVAL = timedelta(minutes = 10)
MAX_DECREASE = 0.0001


## --

class NiceHash():
    def __init__(self, API_ID=None, API_KEY=None, market="EU"):
        self.API_ID = API_ID
        self.API_KEY = API_KEY
        self.market = market
        self.algo = "GRINCUCKATOO32"

    def setAuth(self):
        if self.API_ID is None or self.API_KEY is None:
            try:
                # From environment
                self.API_ID = os.environ["NICEHASH_API_ID"]
                self.API_KEY = os.environ["NICEHASH_API_KEY"]
            except Exception as e:
                raise Exception("Failed to find NiceHash auth in config or environment")


    def call_nicehash_api(self, path, method, args=None, body=None):
        url = "https://api2.nicehash.com"
        zero_byte_field = "\x00"

        timestamp = str(int(time.time() * 1000 ))
        nonce = str(uuid.uuid4())
        request_query_str = url + path
        body_str = json.dumps(body)

        req = "ts=" + str(timestamp)
        if args is not None:
            for arg, val in args.items():
                req += "&{}={}".format(arg, val)
        elif body is not None:
            for arg, val in body.items():
                req += "&{}={}".format(arg, val)
        else:
            raise Exception("Must specify either args or body")
        request_query_str += "?" + req
        
        secret_bytes = bytearray(self.API_KEY, 'ISO-8859-1')

        message = self.API_ID + \
                  zero_byte_field + \
                  timestamp + \
                  zero_byte_field + \
                  nonce + \
                  zero_byte_field + \
                  zero_byte_field + \
                  zero_byte_field + \
                  zero_byte_field + \
                  method + \
                  zero_byte_field + \
                  path + \
                  zero_byte_field + \
                  req
        if body is not None:
            message += \
                  zero_byte_field + \
                  body_str

        message_bytes = bytearray(message, 'ISO-8859-1')

        signature = hmac.new(secret_bytes, msg = message_bytes, digestmod = hashlib.sha256).hexdigest()

        headers = {
            'Content-type': 'application/json',
            "X-Time": timestamp,
            "X-Nonce": nonce,
            "X-Auth": self.API_ID + ":" + signature,
        }

        if method == "GET":
            r = requests.get(
                    url=request_query_str,
                    headers=headers,
                )
        elif method == "POST":
    #        print("xxx: {}".format(request_query_str))
    #        print("yyy: {}".format(body_str))
            r = requests.post(
                    url=request_query_str,
                    headers=headers,
                    data=body_str,
                )
        else:
            raise Exception("Unsupported method: {}".format(method))
        
        if r.status_code >= 300 or r.status_code < 200:
            error_msg = "Error calling {}.  Code: {} Reason: {}".format(url, r.status_code, r.reason)
            raise Exception(error_msg)

        r_json = r.json()
        if "error_id" in r_json:
            message = r_json["errors"]["message"]
            method = r_json["method"]
            error_msg = "Error calling {}. Reason: {}".format(method, message)
            raise Exception(error_msg)
        #print("xxx {}".format(r_json))
        return r_json

    def getCurrentPrice(self):
        # Find the lowest price thats has miners working
        getOrderBook_path = "/main/api/v2/hashpower/orderBook/"
        getOrderBook_args = {
                "algorithm": self.algo,
                "page": "0",
                "size": "1000",
            }
        try:
            result = self.call_nicehash_api(
                    path = getOrderBook_path,
                    args = getOrderBook_args,
                    method = "GET",
                )
            data = result["stats"][self.market]
            prices = [o["price"] for o in data["orders"] if int(o["rigsCount"]) > 0 and float(o["acceptedSpeed"]) > 0.00000005 and o["type"] == "STANDARD"]
            prices = sorted(prices)
            return float(prices[0])
        except Exception as e:
            print("failed: {}".format(e))
            raise

    def getCurrentSpeed(self):
        # Find the current Total Available Speed
        getOrderBook_path = "/main/api/v2/hashpower/orderBook/"
        getOrderBook_args = {
                "algorithm": self.algo,
                "page": "0",
                "size": "1",
            }
        try:
            result = self.call_nicehash_api(
                    path = getOrderBook_path,
                    args = getOrderBook_args,
                    method = "GET",
                )
            data = result["stats"][self.market]
            speed = data["totalSpeed"]
            return float(speed)
        except Exception as e:
            print("failed: {}".format(e))
            raise






def main():
    # Some Tests
    nh_api = NiceHash()
    nh_api.setAuth()
    p = nh_api.getCurrentPrice() 
    print("Current Price: {}".format(p))
    s = nh_api.getCurrentSpeed()
    print("Current Speed: {}".format(s))
 

if __name__ == "__main__":
    main()
