const { Gateway, Wallets, X509WalletMixin } = require('fabric-network');
const fs = require('fs');
const path = require('path');

const rootPath = '/home/saransh03sharma/Desktop/fabric/fabric-samples/test-network'

async function main() {
  try {
    const orgMSPID = 'Org1MSP'; // Modify with your organization's MSP ID
    ccpPath = path.resolve(rootPath, 'organizations', 'peerOrganizations', 'org1.example.com', 'connection-org1.json');
    let ccp = JSON.parse(fs.readFileSync(ccpPath, 'utf8'));
    console.log(ccpPath)
    const channelName = 'mychannel';
    const chaincodeName = 'basic';

    const walletPath = path.join(process.cwd(), 'wallet');
    const wallet = await Wallets.newFileSystemWallet(walletPath);
    console.log(`Wallet path: ${walletPath}`);

    const gateway = new Gateway();

    await gateway.connect(ccp, {
      wallet,
      identity: 'appUser',
      discovery: { enabled: true, asLocalhost: true },
    });

    
    const network = await gateway.getNetwork(channelName);
    const contract = network.getContract(chaincodeName);

    // Invoke the chaincode to initialize the ledger
    await contract.submitTransaction('InitLedger');

    console.log('Ledger initialized successfully.');

    // Query the ledger to get all assets
    const queryResult = await contract.evaluateTransaction('GetAllAssets');
    console.log(`All assets: ${queryResult.toString()}`);

    await gateway.disconnect();
  } catch (error) {
    console.error(`Error: ${error.message}`);
  }
}

main();

