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

##
# Watchers for external data

class GrinHashSpeedWatcher():
    def __init__(self, max_history=1440):
        self.interval = 60
        self.max_size = max_history
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
            try:
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
            except Exception as e:
                print("Error in Grin51::GrinHashSpeedWatcher - {}".format(e))
            # sleep interval
            time.sleep(self.interval)

class GrinPriceWatcher():
    def __init__(self, max_history=1440):
        self.interval = 60
        self.max_size = max_history
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
            try:
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
            except Exception as e:
                print("Error in Grin51::GrinPriceWatcher - {}".format(e))
            # sleep interval
            time.sleep(self.interval)

class NiceHashPriceWatcher():
    def __init__(self, market, algo, max_history=1440):
        self.market = market
        self.algo = algo
        self.interval = 60
        self.max_size = max_history
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
        while True:
            try:
                # Get NH price
                price = nh_api.getCurrentPrice(self.market, self.algo)
                pricepoint = {
                        "price": price,
                        "ts": datetime.now(),
                    }
                self.prices.append(pricepoint)
                if len(self.prices) > self.max_size:
                    self.prices.pop(0)
            except Exception as e:
                print("Error in Grin51::NiceHashPriceWatcher - {}".format(e))
            # sleep interval
            time.sleep(self.interval)

class NiceHashSpeedWatcher():
    def __init__(self, market, algo, max_history=1440):
        self.market = market
        self.algo = algo
        self.interval = 60
        self.max_size = max_history
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
        while True:
            try:
                # Get NH speed
                speed = nh_api.getCurrentSpeed(self.market, self.algo)
                speedpoint = {
                        "speed": speed,
                        "ts": datetime.now(),
                    }
                self.speeds.append(speedpoint)
                if len(self.speeds) > self.max_size:
                    self.speeds.pop(0)
            except Exception as e:
                print("Error in Grin51::NiceHashSpeedWatcher - {}".format(e))
            # sleep interval
            time.sleep(self.interval)



