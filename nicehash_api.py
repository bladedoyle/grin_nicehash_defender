#!/usr/bin/env python3
  
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
    def __init__(self, API_ID="", API_KEY="", logger=None):
        self.API_ID = API_ID
        self.API_KEY = API_KEY
        self.mfd = {}
        if logger is not None:
            self.logger = logger
        else:
            import logging
            self.logger = logging.getLogger("gnd")


    def setAuth(self, nhid, nhkey):
        self.API_ID = nhid
        self.API_KEY = nhkey

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
        }
        if self.API_ID != "" and self.API_KEY != "":
            headers["X-Auth"] = self.API_ID + ":" + signature

        if method == "GET":
            r = requests.get(
                    url=request_query_str,
                    headers=headers,
                    timeout=20,
                )
        elif method == "POST":
            #print("xxx: {}".format(request_query_str))
            #print("yyy: {}".format(body_str))
            r = requests.post(
                    url=request_query_str,
                    headers=headers,
                    data=body_str,
                    timeout=20,
                )
        elif method == "DELETE":
            #print("xxx: {}".format(request_query_str))
            #print("yyy: {}".format(body_str))
            r = requests.delete(
                    url=request_query_str,
                    headers=headers,
                    timeout=20,
                )
        else:
            raise Exception("Unsupported method: {}".format(method))
        
        if r.status_code >= 300 or r.status_code < 200:
            error_msg = "Error calling {}.  Code: {} Reason: {} content: {}".format(url, r.status_code, r.reason, r.content)
            raise Exception(error_msg)

        r_json = r.json()
        if "error_id" in r_json:
            message = r_json["errors"]["message"]
            method = r_json["method"]
            error_msg = "Error calling {}. Reason: {}".format(method, message)
            raise Exception(error_msg)
        #print("xxx {}".format(r_json))
        return r_json


    ## 

    # Get Market Factor Data
    def getMarketFactorData(self, algo):
        # Its ok to cache this, it does not change
        if algo in self.mfd:
            return self.mfd[algo]
        getAlgorithms_path = "/main/api/v2/mining/algorithms/"
        getAlgorithms_args = {}
        try:
            result = self.call_nicehash_api(
                    path = getAlgorithms_path,
                    args = getAlgorithms_args,
                    method = "GET",
                )
            algorithms = result["miningAlgorithms"]
            for a in algorithms:
                if a["algorithm"] == algo:
                    self.mfd[algo] = a
                    return a
        except Exception as e:
            self.logger.error("failed getMarketFactorData(): {}".format(e))
            raise
        return None

    ##

    # Get NiceHash orderbook for algo on market
    def getOrderBook(self, market, algo):
        getOrderBook_path = "/main/api/v2/hashpower/orderBook/"
        getOrderBook_args = {
                "algorithm": algo,
                "page": "0",
                "size": "1000",
            }
        try:
            result = self.call_nicehash_api(
                    path = getOrderBook_path,
                    args = getOrderBook_args,
                    method = "GET",
                )
            orderbook = result["stats"][market]
        except Exception as e:
            self.logger.error("failed getOrderBook(): {}".format(e))
            raise
        return orderbook

    # Get pool ID by name
    def getPoolId(self, pool_name):
        getPoolId_path = "/main/api/v2/pools"
        getPoolId_args = {
                "page": "0",
                "size": "1000",
            }
        try:
            result = self.call_nicehash_api(
                    path = getPoolId_path,
                    args = getPoolId_args,
                    method = "GET",
                )
            pools = result["list"]
        except Exception as e:
            self.logger.error("failed getPoolId(): {}".format(e))
            raise
        for pool in pools:
            if pool["name"] == pool_name:
                return pool["id"]
        return None

    def createOrder(self, algo, market, pool_id, price, speed, amount):
        marketFactor = int(self.getMarketFactorData(algo)["marketFactor"])
        displayMarketFactor = self.getMarketFactorData(algo)["displayMarketFactor"]
        # Create an order
        createOrder_path = "/main/api/v2/hashpower/order"
        createOrder_body = {
                "market": market,
                "algorithm": algo,
                "amount": amount,
                "type": "STANDARD",
                "poolId": pool_id,
                "limit": "{:.2f}".format(float(speed)),
                "price": "{:.4f}".format(float(price)),
                "marketFactor": marketFactor,
                "displayMarketFactor": displayMarketFactor.encode(),
            }
        self.logger.warn("createOrder_body: {}".format(createOrder_body))
        try:
            result = self.call_nicehash_api(
                    path = createOrder_path,
                    body = createOrder_body,
                    method = "POST",
                )
            order = result
            self.logger.warn("order: {}".format(order))
        except Exception as e:
            self.logger.error("failed createOrder(): {}".format(e))
            raise
        return order


    def getMyOrders(self, market, algo):
        # Get existing orders
        getMyOrders_path =  "/main/api/v2/hashpower/myOrders/"
        getMyOrders_args = {
                "algorithm": algo,
                "market": market,
                "op": "LT",
                "active": True,
                "limit": 100,
            }
        try:
            result = self.call_nicehash_api(
                    path = getMyOrders_path,
                    args = getMyOrders_args,
                    method = "GET",
                )
            myorders = result["list"]
        except Exception as e:
            self.logger.error("failed getMyOrders(): {}".format(e))
            raise
        return myorders

    def getOrder(self, order_id):
        # Get existing order by id
        getOrder_path = "/main/api/v2/hashpower/order/{}/".format(order_id)
        getOrder_args = {}
        try:
            result = self.call_nicehash_api(
                    path = getOrder_path,
                    args = getOrder_args,
                    method = "GET",
                )
        except Exception as e:
            self.logger.error("failed getOrder(): {}".format(e))
            raise
        return result
        

    def cancelOrder(self, order_id):
        # Cancel an order
        cancelOrder_path =  "/main/api/v2/hashpower/order/{}".format(order_id)
        cancelOrder_args = {}
        try:
            result = self.call_nicehash_api(
                    path = cancelOrder_path,
                    args = cancelOrder_args,
                    method = "DELETE",
                )
        except Exception as e:
            self.logger.error("failed cancelOrder(): {}".format(e))
            raise
        return result

    def updateOrder(self, algo, order_id, speed, price):
        marketFactor = self.getMarketFactorData(algo)["marketFactor"]
        displayMarketFactor = self.getMarketFactorData(algo)["displayMarketFactor"]
        # Update an orders price and/or speed limit
        increasePrice_path = "/main/api/v2/hashpower/order/{}/updatePriceAndLimit".format(order_id)
        increasePrice_body = {
                 "marketFactor": marketFactor,
                 "displayMarketFactor": displayMarketFactor,
                 "limit": "{:.2f}".format(float(speed)),
                 "price": "{:.4f}".format(float(price)),
             }
        self.logger.warn("increasePrice_body: {}".format(increasePrice_body))
        try:
            result = self.call_nicehash_api(
                    path = increasePrice_path,
                    body = increasePrice_body,
                    method = "POST",
               )
            self.logger.warn("updated order: {}".format(result))
        except Exception as e:
            self.logger.error("failed updateOrder(): {}".format(e))
            raise
        return result
   

    ##


    def getCurrentPrice(self, market, algo):
        # Find the lowest price thats has miners working
        orderbook = self.getOrderBook(market, algo)
        prices = [o["price"] for o in orderbook["orders"] if int(o["rigsCount"]) > 0 and float(o["acceptedSpeed"]) > 0.00000005 and o["type"] == "STANDARD"]
        prices = sorted(prices)
        return float(prices[0])

    def getCurrentSpeed(self, market, algo):
        # Find the current Total Available NiceHash Speed
        # aka How much hash nicehash is producing
        orderbook = self.getOrderBook(market, algo)
        speed = orderbook["totalSpeed"]
        return float(speed)




