'use strict';

const FabricCAServices = require('fabric-ca-client');
const { Wallets, Gateway } = require('fabric-network');
const fs = require('fs');
const path = require('path');
const process = require('process');
const os = require('os');

const rootPath = os.homedir() + '/Desktop/BTP/Fabric/fabric-samples/test-network'
// console.log(rootPath);

async function openWallet(locPath) {
    const walletPath = path.join(process.cwd(), locPath);
    try {
        const wallet = await Wallets.newFileSystemWallet(walletPath);
        console.log(`Wallet path: ${walletPath}`);
        return wallet;
    } catch (error) {
        console.error(`Failed to open wallet in ${walletPath}: ${error}`);
        process.exit(1);
    }
}

async function enrollAdmin(orgNum, wallet) {
    const org = `org${orgNum}`;
    try {
        
        // load the network configuration
        const ccpPath = path.resolve(rootPath, 'organizations', 'peerOrganizations', `${org}.example.com`, `connection-${org}.json`);
        const ccp = JSON.parse(fs.readFileSync(ccpPath, 'utf8'));

        // Create a new CA client for interacting with the CA.
        const caInfo = ccp.certificateAuthorities[`ca.${org}.example.com`];
        const caTLSCACerts = caInfo.tlsCACerts.pem;
        const ca = new FabricCAServices(caInfo.url, { trustedRoots: caTLSCACerts, verify: false }, caInfo.caName);

        // Check to see if we've already enrolled the admin user.
        const identity = await wallet.get('admin');
        if (identity) {
            console.log(`An identity for the admin user admin${orgNum} already exists in the wallet for ${org}`);
            return;
        }

        // Enroll the admin user, and import the new identity into the wallet.
        const enrollment = await ca.enroll({ enrollmentID: 'admin', enrollmentSecret: 'adminpw' });
        const x509Identity = {
            credentials: {
                certificate: enrollment.certificate,
                privateKey: enrollment.key.toBytes(),
            },
            mspId: `Org${orgNum}MSP`,
            type: 'X.509',
        };
        await wallet.put('admin', x509Identity);
        console.log(`Successfully enrolled admin user "admin" and imported it into the wallet ${org}`);

    } catch (error) {
        console.error(`Failed to enroll admin user "admin" for ${org}: ${error}`);
        process.exit(1);
    }
}

async function registerUser(orgNum, wallet) {
    const org = `org${orgNum}`;
    const userName = `appUser${orgNum}`;
    try {
        
        // load the network configuration
        const ccpPath = path.resolve(rootPath, 'organizations', 'peerOrganizations', `${org}.example.com`, `connection-${org}.json`);
        const ccp = JSON.parse(fs.readFileSync(ccpPath, 'utf8'));

        // Create a new CA client for interacting with the CA.
        const caInfo = ccp.certificateAuthorities[`ca.${org}.example.com`];
        const caTLSCACerts = caInfo.tlsCACerts.pem;
        const ca = new FabricCAServices(caInfo.url);
        // Check to see if we've already enrolled the user.
        const userIdentity = await wallet.get(userName);
        if (userIdentity) {
            console.log(`An identity for the user ${userName} already exists in the wallet for ${org}`);
            return;
        }
        
        // Check to see if we've already enrolled the admin user.
        const adminIdentity = await wallet.get('admin');
        if (!adminIdentity) {
            console.log(`An identity for the admin user admin${orgNum} does not exist in the wallet ${org}`);
            return;
        }
        
        // build a user object for authenticating with the CA
        const provider = wallet.getProviderRegistry().getProvider(adminIdentity.type);
        const adminUser = await provider.getUserContext(adminIdentity, 'admin');
        
        // Register the user, enroll the user, and import the new identity into the wallet.
        // console.log('My Own Hell')
        const secret = await ca.register({
            affiliation: `${org}.department1`,
            enrollmentID: userName,
            role: 'client'
        }, adminUser);
        const enrollment = await ca.enroll({
            enrollmentID: userName,
            enrollmentSecret: secret
        });
        const x509Identity = {
            credentials: {
                certificate: enrollment.certificate,
                privateKey: enrollment.key.toBytes(),
            },
            mspId: `Org${orgNum}MSP`,
            type: 'X.509',
        };
        await wallet.put(userName, x509Identity);
        console.log(`Successfully registered and enrolled admin user "${userName}" and imported it into the wallet ${org}`);

    } catch (error) {
        console.error(`Failed to register user "${userName}" for ${org}: ${error}`);
        process.exit(1);
    }
}

async function getGatewayAndContract(orgNum, wallet) {
    const org = `org${orgNum}`;
    const userName = `appUser${orgNum}`;
    try {
        
        // load the network configuration
        const ccpPath = path.resolve(rootPath, 'organizations', 'peerOrganizations', `${org}.example.com`, `connection-${org}.json`);
        const ccp = JSON.parse(fs.readFileSync(ccpPath, 'utf8'));

        const identity = await wallet.get(userName);
        if (!identity) {
            console.log(`An identity for the user "${userName}" does not exist in the wallet`);
            return;
        }

        // Create a new gateway for connecting to our peer node.
        const gateway = new Gateway();
        await gateway.connect(ccp, { wallet, identity: userName, discovery: { enabled: true, asLocalhost: true } });

        // Get the network (channel) our contract is deployed to.
        const network = await gateway.getNetwork('mychannel');

        // Get the contract from the network.
        const contract = network.getContract('basic');

        return [gateway, contract];
    } catch (error) {
        console.error(`Failed to get contract for ${org}: ${error}`);
    }
}

async function invokeFn(contract, fnName, ...args) {
    try {
        const result = await contract.submitTransaction(fnName, args);
        console.log('Transaction has been submitted');
        return result;
    } catch (error) {
        console.error(`Failed to submit transaction: ${error}`);
    }
}

async function main() {
    const wallet1 = await openWallet('wallet1');
    const wallet2 = await openWallet('wallet2');

    await enrollAdmin(1, wallet1);
    await enrollAdmin(2, wallet2);

    await registerUser(1, wallet1);
    await registerUser(2, wallet2);

    // const [gateway1, contract1] = await getGatewayAndContract(1, wallet1);
    // // const [gateway2, contract2] = await getGatewayAndContract(2, wallet2);

    // // invokeFn(contract1, "Insert", 1);
    // // // invokeFn(contract2, "Insert", 2);

    // await gateway1.disconnect();
    // await gateway2.disconnect();
}

main();