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
    event TimeRemaining(uint256 timeLeft);
    event PriceReduced(uint256 newPrice);

    IERC721 public nft;
    uint256 public nftId;

    address payable public seller;
    bool public started;
    bool public ended;

    uint32 public timer;
    uint32 public totalTime;
    uint32 public inactiveTime = 30;

    address public highestBidder;
    uint256 public highestBid;
    mapping(address => uint) public bids; // stores the amounts that bidders can withdraw if they are outbid

    // Dutch auction features:
    uint256 public floorPrice; // Minimum price the auction can go down to
    uint256 public reductionPercentage = 5; // Percentage to reduce the price by

    constructor(address _nft, uint256 _nftId, uint256 _startingBid, uint32 _totalTime, uint256 _floorPrice) {
        require(_startingBid > _floorPrice, "Starting bid must be greater than floor price");
        nft = IERC721(_nft);
        nftId = _nftId;

        seller = payable(msg.sender);
        highestBid = _startingBid;
        totalTime = uint32(block.timestamp) + _totalTime; // total time limit for auction
        floorPrice = _floorPrice;
    }

    function start() external {
        require(msg.sender == seller, "not seller");
        require(!started, "started");

        // Transfer NFT to contract and ensure it's successful
        nft.transferFrom(seller, address(this), nftId);
        require(nft.ownerOf(nftId) == address(this), "Failed to transfer NFT");
        
        started = true;
        timer = uint32(block.timestamp + inactiveTime);

        emit Start();
    }

    function bid() external payable nonReentrant {
        require(started, "Auction has not started");
        require(!ended, "Auction has already ended");
        require(block.timestamp <= totalTime, "Total auction time has expired");
        require(msg.value > highestBid, "New bid must be higher than the current highest bid");

        if (highestBidder != address(0)) {
            bids[highestBidder] += highestBid;
        }

        highestBidder = msg.sender;
        highestBid = msg.value;
        timer = uint32(block.timestamp + inactiveTime); // reset the timer since a new bid has been made

        emit Bid(msg.sender, msg.value);
    }

    function withdraw() external nonReentrant {
        uint balance = bids[msg.sender];
        bids[msg.sender] = 0; // protect from reentrancy. if we transfer eth before setting balance, then contract will be vulnerable to reentrancy
        
        // then after resetting the balance, transfer the eth out:
        payable(msg.sender).transfer(balance);

        // Emit event for successful withdrawal
        emit Withdraw(msg.sender, balance);
    }

    function end() external {
        require(started, "Auction has not started");
        require(!ended, "Auction has already ended");
        require(msg.sender == seller || block.timestamp >= timer, "Only the seller can end the auction or time must be expired");

        _endAuction();
    }

    // check if upkeep is needed. this is when the timer is over
    function checkUpkeep(bytes calldata) external view override returns (bool upkeepNeeded, bytes memory) {
        upkeepNeeded = (started && !ended && (block.timestamp >= timer || block.timestamp >= totalTime));
    }

    // Automatically perform upkeep. either end the auction or reduce the price
    function performUpkeep(bytes calldata) external override {
        if (started && !ended) {
            if (block.timestamp >= totalTime) {
                // total time limit is reached, end the auction
                _endAuction();
            } else if (block.timestamp >= timer) {
                // No bids made in the last inactiveTime, reduce price (Dutch auction feature)
                if (highestBidder == address(0)) {
                    // Reduce the starting bid by reductionPercentage if no bids have been placed
                    uint256 newPrice = highestBid - (highestBid * reductionPercentage) / 100;

                    if (newPrice < floorPrice) {
                        highestBid = floorPrice; // Ensure price does not go below the floor price
                    } else {
                        highestBid = newPrice;
                    }

                    timer = uint32(block.timestamp + inactiveTime); // Reset timer for next price reduction
                    emit PriceReduced(highestBid);
                }
            }
        }
    }

    function _endAuction() internal {
        ended = true;

        if (highestBidder != address(0)) {
            // Transfer the NFT to the highest bidder
            nft.safeTransferFrom(address(this), highestBidder, nftId);

            // Transfer funds to the seller
            seller.transfer(highestBid);
        } else {
            // If no bids, return NFT to seller
            nft.safeTransferFrom(address(this), seller, nftId);
        }

        emit End(highestBidder, highestBid);
    }
}
