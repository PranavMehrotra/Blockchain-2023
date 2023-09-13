#!/bin/bash

# Infura API key and Ethereum node URL
INFURA_API_KEY="bb9a7bde227c4446afd8d7a23d806d94"
ETHEREUM_NODE_URL="https://goerli.infura.io/v3/$INFURA_API_KEY"

# Replace with the transaction hash you want to query
TRANSACTION_HASH="0xdcae4a84a5780f62f18a9afb07b3a7627b9a28aa128a76bfddec72de9a0c2606"

# Function to get the number of sender's transactions before the specified transaction in the block
    tx_hash="$TRANSACTION_HASH"
    
    echo "$tx_hash"
    # Get the transaction details
    tx_info=$(curl -X POST -H "Content-Type: application/json" --data '{
        "jsonrpc":"2.0",
        "method":"eth_getTransactionByHash",
        "params":["'"$tx_hash"'"],
        "id":1
    }' "$ETHEREUM_NODE_URL")
    
    sender_address=$(echo "$tx_info" | jq -r '.result.from')
    block_hash=$(echo "$tx_info" | jq -r '.result.blockHash')

    echo "$sender_address"
    echo "$block_hash"
    
    # Get the block containing the transaction
    block_info=$(curl -X POST -H "Content-Type: application/json" --data '{
        "jsonrpc":"2.0",
        "method":"eth_getBlockByHash",
        "params":["'"$block_hash"'", true],
        "id":1
    }' "$ETHEREUM_NODE_URL")
    
    transaction_count=0
    # echo "$block_info"
    # Iterate through the transactions in the block
    transactions=$(echo "$block_info" | jq -c '.result.transactions[]')
    # echo "$transactions"
    
    for tx in $transactions; do
        tx_sender=$(echo "$tx" | jq -r '.from')
        echo "$tx"
        
        if [ "$tx_sender" == "$sender_address" ]; then
            transaction_count=$((transaction_count + 1))
        fi
        
        if [ "$tx_hash" == $(echo "$tx" | jq -r '.hash') ]; then
            break
        fi
        # break
    done
    
    echo "$transaction_count"
