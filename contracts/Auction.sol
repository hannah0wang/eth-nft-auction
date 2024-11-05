// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {AutomationCompatibleInterface} from "@chainlink/contracts/src/v0.8/automation/AutomationCompatible.sol";

contract EnglishAuction is AutomationCompatibleInterface, ReentrancyGuard {
    event Start();
    event Bid(address indexed sender, uint256 amount);
    event Withdraw(address indexed bidder, uint256 amount);
    event End(address winner, uint256 amount);
    event TimeRemaining(uint256 timeLeft); // notify about remaining time


    IERC721 public nft;
    uint256 public nftId;

    address payable public seller;
    uint32 public timer;
    bool public started;
    bool public ended;

    address public highestBidder;
    uint256 public highestBid;
    mapping(address => uint) public bids; // stores the amouts that bidders can withdraw if they are outbid


    constructor(address _nft, uint256 _nftId, uint256 _startingBid) {
        nft = IERC721(_nft);
        nftId = _nftId;

        seller = payable(msg.sender);
        highestBid = _startingBid;
    }

    function start() external {
        require(msg.sender == seller, "not seller");
        require(!started, "started");

        // Transfer NFT to contract and ensure it's successful
        nft.transferFrom(seller, address(this), nftId);
        require(nft.ownerOf(nftId) == address(this), "Failed to transfer NFT");
        
        started = true;
        timer = uint32(block.timestamp + 30);

        emit Start();
    }

    function bid() external payable nonReentrant {
        require(started, "Auction has not started");
        require(!ended, "Auction has already ended");
        require(msg.value > highestBid, "New bid must be higher than the current highest bid");

        if (highestBidder != address(0)) {
            bids[highestBidder] += highestBid;
        }

        highestBidder = msg.sender;
        highestBid = msg.value;
        timer = uint32(block.timestamp + 30); // reset the timer since a new bid has been made

        emit Bid(msg.sender, msg.value);
    }

    function withdraw() external nonReentrant {
        uint256 balance = bids[msg.sender];
        require(balance > 0, "No funds to withdraw");

        bids[msg.sender] = 0; // Protect against reentrancy
        (bool success, ) = msg.sender.call{value: balance}("");
        require(success, "Withdraw failed");

        emit Withdraw(msg.sender, balance);
    }

    function end() external {
        require(started, "Auction has not started");
        require(!ended, "Auction has already ended");
        require(msg.sender == seller || block.timestamp >= timer, "Only the seller can end the auction or time must be expired");

        _endAuction();
    }

    function checkUpkeep(bytes calldata) external view override returns (bool upkeepNeeded, bytes memory) {
        upkeepNeeded = (started && !ended && block.timestamp >= timer);
    }

    function performUpkeep(bytes calldata) external override {
        if (started && !ended && block.timestamp >= timer) {
            _endAuction();
        } else if (started && !ended) {
            uint256 timeLeft = timer > block.timestamp ? timer - block.timestamp : 0;

            if (timeLeft == 30 || timeLeft == 5) {
                emit TimeRemaining(timeLeft);
            }
        }
    }

    function _endAuction() internal {
        ended = true;

        if (highestBidder != address(0)) {
            // Transfer the NFT to the highest bidder
            nft.safeTransferFrom(address(this), highestBidder, nftId);

            // Transfer funds to the seller
            (bool success, ) = seller.call{value: highestBid}("");
            require(success, "Transfer to seller failed");
        } else {
            // If no bids, return NFT to seller
            nft.safeTransferFrom(address(this), seller, nftId);
        }

        emit End(highestBidder, highestBid);
    }
}
