const { Gateway, Wallets, X509WalletMixin } = require('fabric-network');
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const os = require('os');

// input rootPath
const rootPath = os.homedir() + '/Desktop/BTP/Fabric/fabric-samples/test-network'
// console.log(rootPath);

async function main() {
  try {
    // const orgMSPID = 'Org1MSP'; // Modify with your organization's MSP ID
    /**
     * Take Organisation as input from user, give 2 options and let them enter 1 or 2
     */
    var org = 'org1'; // Modify with your organization's name
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });
    // Give 2 options and let them enter 1 or 2
    const orgInput = await new Promise((resolve) => {
      rl.question('Enter 1 for Org1 and 2 for Org2: ', (answer) => {
        resolve(answer);
      });
    });
    if (orgInput == '1') {
      org = 'org1';
    }
    else if (orgInput == '2') {
      org = 'org2';
    }
    else {
      console.log('Wrong input');
      // Exit the program
      rl.close();
      return;
    }
    ccpPath = path.resolve(rootPath, 'organizations', 'peerOrganizations', org + '.example.com', 'connection-'+org+'.json');
    let ccp = JSON.parse(fs.readFileSync(ccpPath, 'utf8'));
    console.log('CCP Path: ' + ccpPath);
    const channelName = 'mychannel';
    const chaincodeName = 'basic';

    const walletPath = path.join(process.cwd(), 'wallet');
    const wallet = await Wallets.newFileSystemWallet(walletPath);
    console.log(`Wallet path: ${walletPath}`);

    const gateway = new Gateway();

    await gateway.connect(ccp, {
      wallet: wallet,
      identity: 'appUser',
      discovery: { enabled: true, asLocalhost: true },
    });

    
    const network = await gateway.getNetwork(channelName);
    const contract = network.getContract(chaincodeName);
    // Create a items_wishlist array, to which we will add items from Wishlist function and check in listener if the item is in items_wishlist
    var items_wishlist = [];

    // Create a event listener on AddToMarket Event, check if the item is in items_wishlist, if yes, call BuyFromMarket
    // const listener = async (err, event, blockNumber, transactionId, status) => {
    //   if (err) {
    //     console.error(err);
    //     return;
    //   }
    //   // Get the payload from the chaincode event
    //   let event_payload = event.payload.toString();
    //   console.log(event_payload);
    //   // Check if the item is in items_wishlist, if yes, call BuyFromMarket
    //   if (items_wishlist.includes(event_payload)) {
    //     await BuyFromMarket(contract, ['BuyFromMarket', event_payload]);
    //   }
    // }

    await contract.addContractListener(async (event) => {
      // console.log('Inside listener');
      // if (err) {
      //   console.error(err);
      //   return;
      // }
      // Get the payload from the chaincode event
      let event_payload = event.payload.toString();
      // console.log(event_payload);
      // Check if the item is in items_wishlist, if yes, call BuyFromMarket
      if (items_wishlist.includes(event_payload)) {
        await BuyFromMarket(contract, ['BuyFromMarket', event_payload]);
        // await GetBalance(contract);
        // Remove item from items_wishlist
        items_wishlist = items_wishlist.filter(item => item !== event_payload);
        // console.log(items_wishlist);
      }
      // console.log(`Block Number: ${blockNumber} Transaction ID: ${transactionId} Status: ${status}`);
    }, 'AddToMarket');
    
    // console.log('Added contract listener\n\n');
    let isExit = false;

    while (!isExit) {
      /**
       * Take Inputs, add if else and call necessary functions accordingly
       * Scan whole line and then split it into words(by space), clean the words
       * If first word is AddItem, call AddItem function, and so on
       * If first word is exit, break the loop
       * Else wrong input, continue
      */
      // Use a Promise to wait for user input
      const input = await new Promise((resolve) => {
        rl.question('Enter Command: ', (answer) => {
          resolve(answer);
        });
      });

      // Remove extra spaces between words and split the input
      const cleanedInput = input.replace(/\s+/g, ' ').trim();
      let args = cleanedInput.split(' ');
      args[0] = args[0].toUpperCase();

        // Switch case for handling different commands
        switch (args[0]) {
          case 'ADD_ITEM':
            await AddItem(contract, args);
            break;
          case 'ADD_MONEY':
            await AddBalance(contract, args);
            break;
          case 'QUERY_BALANCE':
            await GetBalance(contract);
            break;
          case 'GET_ITEM':
            await GetItem(contract);
            break;
          case 'ENLIST_ITEM':
            await AddToMarket(contract, args);
            break;
          case 'ALL_ITEMS':
            await GetItemsInMarket(contract);
            break;
          case 'WISHLIST':
            Wishlist(items_wishlist, args);
            break;
          case 'EXIT':
            console.log('Bye! Thank you for using our service');
            isExit = true;
            rl.close();
            break;
          default:
            console.log('Wrong command');
            break;
        }
      // if (isExit) {
      //   rl.close();
      //   break;
      // }
    }

    // // Sleep for 100 seconds
    // await new Promise(resolve => setTimeout(resolve, 100000));

    await gateway.disconnect();
  } catch (error) {
    console.error(`Error: ${error.message}`);
  }
}

