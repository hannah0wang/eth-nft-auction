import os
import telebot
from dotenv import load_dotenv
from web3 import Web3
from threading import Timer

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB3_PROVIDER_URI = os.getenv('WEB3_PROVIDER_URI')
AUCTION_CONTRACT_ADDRESS = os.getenv('AUCTION_CONTRACT_ADDRESS')
NFT_CONTRACT_ADDRESS = os.getenv('NFT_CONTRACT_ADDRESS')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')
ADMIN_USER = os.getenv('ADMIN_USER')
AUCTION_CONTRACT_ABI = [...]  # Replace with your Auction contract ABI
NFT_CONTRACT_ABI = [...]  # Replace with your NFT contract ABI

# Initialize the bot and web3
bot = telebot.TeleBot(BOT_TOKEN)
web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URI))

# Load the smart contracts
auction_contract = web3.eth.contract(address=Web3.toChecksumAddress(AUCTION_CONTRACT_ADDRESS), abi=AUCTION_CONTRACT_ABI)
nft_contract = web3.eth.contract(address=Web3.toChecksumAddress(NFT_CONTRACT_ADDRESS), abi=NFT_CONTRACT_ABI)

# Global variables to track auction state
auction_started = False
auction_end_timer = None
highest_bid = 0
highest_bidder = None
timer_duration = 30  # 30 seconds of no bidding ends the auction


# Command to mint an NFT
@bot.message_handler(commands=['mint_nft'])
def mint_nft(message):
    if message.from_user.username == ADMIN_USER:  # Replace with actual admin username
        # Call mint() function on the NFT contract
        mint_tx = nft_contract.functions.mint().buildTransaction({
            'from': WALLET_ADDRESS,
            'nonce': web3.eth.getTransactionCount(WALLET_ADDRESS),
            'gasPrice': web3.toWei('5', 'gwei')
        })
        signed_mint_tx = web3.eth.account.sign_transaction(mint_tx, PRIVATE_KEY)
        tx_hash = web3.eth.sendRawTransaction(signed_mint_tx.rawTransaction)
        receipt = web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            token_id = nft_contract.functions.tokenIds().call()
            bot.send_message(message.chat.id, f"NFT minted successfully! Token ID: {token_id}")
        else:
            bot.send_message(message.chat.id, "Failed to mint NFT.")
    else:
        bot.reply_to(message, "Only the admin can mint an NFT.")


# Command to approve the auction contract to manage the NFT
@bot.message_handler(commands=['approve_auction'])
def approve_auction(message):
    try:
        user_input = message.text.split()
        if len(user_input) < 2:
            bot.reply_to(message, "Please provide the Token ID. Usage: /approve_auction <token_id>")
            return

        token_id = int(user_input[1])

        # Call approve() function on the NFT contract
        approve_tx = nft_contract.functions.approve(AUCTION_CONTRACT_ADDRESS, token_id).buildTransaction({
            'from': WALLET_ADDRESS,
            'nonce': web3.eth.getTransactionCount(WALLET_ADDRESS),
            'gasPrice': web3.toWei('5', 'gwei')
        })
        signed_approve_tx = web3.eth.account.sign_transaction(approve_tx, PRIVATE_KEY)
        tx_hash = web3.eth.sendRawTransaction(signed_approve_tx.rawTransaction)
        receipt = web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            bot.send_message(message.chat.id, f"NFT with Token ID {token_id} approved successfully for auction.")
        else:
            bot.send_message(message.chat.id, "Failed to approve NFT for auction.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid Token ID. Usage: /approve_auction <token_id>")


# Command to start the auction
@bot.message_handler(commands=['start_auction'])
def start_auction(message):
    global auction_started, chat_id

    if message.from_user.username == ADMIN_USER:
        # Call start() function on the Auction contract
        tx = auction_contract.functions.start().buildTransaction({
            'from': WALLET_ADDRESS,
            'nonce': web3.eth.getTransactionCount(WALLET_ADDRESS),
            'gasPrice': web3.toWei('5', 'gwei')
        })
        signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        receipt = web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            auction_started = True
            chat_id = message.chat.id  # Store the chat ID to use in the end_auction function
            bot.send_message(message.chat.id, "The auction has started! Place your bids using /bid <amount>.")
            reset_timer()  # Start the timer
        else:
            bot.send_message(message.chat.id, "Failed to start the auction.")
    else:
        bot.reply_to(message, "Only the admin can start the auction.")



# Command to place a bid
@bot.message_handler(commands=['bid'])
def place_bid(message):
    global auction_started, highest_bid, highest_bidder

    if not auction_started:
        bot.reply_to(message, "The auction has not started yet.")
        return

    try:
        bid_amount = float(message.text.split()[1])
        bid_amount_wei = web3.toWei(bid_amount, 'ether')

        if bid_amount_wei <= highest_bid:
            bot.reply_to(message, f"Your bid must be higher than the current highest bid of {web3.fromWei(highest_bid, 'ether')} ETH.")
        else:
            # Call bid() function on the Auction contract
            tx = auction_contract.functions.bid().buildTransaction({
                'from': WALLET_ADDRESS,
                'value': bid_amount_wei,
                'nonce': web3.eth.getTransactionCount(WALLET_ADDRESS),
                'gasPrice': web3.toWei('5', 'gwei')
            })
            signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
            tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
            receipt = web3.eth.waitForTransactionReceipt(tx_hash)

            if receipt.status == 1:
                highest_bid = bid_amount_wei
                highest_bidder = message.from_user.first_name

                bot.send_message(message.chat.id, f"New highest bid of {web3.fromWei(highest_bid, 'ether')} ETH by {highest_bidder}!")

                # Reset the auction end timer after a new bid
                reset_timer()
            else:
                bot.reply_to(message, "Failed to place bid.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Please provide a valid bid amount. Usage: /bid <amount>")


# Function to end the auction
def end_auction():
    global auction_started, highest_bid, highest_bidder, auction_end_timer

    if auction_started:
        # Call end() function on the Auction contract
        tx = auction_contract.functions.end().buildTransaction({
            'from': WALLET_ADDRESS,
            'nonce': web3.eth.getTransactionCount(WALLET_ADDRESS),
            'gasPrice': web3.toWei('5', 'gwei')
        })
        signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        receipt = web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            if highest_bidder:
                bot.send_message(chat_id, f"The auction has ended! The winner is {highest_bidder} with a bid of {web3.fromWei(highest_bid, 'ether')} ETH.")
            else:
                bot.send_message(chat_id, "The auction has ended with no bids.")
        else:
            bot.send_message(chat_id, "Failed to end the auction.")

        # Reset auction state
        auction_started = False
        auction_end_timer = None


# Helper function to reset timer
def reset_timer():
    global auction_end_timer

    if auction_end_timer:
        auction_end_timer.cancel()

    auction_end_timer = Timer(timer_duration, end_auction)
    auction_end_timer.start()


# Run the bot to listen for messages
bot.infinity_polling()
