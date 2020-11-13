# Grin Nicehash Defender

What it does:
  * Monitors grin network and price, and nicehash C32 rate and price
  * If an attack is detected 2 NiceHash C32 orders will be created
  * While the attack is active, the order limit prices will be increased to keep miners
  * After the attack ends, the 2 orders will be deleted

How to use it:
  * Create a NiceHash account
  * Get a NiceHash API ID and KEY
  * Set environment variables NICEHASH_API_ID and NICEHASH_API_KEY
  * Clone this git project
  * Edit "config.yml" and update settings
  * Run:  grin_nicehash_defender.py

grin51 attack detection module will detect a possible attack if:
  * NiceHash C32 price is at least 30% higher than recent average
and
  * NiceHash C32 "Total Available Speed" is at least 30% higher than recent average
and
  * NiceHash C32 price is at least 30% higher than is profitable based on current grin price and current grin network c32 graph rate.