main();


// Function for handling AddItem, take contract and args(string array) as input
async function AddItem(contract, args) {
  // Check len(args)
  if (args.length != 4) {
    console.log('Wrong number of arguments');
    return;
  }
  // Prepare transient data, arg[2] and arg[3] are integers
  const assetProperties = {
    Name: args[1],
    NumItems: parseInt(args[2], 10),
    Price: parseInt(args[3], 10)
  };
  const assetPropertiesString = JSON.stringify(assetProperties);
  const transientData = {
    "asset_properties": Buffer.from(assetPropertiesString).toString('base64').replace(/\n/g, '')
  };

  console.log('Transient data: ' + transientData);

  // Create a transaction
  const transaction = contract.createTransaction('AddItem');

  // Set the transient data
  transaction.setTransient(transientData);

  const response = await transaction.submit();
  console.log(`Result: ${response.toString()}`);
}

// Function for handling AddBalance, take contract and args(string array) as input
async function AddBalance(contract, args) {
  // Check len(args)
  if (args.length != 2) {
    console.log('Wrong number of arguments');
    return;
  }
  // Prepare transient data
  const assetProperties = {
    Balance: parseInt(args[1], 10)
  };
  const assetPropertiesString = JSON.stringify(assetProperties);
  const transientData = {
    "balance": Buffer.from(assetPropertiesString).toString('base64').replace(/\n/g, '')
  };

  console.log('Transient data: ' + transientData);

  // Create a transaction
  const transaction = contract.createTransaction('AddBalance');

  // Set the transient data
  transaction.setTransient(transientData);

  const response = await transaction.submit();
  console.log(`Result: ${response.toString()}`);
}

// Function for handling AddToMarket, take contract and args(string array) as input, also pass args as arguments and not transient data
async function AddToMarket(contract, args) {
  // Check len(args)
  if (args.length != 3) {
    console.log('Wrong number of arguments');
    return;
  }
  // Create a transaction
  const transaction = contract.createTransaction('AddToMarket');

  // Submit the transaction, with arguments
  const response = await transaction.submit(args[1], args[2]);  // Name and Price
  console.log(`Result: ${response.toString()}`);
}

//Function for handling BuyFromMarket, take contract and args(string array) as input
async function BuyFromMarket(contract, args) {
  // Check len(args)
  if (args.length != 2) {
    console.log('Wrong number of arguments');
    return;
  }
  // Create a transaction
  const transaction = contract.createTransaction('BuyFromMarket');

  // Submit the transaction, with arguments
  const response = await transaction.submit(args[1]);  // Name
  console.log(`Result: ${response.toString()}`);
}



//Function for handling Wishlist, take items_wishlist and args(string array) as input, and add item to items_wishlist
function Wishlist(items_wishlist, args) {
  // Check len(args)
  if (args.length != 2) {
    console.log('Wrong number of arguments');
    return;
  }
  // Add item to items_wishlist
  items_wishlist.push(args[1]);
  return;
}




/**** QUERIES ****/
// Function for handling GetBalance, take contract as input
async function GetBalance(contract) {
  // Create Transaction to GetAllItems (Query)
  const transaction = contract.createTransaction('GetBalance');
  const result = await transaction.evaluate();
  console.log(`Result: ${result.toString()}`);
}

// Function for handling GetItem, take contract as input
async function GetItem(contract) {
  // Create Transaction to GetItem (Query)
  const transaction = contract.createTransaction('GetItem');
  const result = await transaction.evaluate();
  console.log(`Result: ${result.toString()}`);
}

// Function for handling GetItemsInMarket, take contract as input
async function GetItemsInMarket(contract) {
  // Create Transaction to GetItemsInMarket (Query)
  const transaction = contract.createTransaction('GetItemsInMarket');
  const result = await transaction.evaluate();
  console.log(`Result: ${result.toString()}`);
}
