## ETH NFT Auction

### Overview
This ETH NFT auction combines the functionality of an English auction with Dutch auction features. It allows users to bid on NFTs, with price reductions over time if no bids are made. The auction automatically stops after a specified duration of inactivity or when a total time limit is reached.

### Features
- Participants place bids that must be higher than the current bid.
- If no bids are placed for a specified time, the starting price is reduced by 5%, down to a defined floor price.
- Total time limit to ensures the auction ends automatically after a defined period, even if bids continue to be placed.
- Chainlink Automation to manage automatic auction upkeep, including price reductions and ending the auction.

### Future Improvements
- Frontend UI integration
- Add a Telegram bot to facilitate auctions between users, making it easier for participants to bid and interact with the auction directly whithin a chat environment.
