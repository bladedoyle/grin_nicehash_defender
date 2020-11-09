# Grin Nicehash Defender

Monitors grin network and price, and nicehash C32 rate and speed.
Reports an attack if detected.

How to use it:
  * Create a NiceHash account
  * Get a NiceHash API ID and KEY
  * Set environment variables NICEHASH_API_ID and NICEHASH_API_KEY
  * Clone this git project
  * Run:  grin_nicehash_defender.py

Reports possible to attack if:
  * NiceHash C32 price is at least 30% higher than recent average
and
  * NiceHash C32 "Total Available Speed" is at least 30% higher than recent average
and
  * NiceHash C32 price is at least 30% higher than is profitable based on current grin price and current grin network c32 graph rate.


Example Output:
```
checkForAttack:
  Num Attack Detections: 0
  nh_price_dev: 0.978374441947
  nh_speed_dev: 1.02894497499
  grin_profitability: 0.764705513161
  No attack detected at this time
```
