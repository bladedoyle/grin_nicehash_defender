# Grin Nicehash Defender

Current Project Status:
 * Release 1.0
 * Community-Funded instance is running at <a href="https://grindefender.online/">grindefender.online</a>

Grin Nicehash Defender is a bot that Grin community members can use to help defend the Grin network. If abnormal activity is taking place the bot will rent C32 hashpower from Nicehash to increase Grin network security for the duration of the attack.  

What it does:
  * Monitors grin network for 51% attack (Supports detection algorithms: Grin51 and grin-health)
  * If an attack is detected a NiceHash C32 order will be created on both EU and USA markets
  * While the attack is active, the order limit prices will be increased to keep miners working
  * After the attack ends, the two orders will be deleted

How to use it:
  * Create a NiceHash account
  * Create a NiceHash "Organization" (optional but recommended)
  * Create a pool (under "Hashpower Marketplace" -> "MY POOLS" -> "+ ADD NEW POOL") named "defender" for algorithm "GrinCuckatoo32"
  * Fund your wallet with BTC (at least 0.005 BTC)
  * Get NiceHash "API keys": Needs Permissions:
    Wallet:  "View balances"
    Market place Permissions: "View hashpower orders", "manage hashpower orders - place", "manage hashpower orders - edit price"
  * Set environment variables NICEHASH_API_ID and NICEHASH_API_KEY (or add to config.yml)
  * Clone this git project
  * Install required python modules: ```pip install -r requirements.txt```
  * Edit "config.yml" and update settings
  * Run: ```python grin_nicehash_defender.py```

grin51 attack detection module will detect a possible attack if:
  * NiceHash C32 price is at least 30% higher than recent average
and
  * NiceHash C32 "Total Available Speed" is at least 30% higher than recent average
and
  * NiceHash C32 price is at least 30% higher than is profitable based on current grin price and current grin network c32 graph rate.
Note:  These threasholds are configurable

Joltz attack detection module:
  * Documented here:  https://github.com/j01tz/grin-health
