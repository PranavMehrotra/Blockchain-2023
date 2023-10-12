/*
 SPDX-License-Identifier: Apache-2.0
*/

package main

import (
	"bytes"
	"encoding/json"
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// GetBalance returns the balance of the caller's account from the public data
func (s *SmartContract) GetBalance(ctx contractapi.TransactionContextInterface) (int, error) {
	// Since only public data is accessed in this function, no access control is required
	clientOrgID, err := getClientOrgID(ctx)
	if err != nil {
		return 0, err
	}
	balanceKey, _ := ctx.GetStub().CreateCompositeKey("balance", []string{clientOrgID})
	balanceJSON, err := ctx.GetStub().GetState(balanceKey)
	if err != nil {
		return 0, fmt.Errorf("failed to read from world state: %v", err)
	}
	if balanceJSON == nil {
		return 0, fmt.Errorf("%s does not exist", clientOrgID)
	}

	var balance int
	err = json.Unmarshal(balanceJSON, &balance)
	if err != nil {
		return 0, err
	}
	return balance, nil
}

// GetAllItems returns all items from the client's implicit private data collection, with all the necessary access control checks
// Returns a JSON string of all items
func (s *SmartContract) GetItem(ctx contractapi.TransactionContextInterface) (string, error) {
	// Get the clientOrgId from the input, will be used for implicit collection, owner, and state-based endorsement policy
	clientOrgID, err := getClientOrgID(ctx)
	if err != nil {
		return "", err
	}

	// In this scenario, client is only authorized to read/write private data from its own peer, therefore verify client org id matches peer org id.
	err = verifyClientOrgMatchesPeerOrg(clientOrgID)
	if err != nil {
		return "", err
	}

	// Get all items from the implicit private data collection of the client's org
	collection := buildCollectionName(clientOrgID)
	assetIterator, err := ctx.GetStub().GetPrivateDataByRange(collection, "", "")
	if err != nil {
		return "", fmt.Errorf("failed to read from world state: %v", err)
	}
	defer assetIterator.Close()

	var buffer bytes.Buffer
	buffer.WriteString("[\n\t")

	bArrayMemberAlreadyWritten := false
	for assetIterator.HasNext() {
		responseRange, err := assetIterator.Next()
		if err != nil {
			return "", fmt.Errorf("failed to read asset from iterator: %v", err)
		}

		// Add a comma before array members, suppress it for the first array member
		if bArrayMemberAlreadyWritten {
			buffer.WriteString(",\n\t")
		}
		buffer.WriteString(string(responseRange.Value))
		bArrayMemberAlreadyWritten = true
	}
	buffer.WriteString("\n]")

	return buffer.String(), nil
}

// GetItemCount returns the number of items in the client's implicit private data collection
func (s *SmartContract) GetItemCount(ctx contractapi.TransactionContextInterface) (int, error) {
	// Get the clientOrgId from the input, will be used for implicit collection, owner, and state-based endorsement policy
	clientOrgID, err := getClientOrgID(ctx)
	if err != nil {
		return 0, err
	}

	// In this scenario, client is only authorized to read/write private data from its own peer, therefore verify client org id matches peer org id.
	err = verifyClientOrgMatchesPeerOrg(clientOrgID)
	if err != nil {
		return 0, err
	}

	// Get all items from the implicit private data collection of the client's org
	collection := buildCollectionName(clientOrgID)
	assetIterator, err := ctx.GetStub().GetPrivateDataByRange(collection, "", "")
	if err != nil {
		return 0, fmt.Errorf("failed to read from world state: %v", err)
	}
	defer assetIterator.Close()

	itemCount := 0
	for assetIterator.HasNext() {
		_, err := assetIterator.Next()
		if err != nil {
			return 0, fmt.Errorf("failed to read asset from iterator: %v", err)
		}
		itemCount++
	}

	return itemCount, nil
}

// GetItemsInMarket returns all the assets in the market's public ledger, removes the balance assets from the list
// Returns a JSON string of all items
func (s *SmartContract) GetItemsInMarket(ctx contractapi.TransactionContextInterface) (string, error) {
	// Get all items from the implicit private data collection of the client's org
	assetIterator, err := ctx.GetStub().GetStateByPartialCompositeKey("asset", []string{})
	if err != nil {
		return "", fmt.Errorf("failed to read from world state: %v", err)
	}
	defer assetIterator.Close()

	var buffer bytes.Buffer
	buffer.WriteString("[\n\t")

	bArrayMemberAlreadyWritten := false
	for assetIterator.HasNext() {
		responseRange, err := assetIterator.Next()
		if err != nil {
			return "", fmt.Errorf("failed to read asset from iterator: %v", err)
		}
		// if strings.HasPrefix(responseRange.Key, "balance_") {
		// 	continue
		// }
		// Add a comma before array members, suppress it for the first array member
		if bArrayMemberAlreadyWritten {
			buffer.WriteString(",\n\t")
		}
		buffer.WriteString(string(responseRange.Value))
		bArrayMemberAlreadyWritten = true
	}
	buffer.WriteString("\n]")

	return buffer.String(), nil
}
