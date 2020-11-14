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
import yaml
import pprint
pp = pprint.PrettyPrinter(indent=4)
import requests
import traceback
from datetime import datetime, timedelta
from threading import Thread

from nicehash_api import NiceHash


class GrinNiceHashDefender():
    def __init__(self):
        self.nh_api = NiceHash()
        self.config = None
        self.under_attack = False
        self.attack_start = None
        self.nh_pool_id = None
        self.nh_orders = { "EU": None, "USA": None }
        self.nh_order_add_duration = None
        self.attack_stats = {}

    def getConfig(self):
        if not os.path.exists('config.yml'):
            print("Failed to find configuration file")
            sys.exit(1)
        with open('config.yml', 'r') as c:
            cfg = c.read()
            try:
                self.config = yaml.safe_load(cfg)[0]
            except Exception as e:
                print("Failed to load configuration.  Check syntax.\n{}".format(e))
                sys.exit(1)
        self.nh_order_add_duration = timedelta(minutes=int(self.config["ADD_ORDER_DURATION"]))
        try:
            if self.config["NICEHASH_API_ID"] == "":
                self.config["NICEHASH_API_ID"] = os.environ["NICEHASH_API_ID"]
            if self.config["NICEHASH_API_KEY"] == "":
                self.config["NICEHASH_API_KEY"] = os.environ["NICEHASH_API_KEY"]
            self.nh_api.setAuth(self.config["NICEHASH_API_ID"], self.config["NICEHASH_API_KEY"])
        except Exception as e:
            print("Failed to find NICEHASH_API_ID and NICEHASH_API_KEY: {}".format(e))
            sys.exit(1)
        try:
            self.nh_pool_id = self.nh_api.getPoolId(self.config["POOL_NAME"])
        except Exception as e:
            print("Failed to connect to your nicehash account: {}".format(e))
            sys.exit(1)
        if self.nh_pool_id is None:
            print("Failed to find pool {} in your NiceHash account".format(self.config["POOL_NAME"]))
            sys.exit(1)
        if self.config["CHECK_TYPE"] == "grin51":
            print("Loading Grin51 detection module")
            from grin51 import Grin51
            self.grin51 = Grin51()
            self.grin51.run()
            print("Grin51 detection module is running")

    def checkForAttack(self):
        attack = False
        if self.config["CHECK_TYPE"] == "file":
            if os.path.exists('attack'):
                attack = True
        elif self.config["CHECK_TYPE"] == "grin51":
            attack = self.grin51.under_attack
            self.attack_stats = self.grin51.get_stats()
        elif self.config["CHECK_TYPE"] == "service":
            attack = result_of_calling_a_service_api()
        else:
            print("Unknown attack detection method: {}".format(self.config["CHECK_TYPE"]))
            sys.exit(1)
        # Set some values for attack state
        if attack:
            self.under_attack = True
            self.attack_start = datetime.now()
        else:
            self.under_attack = False
            # Dont reset start time since we still use that for a bit

    def manageOrders(self):
        if self.attack_start is not None:
            try:
                eu_price = self.nh_api.getCurrentPrice("EU", "GRINCUCKATOO32") + self.config["ORDER_PRICE_ADD"]
                us_price = self.nh_api.getCurrentPrice("USA", "GRINCUCKATOO32") + self.config["ORDER_PRICE_ADD"]
            except Exception as e:
                print("Error getting NH price data: {}".format(e))
                return
        if self.under_attack:
            # Create orders if needed
            if self.nh_orders["EU"] is None:
                # Create the order
                try:
                    new_order = self.nh_api.createOrder(
                                    algo = "GRINCUCKATOO32",
                                    market = "EU",
                                    pool_id = self.nh_pool_id,
                                    price = eu_price,
                                    speed = self.config["MAX_SPEED"],
                                    amount = self.config["ORDER_AMOUNT"],
                                )
                    self.nh_orders["EU"] = new_order["id"] 
                    print("Created EU Order: {}".format(self.nh_orders["EU"]))
# XXX DEBUGGING XXX
#                    self.nh_orders["EU"] = "0e69ab28-b9c0-40eb-bda7-3a0a975440c7"
# XXX DEBUGGING XXX
                except Exception as e:
                    print("Error creating EU order: {}".format(e))
            if self.nh_orders["USA"] is None:
                try:
                    new_order = self.nh_api.createOrder(
                                    algo = "GRINCUCKATOO32",
                                    market = "USA",
                                    pool_id = self.nh_pool_id,
                                    price = us_price,
                                    speed = self.config["MAX_SPEED"],
                                    amount = self.config["ORDER_AMOUNT"],
                                )
                    self.nh_orders["USA"] = new_order["id"] 
                    print("Created USA Order: {}".format(self.nh_orders["USA"]))
