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
from threading import Thread

from nicehash_api import NiceHash


## Begin User Config

# Basic Config
VERBOSE = True    # Print lots of data
MAX_SPEED = 1.0   # kG/s
MAX_PRICE = 0.270 # BTC/kG/day

MIN_HISTORY = 1  # (minutes) Minimum amount of data to collect before taking action

# Advanced Config
LOOP_INTERVAL = 10      # Sleep this long (seconds) between control loop runs
MAX_INCREASE = 0.0001   # Maximum amount to increase at once
INCREASE_INTERVAL = timedelta(seconds = 0)  # Min time between price increases
TARGET_MIN_ADD = 0.0005 # Amount to set order price over the absolute minimum
## End User Config

# https://docs.nicehash.com/main/index.html
UPDATE_INTERVAL = timedelta(minutes = 10)
MAX_DECREASE = 0.0001


##
# Watchers for external data

class GrinHashSpeedWatcher():
    def __init__(self):
        self.interval = 30
        self.max_size = 9000/self.interval
        self.speeds = []

    def getSize(self):
        return len(self.speeds)
    
    def getCurrentSpeed(self):
        return self.speeds[-1]["speed"]

    def getAverageSpeed(self):
        total = sum([sp["speed"] for sp in self.speeds])
        return total / len(self.speeds)

    def run(self):
        while True:
            # Get grin GPS (from GrinMint Pool API)
            url = "https://api.grinmint.com/v2/networkStats"
            r = requests.get(url, timeout=20)
            speedpoint = { 
                    "speed": r.json()["hashrates"]["32"],
                    "ts": datetime.now(),
                }
            self.speeds.append(speedpoint)
            if len(self.speeds) > self.max_size:
                self.speeds.pop(0)
            # sleep interval
            time.sleep(self.interval)

class GrinPriceWatcher():
    def __init__(self):
        self.interval = 30
        self.max_size = 9000/self.interval
        self.prices = []
    
    def getSize(self):
        return len(self.prices)
    
    def getCurrentPrice(self):
        return self.prices[-1]["price"]

    def getAveragePrice(self):
        total = sum([pp["price"] for pp in self.prices])
        return total / len(self.prices)

    def run(self):
        while True:
            # Get grin price
            url = "https://api.coingecko.com/api/v3/simple/price?ids=grin&vs_currencies=btc"
            r = requests.get(url, timeout=20)
            pricepoint = { 
                    "price": r.json()["grin"]["btc"],
                    "ts": datetime.now(),
                }
            self.prices.append(pricepoint)
            if len(self.prices) > self.max_size:
                self.prices.pop(0)
            # sleep interval
            time.sleep(self.interval)

class NiceHashPriceWatcher():
    def __init__(self):
        self.interval = 30
        self.max_size = 9000/self.interval
        self.prices = []

    def getSize(self):
        return len(self.prices)
    
    def getCurrentPrice(self):
        return self.prices[-1]["price"]

    def getAveragePrice(self):
        total = sum([pp["price"] for pp in self.prices])
        return total / len(self.prices)

    def run(self):
        nh_api = NiceHash()
        nh_api.setAuth()
        while True:
            # Get NH C32 price
            price = nh_api.getCurrentPrice()
            pricepoint = {
                    "price": price,
                    "ts": datetime.now(),
                }
            self.prices.append(pricepoint)
            if len(self.prices) > self.max_size:
                self.prices.pop(0)
            # sleep interval
            time.sleep(self.interval)

class NiceHashSpeedWatcher():
    def __init__(self):
        self.interval = 30
        self.max_size = 9000/self.interval
        self.speeds = []

    def getSize(self):
        return len(self.speeds)

    def getCurrentSpeed(self):
        return self.speeds[-1]["speed"]

    def getAverageSpeed(self):
        total = sum([sp["speed"] for sp in self.speeds])
        return total / len(self.speeds)

    def run(self):
        nh_api = NiceHash()
        nh_api.setAuth()
        while True:
            # Get NH C32 speed
            speed = nh_api.getCurrentSpeed()
            speedpoint = {
                    "speed": speed,
                    "ts": datetime.now(),
                }
            self.speeds.append(speedpoint)
            if len(self.speeds) > self.max_size:
                self.speeds.pop(0)
            # sleep interval
            time.sleep(self.interval)





