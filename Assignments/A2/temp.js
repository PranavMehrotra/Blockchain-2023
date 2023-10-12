var deleteKajmak = async function(username,userOrg,kajmakData) {
    var error_message = null;
    try {
         var array = kajmakData.split("-");
         console.log(array);
         var key = array[0]
         var name = array[1]
         var owner = array[2]
         var animal = array[3]
         var location = array[4]
         var quantity = array[5]
         var productionDate = array[6]
         var expirationDate = array[7]
         var client = await getClientForOrg(userOrg,username);
         logger.debug('Successfully got the fabric client for the organization "%s"', userOrg);
         var channel = client.getChannel('mychannel');
         if(!channel) {
              let message = util.format('Channel %s was not defined in the connection profile', channelName);
              logger.error(message);
              throw new Error(message);
         }
         var targets = null;
         if(userOrg == "Org1") {
              targets = ['peer0.org1.example.com'];
         } else if(userOrg == "Org2") {
              targets = ['peer0.org2.example.com'];
         }
         var tx_id = client.newTransactionID();
         console.log("Assigning transaction_id: ", tx_id._transaction_id);
         var tx_id_string = tx_id.getTransactionID();
         var request = {
              targets: targets,
              chaincodeId: 'kajmak-app',
              fcn: 'deleteKajmak',
              args: [key, name, owner, animal, location, quantity, productionDate, expirationDate],
              chainId: channel,
              txId: tx_id
         };
         let results = await channel.sendTransactionProposal(request);
         var proposalResponses = results[0];
         var proposal = results[1];
         let isProposalGood = false;
         if (proposalResponses && proposalResponses[0].response && proposalResponses[0].response.status === 200) {
              isProposalGood = true;
              console.log('Transaction proposal was good');
         } else {
              console.error('Transaction proposal was bad');
         }
         if (isProposalGood) {
              console.log(util.format('Successfully sent Proposal and received ProposalResponse: Status - %s, message - "%s"', proposalResponses[0].response.status, proposalResponses[0].response.message));
              var promises = [];
              let event_hubs = channel.getChannelEventHubsForOrg();
              event_hubs.forEach((eh) => {
              logger.debug('invokeDeleteKajmakEventPromise - setting up event');
              console.log(eh);
              let invokeEventPromise = new Promise((resolve, reject) => {
                   let regid = null;
                   let event_timeout = setTimeout(() => {
                   if(regid) {
                   let message = 'REQUEST_TIMEOUT:' + eh.getPeerAddr();
                   logger.error(message);
                   eh.unregisterChaincodeEvent(regid);
                   eh.disconnect();
                   }
                   reject();
                   }, 20000);
              regid = eh.registerChaincodeEvent('kajmak-app', 'deleteEvent',(event, block_num, txnid, status) => {
              console.log('Successfully got a chaincode event with transid:'+ txnid + ' with status:'+status);
              let event_payload = event.payload.toString();
              console.log(event_payload);
              if(event_payload.indexOf(array[0]) > -1) {
                   clearTimeout(event_timeout);
                   //Chaincode event listeners are meant to run continuously
                   //Therefore the default to automatically unregister is false
                   //So in this case we want to shutdown the event listener once
                   // we see the event with the correct payload
                   eh.unregisterChaincodeEvent(regid);
                   console.log('Successfully received the chaincode event on block number '+ block_num);
                   resolve(event_payload);
              } else {
                   console.log('Successfully got chaincode event ... just not the one we are looking for on block number '+ block_num);
              }
              }, (err) => {
              clearTimeout(event_timeout);
              logger.error(err);
              reject(err);
              }
              //no options specified
              //startBlock will default to latest
              //endBlock will default to MAX
              //unregister will default to false
              //disconnect will default to false
              );
              eh.connect(true);
         });
         promises.push(invokeEventPromise);
         console.log(eh.isconnected());
         });
    
         var requestMain = {
              txId: tx_id,
              proposalResponses: proposalResponses,
              proposal: proposal
         };
         var sendPromise = channel.sendTransaction(requestMain);
         promises.push(sendPromise);
         let results = await Promise.all(promises);
         logger.debug(util.format('------->>> R E S P O N S E : %j', results));
         let response = results.pop(); //  orderer results are last in the results
         if (response.status === 'SUCCESS') {
              logger.info('Successfully sent transaction to the orderer.');
         } else {
              error_message = util.format('Failed to order the transaction. Error code: %s',response.status);
              logger.debug(error_message);
         }
    
         // now see what each of the event hubs reported
         for(let i in results) {
              let event_hub_result = results[i];
              let event_hub = event_hubs[i];
              logger.debug('Event results for event hub :%s',event_hub.getPeerAddr());
              if(typeof event_hub_result === 'string') {
                   logger.debug(event_hub_result);
                   var rezultat = {event_payload : event_hub_result};
                   return rezultat;
              } else {
                   if(!error_message) error_message = event_hub_result.toString();
                   logger.debug(event_hub_result.toString());
              }
         }
    } else {
         error_message = util.format('Failed to send Proposal and receive all good ProposalResponse');
         logger.debug(error_message);
    }
} catch(error) {
    logger.error('Failed to delete kajmak with error: %s', error.toString());
}
};