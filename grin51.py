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

# TODO - move config to config.yml
MIN_HISTORY = 30   # (minutes) Minimum amount of data to collect before taking action
MAX_HISTORY = 1440 # (minutes) Maximum amount of data to use as "recent history"

##
# Watchers for external data

class GrinHashSpeedWatcher():
    def __init__(self):
        self.interval = 60
        self.max_size = MAX_HISTORY
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
    def __init__(self):
        self.interval = 60
        self.max_size = MAX_HISTORY
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
    def __init__(self, market, algo):
        self.market = market
        self.algo = algo
        self.interval = 60
        self.max_size = MAX_HISTORY
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
    def __init__(self, market, algo):
        self.market = market
        self.algo = algo
        self.interval = 60
        self.max_size = MAX_HISTORY
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
    def __init__(self):
        self.nh_api = NiceHash()
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
                "nh_price_score": nh_price_score,
                "nh_eu_speed": nh_eu_speed,
                "nh_eu_speed_avg": nh_eu_speed_avg,
                "nh_eu_speed_dev": nh_eu_speed_dev,
                "nh_us_speed": nh_us_speed,
                "nh_us_speed_avg": nh_us_speed_avg,
                "nh_us_speed_dev": nh_us_speed_dev,
                "nh_speed_score": nh_speed_score,
                "nh_mining_breakeven_price": nh_mining_breakeven_price,
                "nh_mining_profitability_score": nh_mining_profitability_score,
            }
        return stats

    def checkForAttack(self):
        # Possible to attack if:
        # 1. NiceHash C32 price is at least 30% higher than recent average
        # 2. NiceHash C32 "Total Available Speed" is at least 30% higher than recent average
        # 3. NiceHash C32 price is at least 30% higher than is profitable
        #    based on current grin price and current grin network c32 graph rate
        stats = self.get_stats()
        if stats["nh_price_score"] > 1.3 and stats["nh_speed_score"] > 1.3 and stats["nh_mining_profitability_score"] > 1.3:
            self.under_attack = True
        else:
            self.under_attack = False

    def run(self):
        # Start grin price watcher thread
        self.grin_price = GrinPriceWatcher()
        grin_price_thread = Thread(target = self.grin_price.run)
        grin_price_thread.daemon = True
        grin_price_thread.start()

        # Start the grin network gps watcher thread
        self.grin_speed = GrinHashSpeedWatcher()
        grin_speed_thread = Thread(target = self.grin_speed.run)
        grin_speed_thread.daemon = True
        grin_speed_thread.start()

        # Start the EU NiceHash price watcher thread
        self.nh_eu_price = NiceHashPriceWatcher("EU", "GRINCUCKATOO32")
        nh_eu_price_thread = Thread(target = self.nh_eu_price.run)
        nh_eu_price_thread.daemon = True
        nh_eu_price_thread.start()

        # Start the USA NiceHash price watcher thread
        self.nh_us_price = NiceHashPriceWatcher("USA", "GRINCUCKATOO32")
        nh_us_price_thread = Thread(target = self.nh_us_price.run)
        nh_us_price_thread.daemon = True
        nh_us_price_thread.start()

        # Start the EU NiceHash speed watcher thread
        self.nh_eu_speed = NiceHashSpeedWatcher("EU", "GRINCUCKATOO32")
        nh_eu_speed_thread = Thread(target = self.nh_eu_speed.run)
        nh_eu_speed_thread.daemon = True
        nh_eu_speed_thread.start()

        # Start the US NiceHash speed watcher thread
        self.nh_us_speed = NiceHashSpeedWatcher("USA", "GRINCUCKATOO32")
        nh_us_speed_thread = Thread(target = self.nh_us_speed.run)
        nh_us_speed_thread.daemon = True
        nh_us_speed_thread.start()

        sz = 0
        while sz < MIN_HISTORY:
            print("Waiting for more data history: {} of {}".format(sz, MIN_HISTORY))
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
    g51 = Grin51()
    g51.run()
    print("Running")
    print("Under Attack: {}".format(g51.under_attack))
    print("Details: {}".format(g51.get_stats()))

if __name__ == "__main__":
    main()