class GrinNiceHashDefender():
    def __init__(self):
        self.nicehash_auth = {"API_ID": None, "API_KEY": None}
        self.config = {
                "MAX_SPEED": MAX_SPEED,
                "MAX_PRICE": MAX_PRICE,
                "LOOP_INTERVAL": LOOP_INTERVAL,
                "MAX_INCREASE": MAX_INCREASE,
                "INCREASE_INTERVAL": INCREASE_INTERVAL,
                "TARGET_MIN_ADD": TARGET_MIN_ADD,
                "UPDATE_INTERVAL": UPDATE_INTERVAL,
                "MAX_DECREASE": MAX_DECREASE,
            }
        self.orders = {}
        self.attacks_detected = 0
        self.grin_price = None
        self.grin_speed = None
        self.nh_price = None
        self.nh_speed = None


    def getProfitabilityPrice(self):
        grin_price = self.grin_price.getCurrentPrice()
        grin_speed = self.grin_speed.getCurrentSpeed() / 1000.0
        grin_per_day = 60*60*24
        price = (grin_per_day * grin_price) / grin_speed
        return price
        

    def checkForAttack(self):
        # Possible to attack if:
        # 1. NiceHash C32 price is at least 30% higher than recent average
        # 2. NiceHash C32 "Total Available Speed" is at least 30% higher than recent average
        # 3. NiceHash C32 price is at least 30% higher than is profitable
        #    based on current grin price and current grin network c32 graph rate
        nh_price = self.nh_price.getCurrentPrice()
        nh_avg_price = self.nh_price.getAveragePrice()
        nh_price_dev = nh_price / nh_avg_price
        
        nh_speed = self.nh_speed.getCurrentSpeed()
        nh_avg_speed = self.nh_speed.getAverageSpeed()
        nh_speed_dev = nh_speed / nh_avg_speed

        grin_profitability_price = self.getProfitabilityPrice()
        grin_profitability = nh_price / grin_profitability_price

        print("checkForAttack:")
        print("  Num Attack Detections: {}".format(self.attacks_detected))
        print("  nh_price_dev: {}".format(nh_price_dev))
        print("  nh_speed_dev: {}".format(nh_speed_dev))
        print("  grin_profitability: {}".format(grin_profitability))
        if nh_price_dev > 1.3 and nh_speed_dev > 1.3 and grin_profitability > 1.3:
            print("XXXXXXXXXXXXXX: Possible Attack")
            self.attacks_detected = self.attacks_detected + 1
        else:
            print("  No attack detected at this time")

        

    def run(self):
        # Start grin price watcher thread
        self.grin_price = GrinPriceWatcher()
        grin_price_thread = Thread(target = self.grin_price.run)
        grin_price_thread.daemon = True
        grin_price_thread.start()

        # Start the NiceHash price watcher thread
        self.nh_price = NiceHashPriceWatcher()
        nh_price_thread = Thread(target = self.nh_price.run)
        nh_price_thread.daemon = True
        nh_price_thread.start()

        # Start the NiceHash speed watcher thread
        self.nh_speed = NiceHashSpeedWatcher()
        nh_speed_thread = Thread(target = self.nh_speed.run)
        nh_speed_thread.daemon = True
        nh_speed_thread.start()

        # Start the grin network gps watcher thread
        self.grin_speed = GrinHashSpeedWatcher()
        grin_speed_thread = Thread(target = self.grin_speed.run)
        grin_speed_thread.daemon = True
        grin_speed_thread.start()

        print("self.nicehash_auth = {}".format(self.nicehash_auth))
        print("self.config = {}".format(self.config))

        while self.grin_price.getSize() < MIN_HISTORY:
            print("Waiting for history: {} of {}".format(self.grin_price.getSize(), MIN_HISTORY))
            time.sleep(20)

        while True:
            if VERBOSE:
                print("Time:")
                print("  Current: {}".format(datetime.now()))
                print("Grin Price:")
                print("  Current: {}".format(self.grin_price.getCurrentPrice()))
                print("  Avg: {}".format(self.grin_price.getAveragePrice()))
                print("  Dev: {}".format(self.grin_price.getCurrentPrice()/self.grin_price.getAveragePrice()))
                print("NiceHash Price:")
                print("  Current: {}".format(self.nh_price.getCurrentPrice()))
                print("  Avg: {}".format(self.nh_price.getAveragePrice()))
                print("  Dev: {}".format(self.nh_price.getCurrentPrice()/self.nh_price.getAveragePrice()))
                print("NiceHash Speed:")
                print("  Current: {}".format(self.nh_speed.getCurrentSpeed()))
                print("  Avg: {}".format(self.nh_speed.getAverageSpeed()))
                print("  Dev: {}".format(self.nh_speed.getCurrentSpeed()/self.nh_speed.getAverageSpeed()))
                print("Grin Speed:")
                print("  Current: {}".format(self.grin_speed.getCurrentSpeed()))
                print("  Avg: {}".format(self.grin_speed.getAverageSpeed()))
                print("  Dev: {}".format(self.grin_speed.getCurrentSpeed()/self.grin_speed.getAverageSpeed()))
                print("Profitability Limit:")
                print("  Current: {}".format(self.getProfitabilityPrice()))
                print("  Dev: {}".format(self.nh_price.getCurrentPrice()/self.getProfitabilityPrice()))
                print("\n")
            self.checkForAttack()
            print("\n\n\n")
            time.sleep(30)


def main():
    defender = GrinNiceHashDefender()
    defender.run()

 

if __name__ == "__main__":
    main()