def main():
    # Some Tests
    nh_api = NiceHash()
    nh_api.setAuth("x", "y")
    p = nh_api.getCurrentPrice("EU", "GRINCUCKATOO32") 
    print("Current Price EU: {}".format(p))
    p = nh_api.getCurrentPrice("USA", "GRINCUCKATOO32") 
    print("Current Price USA: {}\n\n".format(p))
    s = nh_api.getCurrentSpeed("EU", "GRINCUCKATOO32")
    print("Current Speed EU: {}".format(s))
    s = nh_api.getCurrentSpeed("USA", "GRINCUCKATOO32")
    print("Current Speed USA: {}\n\n".format(s))
    o = nh_api.getMyOrders("EU", "GRINCUCKATOO32")
    print("Current Orders EU: {}".format(o))
    o = nh_api.getMyOrders("USA", "GRINCUCKATOO32")
    print("Current Orders USA: {}\n\n".format(o))
    poolid = nh_api.getPoolId("defender")
    print("Pool id: {}\n\n".format(poolid))
# The following is commented out because it costs money to test
#    o = nh_api.createOrder(algo = "GRINCUCKATOO32",
#                                market = "EU",
#                                pool_id = poolid,
#                                price = 0.1122,
#                                speed = 0.2,
#                                amount = 0.005,
#                            )
#    o = nh_api.getOrder(o["id"])
#    print("EU order details {}".format(o))
#    updated_order = nh_api.updateOrder("GRINCUCKATOO32", o, 0.02 , 0.1122)
#    print("Update Order Result: {}\n\n".format(updated_order))
#    nh_api.cancelOrder(o)
    
 

if __name__ == "__main__":
    main()