# XXX DEBUGGING XXX
#                    self.nh_orders["USA"] = "8ef742e2-6a8c-4c19-b46c-d96b2050a43f"
# XXX DEBUGGING XXX
                except Exception as e:
                    print("Error creating USA order: {}".format(e))




        # Update order price limits if needed
        if self.nh_orders["EU"] is not None:
            # Update the EU order
            try:
                order = self.nh_api.getOrder(self.nh_orders["EU"])
                new_eu_price = max(float(order["price"]), float(eu_price))
                print("order price: {}, eu_price: {}, new_eu_price: {}".format(order["price"], eu_price, new_eu_price))
                order = self.nh_api.updateOrder(
                                algo = "GRINCUCKATOO32",
                                order_id = self.nh_orders["EU"],
                                speed = self.config["MAX_SPEED"],
                                price = new_eu_price,
                            )
                print("EU order status:")
                if self.config["VERBOSE"]:
                    pp.pprint(order)
                else:
                    print("Speed: {}, Price: {}, BTC_Remaining: {}".format(order["acceptedCurrentSpeed"], order["price"], order["availableAmount"]))
            except Exception as e:
                print("Error updating EU order: {}".format(e))
        if self.nh_orders["USA"] is not None:
            # Update the order
            try:
                order = self.nh_api.getOrder(self.nh_orders["USA"])
                new_us_price = max(float(order["price"]), float(us_price))
                print("order price: {}, us_price: {}, new_us_price: {}".format(order["price"], us_price, new_us_price))
                order = self.nh_api.updateOrder(
                                algo = "GRINCUCKATOO32",
                                order_id = self.nh_orders["USA"],
                                speed = self.config["MAX_SPEED"],
                                price = new_us_price,
                            )
                print("USA order status:")
                if self.config["VERBOSE"]:
                    pp.pprint(order)
                else:
                    print("Speed: {}, Price: {}, BTC_Remaining: {}".format(order["acceptedCurrentSpeed"], order["price"], order["availableAmount"] ))
            except Exception as e:
                print("Error updating USA order: {}".format(e))
            
        
        # Following an attack ensure no orders are active after minimum run duration
        if not self.under_attack and self.attack_start is not None:
            print("Attack start: {}".format(self.attack_start))
            print("Time remaining: {}".format(self.nh_order_add_duration-(datetime.now() - self.attack_start)))
            if datetime.now() - self.attack_start > self.nh_order_add_duration:
                if self.nh_orders["EU"] is not None:
                    try:
                        self.nh_api.cancelOrder(self.nh_orders["EU"])
                        print("Deleted EU order: {}".format(self.nh_orders["EU"]))
                        self.nh_orders["EU"] = None
                    except Exception as e:
                        print("Error canceling EU order: {}".format(e))
                if self.nh_orders["USA"] is not None:
                    try:
                        self.nh_api.cancelOrder(self.nh_orders["USA"])
                        print("Deleted USA order: {}".format(self.nh_orders["USA"]))
                        self.nh_orders["USA"] = None
                    except Exception as e:
                        print("Error canceling USA order: {}".format(e))
            if self.nh_orders["EU"] is None and self.nh_orders["USA"] is None:
                # The attack is over, we are done defending, all is cleaned up
                self.attack_start = None
            

    def run(self):
        # Load Tool Configuration
        try:
            print("Loading Configuration....")
            self.getConfig()
            if self.config["VERBOSE"]:
              pp.pprint(self.config)
            print("Done Loading Configuration")
        except Exception as e:
            print("Failed to load configuration: {}".format(e))
            sys.exit(1)
        # Run the Tool
        print("Running {}: {}".format(self.config["NAME"], datetime.now()))
        while True:
            print("---> Starting control loop: {}".format(datetime.now()))
            try:
                self.checkForAttack()
                print("Under Attack: {}".format(self.under_attack))
                print("Attack Analysis Stats:")
                pp.pprint(self.attack_stats)
                self.manageOrders()
                if self.nh_orders["EU"] is not None:
                    print("Managing EU NiceHash order: {}".format(self.nh_orders["EU"]))
                if self.nh_orders["USA"] is not None:
                    print("Managing US NiceHash order: {}".format(self.nh_orders["USA"]))
            except Exception as e:
                print("Unexpected Error: {}".format(e))
                print("Attemping to continue...")
            print("<--- Completed control loop\n\n")
            time.sleep(self.config["LOOP_INTERVAL"])


def main():
    defender = GrinNiceHashDefender()
    defender.run()

 

if __name__ == "__main__":
    main()
