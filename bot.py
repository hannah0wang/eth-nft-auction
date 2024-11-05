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

# Initialization
bot = telebot.TeleBot(BOT_TOKEN)
web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URI))

auction_started = False
auction_end_timer = None
highest_bid = 0
highest_bidder = None
timer_duration = 30


@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "Howdy")

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    bot.reply_to(message, message.text)


bot.infinity_polling()