// 0x4d49092da1C9Ce60c3DD105E3524312E72476b2b
// Pranav Mehrotra          20CS10085
// Saransh Sharma           20CS30065
// Shah Dhruv Rajendrabhai  20CS10088
// Vivek Jaiswal            20CS10077
// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.2 <0.9.0;

contract TicketBooking {

    struct Buyer {
        uint256 totalPrice;
        uint numTickets;
        string email;
    }
    address public seller;
    uint256 public numTicketsSold;
    uint256 public maxOccupancy;
    uint256 public price;
    mapping (address => Buyer) buyersPaid;
    bool isSoldOut;

    // Events: Deposit and Refund
    event Deposit(address from, uint256 amount);
    event Refund(address to, uint256 amount);


    constructor(uint256 _quota, uint256 _price) {
        seller = msg.sender;
        numTicketsSold = 0;
        maxOccupancy = _quota;
        price = _price;
        isSoldOut=false;
    }

    function buyTickets(string memory _emailAddress, uint _numTickets) public payable soldOut {
        require(_numTickets > 0, "You must buy at least one ticket");
        require(numTicketsSold + _numTickets <= maxOccupancy, "Not enough tickets left");
        uint256 totalCost = _numTickets * price;
        require(msg.value >= totalCost, "Insufficient funds sent");

        if (buyersPaid[msg.sender].numTickets > 0) {
            buyersPaid[msg.sender].numTickets += _numTickets;
            buyersPaid[msg.sender].totalPrice += totalCost;
        } else {
            buyersPaid[msg.sender] = Buyer({
                numTickets: _numTickets,
                totalPrice: totalCost,
                email: _emailAddress
            });
        }

        numTicketsSold += _numTickets;

        if (numTicketsSold >= maxOccupancy) {
            isSoldOut = true;
        }

        if (msg.value > totalCost) {
            uint256 refundAmount = msg.value - totalCost;
            payable(msg.sender).transfer(refundAmount);
        }
        emit Deposit(msg.sender, totalCost);
    }

    modifier soldOut() {
        require(!isSoldOut, "All tickets have been sold!");
        _;
    }

    modifier onlySeller() {
        require(msg.sender == seller, "Only the seller can perform this action");
        _;
    }

    function withdrawFunds() public onlySeller {
        // require(isSoldOut, "Cannot withdraw funds until all tickets are sold");
        payable(seller).transfer(address(this).balance);
    }

    function refundTicket(address buyer) public onlySeller {
        require(buyersPaid[buyer].numTickets > 0, "This address has not purchased any tickets");
        uint256 refundAmount = buyersPaid[buyer].totalPrice;
        require(refundAmount <= address(this).balance, "Insufficient Balance, cannot refund the ticket!");
        numTicketsSold -= buyersPaid[buyer].numTickets;
        isSoldOut = false; // Reset sold out status
        delete buyersPaid[buyer];
        payable(buyer).transfer(refundAmount);
        emit Refund(buyer, refundAmount);
    }

    function getBuyerAmountPaid(address buyer) public view returns (uint256) {
        return buyersPaid[buyer].totalPrice;
    }

    function kill() public onlySeller {
        // address payable payableOwner = payable(seller);
        // uint256 contractBalance = address(this).balance;
        // payableOwner.transfer(contractBalance);
   		selfdestruct(payable(seller));
    }

}