class Grin51():
    def __init__(self, threashold, min_history=30, max_history=1440):
        self.nh_api = NiceHash()
        self.threashold = threashold
        self.min_history = min_history
        self.max_history = max_history
        self.under_attack = False

    # Attempt at calculating the break-eaven nicehash rental price
    def getBreakevenPrice(self):
        grin_price = self.grin_price.getCurrentPrice()
        grin_speed = self.grin_speed.getCurrentSpeed() / 1000.0 # XXX NH specific - only valid for C32
        grin_per_day = 60*60*24
        price = (grin_per_day * grin_price) / grin_speed
        return price
        
    def get_stats(self):
        nh_eu_price = self.nh_eu_price.getCurrentPrice()
        nh_eu_price_avg = self.nh_eu_price.getAveragePrice()
        nh_eu_price_dev = nh_eu_price / nh_eu_price_avg
        #
        nh_us_price = self.nh_us_price.getCurrentPrice()
        nh_us_price_avg = self.nh_us_price.getAveragePrice()
        nh_us_price_dev = nh_us_price / nh_us_price_avg
        #
        nh_price = (nh_eu_price + nh_us_price) / 2
        nh_price_score = (nh_eu_price_dev + nh_us_price_dev) / 2
        #
        nh_eu_speed = self.nh_eu_speed.getCurrentSpeed()
        nh_eu_speed_avg = self.nh_eu_speed.getAverageSpeed()
        nh_eu_speed_dev = nh_eu_speed / nh_eu_speed_avg
        #
        nh_us_speed = self.nh_us_speed.getCurrentSpeed()
        nh_us_speed_avg = self.nh_us_speed.getAverageSpeed()
        nh_us_speed_dev = nh_us_speed / nh_us_speed_avg
        #
        nh_speed_score = (nh_eu_speed_dev + nh_us_speed_dev) / 2
        #
        nh_mining_breakeven_price = self.getBreakevenPrice()
        nh_mining_profitability_score = nh_price / nh_mining_breakeven_price
        #
       
        stats = {
                "nh_eu_price": nh_eu_price,
                "nh_eu_price_avg": nh_eu_price_avg,
                "nh_eu_price_dev": nh_eu_price_dev,
                "nh_us_price": nh_us_price,
                "nh_us_price_avg": nh_us_price_avg,
                "nh_us_price_dev": nh_us_price_dev,
                "nh_eu_speed": nh_eu_speed,
                "nh_eu_speed_avg": nh_eu_speed_avg,
                "nh_eu_speed_dev": nh_eu_speed_dev,
                "nh_us_speed": nh_us_speed,
                "nh_us_speed_avg": nh_us_speed_avg,
                "nh_us_speed_dev": nh_us_speed_dev,
                "nh_mining_breakeven_price": nh_mining_breakeven_price,
                "score": {
                        "nh_price_score": nh_price_score,
                        "nh_speed_score": nh_speed_score,
                        "nh_mining_profitability_score": nh_mining_profitability_score,
                    }
            }
        return stats

    def checkForAttack(self):
        # Possible to attack if:
        # 1. NiceHash C32 price is at least XX% higher than recent average
        # 2. NiceHash C32 "Total Available Speed" is at least XX% higher than recent average
        # 3. NiceHash C32 price is at least XX% higher than is profitable
        #    based on current grin price and current grin network c32 graph rate
        stats = self.get_stats()
        if stats["score"]["nh_price_score"] > self.threashold and stats["score"]["nh_speed_score"] > self.threashold and stats["score"]["nh_mining_profitability_score"] > threashold:
            self.under_attack = True
        else:
            self.under_attack = False

    def run(self):
        # Start grin price watcher thread
        self.grin_price = GrinPriceWatcher(max_history=1440)
        grin_price_thread = Thread(target = self.grin_price.run)
        grin_price_thread.daemon = True
        grin_price_thread.start()

        # Start the grin network gps watcher thread
        self.grin_speed = GrinHashSpeedWatcher(max_history=1440)
        grin_speed_thread = Thread(target = self.grin_speed.run)
        grin_speed_thread.daemon = True
        grin_speed_thread.start()

        # Start the EU NiceHash price watcher thread
        self.nh_eu_price = NiceHashPriceWatcher("EU", "GRINCUCKATOO32")
        nh_eu_price_thread = Thread(target = self.nh_eu_price.run)
        nh_eu_price_thread.daemon = True
        nh_eu_price_thread.start()

        # Start the USA NiceHash price watcher thread
        self.nh_us_price = NiceHashPriceWatcher("USA", "GRINCUCKATOO32", max_history=1440)
        nh_us_price_thread = Thread(target = self.nh_us_price.run)
        nh_us_price_thread.daemon = True
        nh_us_price_thread.start()

        # Start the EU NiceHash speed watcher thread
        self.nh_eu_speed = NiceHashSpeedWatcher("EU", "GRINCUCKATOO32", max_history=1440)
        nh_eu_speed_thread = Thread(target = self.nh_eu_speed.run)
        nh_eu_speed_thread.daemon = True
        nh_eu_speed_thread.start()

        # Start the US NiceHash speed watcher thread
        self.nh_us_speed = NiceHashSpeedWatcher("USA", "GRINCUCKATOO32", max_history=1440)
        nh_us_speed_thread = Thread(target = self.nh_us_speed.run)
        nh_us_speed_thread.daemon = True
        nh_us_speed_thread.start()

        sz = 0
        while sz < self.min_history:
            print("Waiting for more data history. Status: {} of {}".format(sz, self.min_history))
            time.sleep(30)
            sz = min(
                     self.grin_price.getSize(),
                     self.grin_speed.getSize(),
                     self.nh_eu_price.getSize(),
                     self.nh_us_price.getSize(),
                     self.nh_eu_speed.getSize(),
                     self.nh_us_speed.getSize()
                )



def main():
    # A few tests
    g51 = Grin51(threashold=1.01)
    g51.run()
    print("Running")
    print("Under Attack: {}".format(g51.under_attack))
    print("Details: {}".format(g51.get_stats()))

if __name__ == "__main__":
    main()
