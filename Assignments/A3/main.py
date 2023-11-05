# Pranav Mehrotra 20CS10085
# Saransh Sharma 20CS30065
# Shah Dhruv Rajendrabhai 20CS10088
# Vivek Jaiswal 20CS10077


# Import necessary libraries
import asyncio
import json
import time
from indy import pool, wallet, did, ledger, anoncreds
from indy.error import IndyError, ErrorCode
from os.path import dirname
from indy import blob_storage
import subprocess

# Define an asynchronous function that retrieves entities (schemas, credential definitions, revocation registry definitions,
# and revocation registries) from a ledger
async def verifier_get_entities_from_ledger(pool_handle, _did, identifiers, actor, timestamp=None):
    # Initialize dictionaries to store retrieved entities
    retrieved_schemas = {}
    retrieved_cred_defs = {}
    revoc_reg_def = {}
    revoc_reg_registry = {}

    # Iterate over each item in the 'identifiers' list
    for item in identifiers:
        # Print a message indicating that we are getting a schema from the ledger
        print("\" {} \" -> Get Schema from Ledger".format(actor))

        # Retrieve a schema from the ledger and store it in the 'retrieved_schemas' dictionary
        (received_schema_id, received_schema) = await get_schema(pool_handle, _did, item['schema_id'])
        retrieved_schemas[received_schema_id] = json.loads(received_schema)

        # Print a message indicating that we are getting a credential definition from the ledger
        print("\" {} \" -> Get Credential Definition from Ledger".format(actor))

        # Retrieve a credential definition from the ledger and store it in the 'retrieved_cred_defs' dictionary
        (received_cred_def_id, received_cred_def) = await get_cred_def(pool_handle, _did, item['cred_def_id'])
        retrieved_cred_defs[received_cred_def_id] = json.loads(received_cred_def)

        # Check if the item includes information about revocation
        if 'rev_reg_seq_no' in item and item['rev_reg_seq_no'] is not None:
            # Print a message indicating that we are getting a revocation registry definition from the ledger
            print("\" {} \" -> Get Revocation Registry Definition from Ledger".format(actor))

            # Build a request to get the revocation registry definition
            get_revoc_reg_def_request = await ledger.build_get_revoc_reg_def_request(_did, item['rev_reg_id'])

            # Ensure that the previous request is applied and the data is not None
            get_revoc_reg_def_response = await ensure_previous_request_applied(pool_handle, get_revoc_reg_def_request,
                                                                             lambda response: response['result']['data'] is not None)

            # Parse the response to get the revocation registry definition and store it in 'revoc_reg_def' dictionary
            (rev_reg_id, revoc_reg_def_json) = await ledger.parse_get_revoc_reg_def_response(get_revoc_reg_def_response)

            # Print a message indicating that we are getting a revocation registry from the ledger
            print("\" {} \" -> Get Revocation Registry from Ledger".format(actor))

            # If 'timestamp' is not provided, use the timestamp from the item
            if not timestamp:
                timestamp = item['timestamp']

            # Build a request to get the revocation registry
            get_revoc_reg_request = await ledger.build_get_revoc_reg_request(_did, item['rev_reg_id'], timestamp)

            # Ensure that the previous request is applied and the data is not None
            get_revoc_reg_response = await ensure_previous_request_applied(pool_handle, get_revoc_reg_request,
                                                                    lambda response: response['result']['data'] is not None)

            # Parse the response to get the revocation registry and its timestamp, then store it in 'revoc_reg_registry' dictionary
            (rev_reg_id, rev_reg_json, timestamp2) = await ledger.parse_get_revoc_reg_response(get_revoc_reg_response)

            revoc_reg_registry[rev_reg_id] = {timestamp2: json.loads(rev_reg_json)}
            revoc_reg_def[rev_reg_id] = json.loads(revoc_reg_def_json)

    # Return the retrieved entities as JSON strings
    return json.dumps(retrieved_schemas), json.dumps(retrieved_cred_defs), json.dumps(revoc_reg_def), json.dumps(revoc_reg_registry)

# Define an asynchronous function that retrieves entities (schemas, credential definitions, and revocation states) from a ledger
async def prover_get_entities_from_ledger(pool_handle, _did, identifiers, actor, timestamp_from=None, timestamp_to=None):
    
    # Initialize dictionaries to store retrieved entities
    schemas = {}
    cred_defs = {}
    rev_states = {}

    # Iterate over each item in the 'identifiers' dictionary
    for item in identifiers.values():
        # Print a message indicating that we are getting a schema from the ledger
        print("\" {} \" -> Get Schema from Ledger".format(actor))
        
        # Retrieve a schema from the ledger and store it in the 'schemas' dictionary
        (received_schema_id, received_schema) = await get_schema(pool_handle, _did, item['schema_id'])
        schemas[received_schema_id] = json.loads(received_schema)

        # Print a message indicating that we are getting a credential definition from the ledger
        print("\" {} \" -> Get Credential Definition from Ledger".format(actor))
        
        # Retrieve a credential definition from the ledger and store it in the 'cred_defs' dictionary
        (received_cred_def_id, received_cred_def) = await get_cred_def(pool_handle, _did, item['cred_def_id'])
        cred_defs[received_cred_def_id] = json.loads(received_cred_def)

        # Check if the item includes information about revocation
        if 'rev_reg_seq_no' in item and item['rev_reg_id'] is not None:
            # Print a message indicating that we are getting a revocation registry definition from the ledger
            print("\" {} \" -> Get Revocation Registry Definition from Ledger".format(actor))
            
            # Build a request to get the revocation registry definition
            get_revoc_reg_def_request = await ledger.build_get_revoc_reg_def_request(_did, item['rev_reg_id'])
            
            # Ensure that the previous request is applied and the data is not None
            get_revoc_reg_def_response = await ensure_previous_request_applied(pool_handle, get_revoc_reg_def_request,
                                                                             lambda response: response['result']['data'] is not None)
            
            # Parse the response to get the revocation registry definition and store it in 'revoc_reg_def_json'
            (rev_reg_id, revoc_reg_def_json) = await ledger.parse_get_revoc_reg_def_response(get_revoc_reg_def_response)

            # Print a message indicating that we are getting a revocation registry delta from the ledger
            print("\" {} \" -> Get Revocation Registry Delta from Ledger".format(actor))
            
            # If 'timestamp_to' is not provided, use the current time
            if not timestamp_to:
                timestamp_to = int(time.time())
            
            # Build a request to get the revocation registry delta
            get_revoc_reg_delta_request = await ledger.build_get_revoc_reg_delta_request(_did, item['rev_reg_id'], timestamp_from, timestamp_to)
            
            # Ensure that the previous request is applied and the data is not None
            get_revoc_reg_delta_response = await ensure_previous_request_applied(pool_handle, get_revoc_reg_delta_request,
                                                        lambda response: response['result']['data'] is not None)
            
            # Parse the response to get the revocation registry delta and store it in 'revoc_reg_delta_json'
            (rev_reg_id, revoc_reg_delta_json, t) = await ledger.parse_get_revoc_reg_delta_response(get_revoc_reg_delta_response)
            
            # Create configuration for tails reader
            tails_reader_config = json.dumps(
                {
                    'base_dir': dirname(json.loads(revoc_reg_def_json)['value']['tailsLocation']),
                    'uri_pattern': ''
                })

            # Open a reader for blob storage using the tails reader configuration
            blob_storage_reader_cfg_handle = await blob_storage.open_reader('default', tails_reader_config)

            # Print a message indicating that we are creating a revocation state
            print("\" {} \" -> Create Revocation State".format(actor))
            
            # Update the revocation state and store it in 'rev_state_json'
            rev_state_json = await anoncreds.verifier_update_revocation_state(blob_storage_reader_cfg_handle, revoc_reg_def_json,
                                                                    revoc_reg_delta_json, item['timestamp'],
                                                                    item['cred_rev_id'])
            
            # Store the revocation state in the 'rev_states' dictionary
            rev_states[rev_reg_id] = {t: json.loads(rev_state_json)}

    # Return the retrieved entities as JSON strings
    return json.dumps(schemas), json.dumps(cred_defs), json.dumps(rev_states)

# Function to create a wallet for an identity (steward, government, etc.)
async def create_wallet(identity):
    try:
        await wallet.create_wallet(identity["wallet_config"], identity["wallet_credentials"])
    except IndyError as ex:
        if ex.error_code == ErrorCode.WalletAlreadyExistsError:
            pass
    
    try:
        identity["wallet"] = await wallet.open_wallet(identity["wallet_config"], identity["wallet_credentials"])
    except IndyError as ex:
        if ex.error_code == ErrorCode.WalletAlreadyOpenedError:
            pass   

        
# Function to set up a Verinym for an identity (DID and key)
async def getting_verinym(from_, to):
    await create_wallet(to)
    (to["did"], to["key"]) = await did.create_and_store_my_did(to["wallet"], "{}")
    
    from_["info"] = {
        "did": to["did"],
        "verkey": to["key"],
        "role": to.get("role", None)
    }

    await send_nym(from_["pool"], from_["wallet"], from_["did"], from_["info"]["did"], from_["info"]["verkey"], from_["info"]["role"])

# Function to send a nym request (register a new DID on the ledger)
async def send_nym(pool_handle, wallet_handle, _did, new_did, new_key, role):
    nym_request = await ledger.build_nym_request(_did, new_did, new_key, None, role)
    print(f"Nym Request: {nym_request}")
    await ledger.sign_and_submit_request(pool_handle, wallet_handle, _did, nym_request)

# Function to ensure that the previous request is applied
async def ensure_previous_request_applied(pool_handle, checker_request, checker):
    for _ in range(3):
        response = json.loads(await ledger.submit_request(pool_handle, checker_request))
        try:
            if checker(response):
                return json.dumps(response)
        except TypeError:
            pass
        time.sleep(5)

# Define an asynchronous function to retrieve a credential definition from the ledger
async def get_cred_def(pool_handle, _did, cred_def_id):
    # Build a request to get the credential definition
    get_cred_def_request = await ledger.build_get_cred_def_request(_did, cred_def_id)
    
    # Ensure that the previous request is applied and that the data is not None
    get_cred_def_response = await ensure_previous_request_applied(pool_handle, get_cred_def_request,
                                          lambda response: response['result']['data'] is not None)
    
    # Parse the response to obtain the credential definition and return it
    return await ledger.parse_get_cred_def_response(get_cred_def_response)


# Define an asynchronous function to retrieve a credential for a given referent
async def get_credential_for_referent(search_handle, referent):
    # Fetch credentials for the given referent from the search handle, limiting to 10 credentials
    credentials = json.loads(
        await anoncreds.prover_fetch_credentials_for_proof_req(search_handle, referent, 10))
    
    # Extract and return the first credential information from the fetched credentials
    return credentials[0]['cred_info']


# Define an asynchronous function to retrieve a schema from the ledger
async def get_schema(pool_handle, _did, schema_id):
    # Build a request to get the schema using the provided DID and schema ID
    get_schema_request = await ledger.build_get_schema_request(_did, schema_id)
    
    # Ensure that the previous request is applied successfully and that the response contains data
    get_schema_response = await ensure_previous_request_applied(pool_handle, get_schema_request,
                                          lambda response: response['result']['data'] is not None)
    
    # Parse the response to obtain the schema and return it
    return await ledger.parse_get_schema_response(get_schema_response)

async def create_schema(government, schema_name, schema_version, attributes):
    schema_id, schema_json = await anoncreds.issuer_create_schema(
        government['did'],
        schema_name,
        schema_version,
        json.dumps(attributes)
    )

    schema_request = await ledger.build_schema_request(government['did'], schema_json)
    await ledger.sign_and_submit_request(government['pool'], government['wallet'], government['did'], schema_request)

    return schema_id, schema_json

# Define a function to create and store a credential definition
async def create_and_store_credential_def(wallet, did, schema, tag, cred_def_type, config):
    cred_def_id, cred_def_json = await anoncreds.issuer_create_and_store_credential_def(
        wallet, did, schema, tag, cred_def_type, json.dumps(config)
    )
    return cred_def_id, cred_def_json

# Define a function to send the credential definition to the ledger
async def send_credential_def_to_ledger(did, cred_def, pool, wallet):
    cred_def_request = await ledger.build_cred_def_request(did, cred_def)
    await ledger.sign_and_submit_request(pool, wallet, did, cred_def_request)


# Main function to run the Indy  program
async def run():
    
    # Define a dictionary for pool configuration
    pool_ = {
        "name": "pool1"
    }


    print("\n\n--------------------------------------------\n\n")
    # PHASE 1: Connect to the pool
    print(f"PHASE 1: Connect to the pool")

    # Print a message to indicate opening the pool ledger with its name
    print(f"Open Pool Ledger: {pool_['name']}")

    # Set the path to the genesis transaction file for the pool
    pool_['genesis_txn_path'] = "pool1.txn"

    # Create a 'config' entry in the dictionary containing JSON configuration data with the genesis transaction path
    pool_['config'] = json.dumps({"genesis_txn": str(pool_['genesis_txn_path'])})

    # Connecting to the pool and setting the protocol version
    await pool.set_protocol_version(2)

    
    # Create the pool ledger configuration
    try:
        await pool.create_pool_ledger_config(pool_['name'], pool_['config'])
    except IndyError as ex:
        if ex.error_code == ErrorCode.PoolLedgerConfigAlreadyExistsError:
            pass
    
    # run  docker image in case it is not running
    try:
        command = "docker run -itd -p 9701-9708:9701-9708 mailtisen/indy_pool"
        subprocess.run(command, shell=True,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

    # Open the pool ledger and store the returned pool handle in the dictionary
    pool_['handle'] = await pool.open_pool_ledger(pool_['name'], None)
    print("Connected to the pool successfully.")
    print("\n\n--------------------------------------------\n\n")
    

    print("PHASE 2: Configure Steward")
    steward = {
        "name": "Sovrin Steward",
        "wallet_config": json.dumps({"id": "sovrin_steward_wallet"}),
        "wallet_credentials": json.dumps({"key": "steward_wallet_key"}),
        "pool": pool_['handle'],
        "seed": "000000000000000000000000Steward1"
    }
    print(f'Creating a wallet for "{steward["name"]}"')

    # Creating a wallet for the steward and generating a DID
    await create_wallet(steward)
    print(steward['wallet'])

    # Define 'did_info' for the steward containing a seed for DID generation
    steward['did_info'] = json.dumps({'seed': steward['seed']})

    # Print the steward's DID information
    print(steward['did_info'])

    # Generate a DID and cryptographic key pair for the steward and store it in the wallet
    steward['did'], steward['key'] = await did.create_and_store_my_did(steward['wallet'], steward['did_info'])

    # Print a success message after configuring the steward
    print("Steward configured successfully.")
    print("\n\n--------------------------------------------\n\n")
    
    
    print("PHASE 3: Register DID for Government")
    government = {
        'name': 'Government',
        "wallet_config": json.dumps({"id": "government_wallet"}),
        "wallet_credentials": json.dumps({"key": "government_wallet_key"}),
        "pool": pool_['handle'],
        "role": "TRUST_ANCHOR"
    }
    print(f'Creating a wallet for "{government["name"]}"')

    # Register a DID (Verinym) for the government
    await getting_verinym(steward, government)
    print("Government registered successfully.")
    print("\n\n--------------------------------------------\n\n")
    
    
    print("PHASE 4: Register DID for NAA")
    naa = {
        'name': 'NAA',
        "wallet_config": json.dumps({"id": "naa_wallet"}),
        "wallet_credentials": json.dumps({"key": "naa_wallet_key"}),
        "pool": pool_['handle'],
        "role": "TRUST_ANCHOR"
    }
    print(f'Creating a wallet for "{naa["name"]}"')

    # Register a DID (Verinym) for the naa
    await getting_verinym(steward, naa)
    print("NAA registered successfully.")
    print("\n\n--------------------------------------------\n\n")
    
    
    print("PHASE 5: Government Creates credential schema")
    print("\"Government\" -> Create \"PropertyDetails\" Schema")
    PropertyDetails_details = {
        'name': 'PropertyDetails',
        'version': '1.2',
        'attributes': ['owner_first_name', 'owner_last_name',
        'address_of_property', 'residing_since_year', 'property_value_estimate']
        #'realtion_to_applicant']
    }
    property_schema_id, property_schema = await create_schema(
        government, PropertyDetails_details['name'], PropertyDetails_details['version'], PropertyDetails_details['attributes'])
    government['PropertyDetails_schema_id'] = property_schema_id
    government['PropertyDetails_schema'] = property_schema
    
    PropertyDetails_id = government['PropertyDetails_schema_id']
    print("\"Government\" -> Create \"BonafideStudent\" Schema")
    
    bonafide_student = {
        'name': 'BonafideStudent',
        'version': '1.2',
        'attributes': ['student_first_name', 'student_last_name',
        'degree_name', 'student_since_year', 'cgpa']
        }
    
    student_schema_id, student_schema = await create_schema(
        government, bonafide_student['name'], bonafide_student['version'], bonafide_student['attributes'])
    government['bonafide_student_schema_id'] = student_schema_id
    government['bonafide_student_schema'] = student_schema
    bonafide_student_id = government['bonafide_student_schema_id']
    
    print("Government schemas created successfully.")
    print("\n\n--------------------------------------------\n\n")


    # PHASE 6: Government Creates credential definition for PropertyDetails
    print("PHASE 6: Government Creates credential definition for PropertyDetails")
    print("\"Government\" -> Get the schema from the ledger")
   
    get_schema_request = await ledger.build_get_schema_request(government['did'], PropertyDetails_id)
    get_schema_response = await ensure_previous_request_applied(government['pool'], get_schema_request,
                                                                lambda response: response['result']['data'] is not None)
    (government['PropertyDetails_schema_id'], government['PropertyDetails_schema']) = await ledger.parse_get_schema_response(get_schema_response)


    #transcript credential definition
    print("\"Government\" -> Create and store in the wallet. Credential definition")
    PropertyDetails_cred_def = {
        'tag': 'TAG1',
        'type': "CL",
        "config": {"support_revocation": False}
    }

    # Create and store the credential definition for PropertyDetails
    government['PropertyDetails_cred_def_id'], government['PropertyDetails_cred_def'] = await create_and_store_credential_def(
        government['wallet'], government['did'], government['PropertyDetails_schema'], PropertyDetails_cred_def['tag'],
        PropertyDetails_cred_def['type'], PropertyDetails_cred_def['config']
    )

    # Send the credential definition to the ledger
    await send_credential_def_to_ledger(government['did'], government['PropertyDetails_cred_def'], government['pool'], government['wallet'])
    print("Government credential definition for PropertyDetails created successfully.")

    print("\n\n--------------------------------------------\n\n")
    
    
    print("PHASE 7: NAA Creates credential definition for Bonafide")
    print("\"NAA\" -> Get the schema from the ledger")
   
    # Request the schema from the ledger for Bonafide
    get_schema_request = await ledger.build_get_schema_request(naa['did'], bonafide_student_id)
    get_schema_response = await ensure_previous_request_applied(naa['pool'], get_schema_request,
                                                                lambda response: response['result']['data'] is not None)
    (naa['bonafide_schema_id'], naa['bonafide_schema']) = await ledger.parse_get_schema_response(get_schema_response)

    # Create and store the credential definition for Bonafide
    print("\"NAA\" -> Create and store in the wallet. Credential definition")
    bonafide_cred_def = {
        'tag': 'TAG1',
        'type': "CL",
        "config": {"support_revocation": False}
    }
    # Create and store the credential definition for Bonafide
    naa['bonafide_cred_def_id'], naa['bonafide_cred_def'] = await create_and_store_credential_def(
        naa['wallet'], naa['did'], naa['bonafide_schema'], bonafide_cred_def['tag'],
        bonafide_cred_def['type'], bonafide_cred_def['config']
    )

    # Send the credential definition to the ledger
    await send_credential_def_to_ledger(naa['did'], naa['bonafide_cred_def'], naa['pool'], naa['wallet'])
    print("NAA credential definition for Bonafide created successfully.")

    # Setting up Rajesh
    _Rajesh = {
        'name': "Rajesh",
        'wallet_config': json.dumps({'id': "Rajesh_wallet"}),
        'wallet_credentials': json.dumps({'key': 'Rajesh_wallet_key'}),
        'pool': pool_['handle'],
    }
    
    # Create a wallet for Rajesh
    await create_wallet(_Rajesh)
    (_Rajesh['did'], _Rajesh['key']) = await did.create_and_store_my_did(_Rajesh['wallet'], "{}")
    
    # Rajesh creates and stores a Master Secret in his wallet
    print("Rajesh creates and stores a Master Secret in Wallet")
    _Rajesh['master_secret_id'] = await anoncreds.prover_create_master_secret(_Rajesh['wallet'], None)
    print("\n\n--------------------------------------------\n\n")
    

    # PHASE 8: Government issues PropertyDetails Credentials to Rajesh
    print("PHASE 8: Government issues PropertyDetails Credentials to Rajesh")
   
    
    # Create and send PropertyDetails credential offer from the government
    print("Government creates PropertyDetails credential offer to Rajesh")
    government['PropertyDetails_cred_offer'] = await anoncreds.issuer_create_credential_offer(government['wallet'], government['PropertyDetails_cred_def_id'])
    
    # Send the PropertyDetails credential offer to Rajesh
    print("Government sends PropertyDetails credential offer to Rajesh")
    _Rajesh['PropertyDetails_cred_offer'] = government['PropertyDetails_cred_offer']
    
    # Rajesh prepares a PropertyDetails credential request
    print("\nRajesh prepares PropertyDetails credential request")
    PropertyDetails_cred_offer_object = json.loads(_Rajesh['PropertyDetails_cred_offer'])
    _Rajesh['PropertyDetails_schema_id'] = PropertyDetails_cred_offer_object['schema_id']
    _Rajesh['PropertyDetails_cred_def_id'] = PropertyDetails_cred_offer_object['cred_def_id']
    
    
    # Get the PropertyDetails credential definition from the ledger
    print("Rajesh gets PropertyDetails credential definition from the ledger")
    (_Rajesh['government_PropertyDetails_cred_def_id'], _Rajesh['government_PropertyDetails_cred_def']) = \
        await get_cred_def(_Rajesh['pool'], _Rajesh['did'], _Rajesh['PropertyDetails_cred_def_id'])
    
    # Rajesh requests the PropertyDetails credential from the government
    print("Rajesh requests for PropertyDetails credential from the government")
    (_Rajesh['PropertyDetails_cred_request'], _Rajesh['PropertyDetails_cred_request_metadata']) = \
        await anoncreds.prover_create_credential_req(_Rajesh['wallet'], _Rajesh['did'],
                                                     _Rajesh['PropertyDetails_cred_offer'],
                                                     _Rajesh['government_PropertyDetails_cred_def'],
                                                     _Rajesh['master_secret_id'])
    
    # Government stores the PropertyDetails credential request from Rajesh
    government['PropertyDetails_cred_request'] = _Rajesh['PropertyDetails_cred_request']
    
    # Government issues the PropertyDetails credential to Rajesh
    print("\nGovernment issues the PropertyDetails credential to Rajesh")
    government['Rajesh_PropertyDetails_cred_values'] = json.dumps({
        'owner_first_name': {"raw": "Rajesh", "encoded": "1139481716457488690172217916278103335"},
        'owner_last_name': {"raw": "Kumar", "encoded": "5321642780241790123587902456789123452"},
        'address_of_property': {"raw": "Malancha Road, Kharagpur", "encoded": "12434523576212321"},
        'residing_since_year': {"raw": "2010", "encoded": "2010"},
        'property_value_estimate': {"raw": "2000000", "encoded": "2000000"},
    })

    government['PropertyDetails_cred'], _, _ = \
        await anoncreds.issuer_create_credential(government['wallet'], government['PropertyDetails_cred_offer'],
                                                 government['PropertyDetails_cred_request'],
                                                 government['Rajesh_PropertyDetails_cred_values'], None, None)

    # Send the PropertyDetails credential to Rajesh
    print("Government sends the PropertyDetails credential to Rajesh")
    _Rajesh['PropertyDetails_cred'] = government['PropertyDetails_cred']

    # Get the PropertyDetails credential definition for Rajesh from the ledger
    _, _Rajesh['PropertyDetails_cred_def'] = await get_cred_def(_Rajesh['pool'], _Rajesh['did'],
                                                        _Rajesh['PropertyDetails_cred_def_id'])
    
    # Store the PropertyDetails credential in Rajesh's wallet
    await anoncreds.prover_store_credential(_Rajesh['wallet'], None, _Rajesh['PropertyDetails_cred_request_metadata'], 
                                            _Rajesh['PropertyDetails_cred'], _Rajesh['PropertyDetails_cred_def'], None)


        
    print("\n\n--------------------------------------------\n\n")
    
    
    print("PHASE 9: NAA issues BonafideStudents Credentials to Rajesh")
    print("NAA creates and sends BonafideStudents credentail offer to Rajesh")
    naa['BonafideStudents_cred_offer'] = \
        await anoncreds.issuer_create_credential_offer(naa['wallet'],naa['bonafide_cred_def_id'])
    
    print("NAA sends BonafideStudents credential offer to Rajesh")
    _Rajesh['BonafideStudents_cred_offer'] = naa['BonafideStudents_cred_offer']

    print("\nRajesh prepares BonafideStudents credential request")
    BonafideStudents_cred_offer_object = json.loads(_Rajesh['BonafideStudents_cred_offer'])
    _Rajesh['BonafideStudents_schema_id'] = BonafideStudents_cred_offer_object['schema_id']
    _Rajesh['BonafideStudents_cred_def_id'] = BonafideStudents_cred_offer_object['cred_def_id']


    print("Rajesh gets BonafideStudents credential definition from the ledger")
    (_Rajesh['naa_BonafideStudents_cred_def_id'], _Rajesh['naa_BonafideStudents_cred_def']) = \
        await get_cred_def(_Rajesh['pool'], _Rajesh['did'], _Rajesh['BonafideStudents_cred_def_id'])

    
    print("Rajesh requests for BonafideStudents credential from the NAA")
    (_Rajesh['BonafideStudents_cred_request'], _Rajesh['BonafideStudents_cred_request_metadata']) = \
        await anoncreds.prover_create_credential_req(_Rajesh['wallet'], _Rajesh['did'],
                                                     _Rajesh['BonafideStudents_cred_offer'],
                                                     _Rajesh['naa_BonafideStudents_cred_def'],
                                                     _Rajesh['master_secret_id'])
    
    naa['BonafideStudents_cred_request'] = _Rajesh['BonafideStudents_cred_request']

    print("\nNAA issues the BonafideStudents credential to Rajesh")
    
    naa['_Rajesh_BonafideStudents_cred_values'] = json.dumps({
        'student_first_name': {"raw":"Rajesh", "encoded":"1139481716457488690172217916278103335"}, 
        'student_last_name': {"raw":"Kumar","encoded":"5321642780241790123587902456789123452"},
        'degree_name': {"raw":"Pilot Training Programme","encoded":"12434523576212321"},
        'student_since_year':{"raw":"2022", "encoded":"2022"}, 
        'cgpa':{"raw":"8","encoded":"8"}
    })

    naa['BonafideStudents_cred'],_,_ = \
        await anoncreds.issuer_create_credential(naa['wallet'], naa['BonafideStudents_cred_offer'],
                                                 naa['BonafideStudents_cred_request'],
                                                 naa['_Rajesh_BonafideStudents_cred_values'], None, None)

    print("NAA sends the BonafideStudents credential to Rajesh")
    _Rajesh['BonafideStudents_cred'] = naa['BonafideStudents_cred']

    _, _Rajesh['BonafideStudents_cred_def'] = await get_cred_def(_Rajesh['pool'], _Rajesh['did'],
                                                        _Rajesh['BonafideStudents_cred_def_id'])
    
    await anoncreds.prover_store_credential(_Rajesh['wallet'], None, _Rajesh['BonafideStudents_cred_request_metadata'], 
                                            _Rajesh['BonafideStudents_cred'], _Rajesh['BonafideStudents_cred_def'], None)
    

    print("\n\n--------------------------------------------\n\n", _Rajesh['PropertyDetails_cred_def'])
    print("\n\n--------------------------------------------\n\n", _Rajesh['BonafideStudents_cred_def'])
    print("\n\n--------------------------------------------\n\n")      

    cbdc_bank = {
        'name': 'CBDC Bank',
        "wallet_config": json.dumps({"id": "cbdc_bank_wallet"}),
        "wallet_credentials": json.dumps({"key": "cbdc_bank_wallet_key"}),
        "pool": pool_['handle'],
    }
    await create_wallet(cbdc_bank)
    await getting_verinym(steward, cbdc_bank)
    nonce = await anoncreds.generate_nonce()

    # Bank creates a proof request for loan application
    cbdc_bank['loan_application_proof_request'] = json.dumps({
        'nonce': nonce,
        'name': 'Loan Application Proof Request',
        'version': '0.1',
        'requested_attributes': {
            'attr1_referent': {
                'name': 'first_name',    
            },
            'attr2_referent': {
                'name': 'last_name',    
            },
            'attr3_referent': {
                'name': 'degree_name',
                'restrictions': [{'cred_def_id': naa['bonafide_cred_def_id']}],
            },
            'attr4_referent': {
                'name': 'address_of_property',
                'restrictions': [{'cred_def_id': government['PropertyDetails_cred_def_id']}],
            },
            'attr5_referent': {
                'name': 'residing_since_year',
                'restrictions': [{'cred_def_id': government['PropertyDetails_cred_def_id']}],
            }
        },
        'requested_predicates': {
            'predicate1_referent': {
                'name': 'student_since_year',
                'p_type': '>=',
                'p_value': 2019,  # Minimum year
                'restrictions': [{'cred_def_id': naa['bonafide_cred_def_id']}],
            },
            'predicate2_referent': {
                'name': 'cgpa',
                'p_type': '>',
                'p_value': 6,  # Minimum CGPA
                'restrictions': [{'cred_def_id': naa['bonafide_cred_def_id']}],
            },
            'predicate3_referent': {
                'name': 'property_value_estimate',
                'p_type': '>',
                'p_value': 800000,  # Minimum property value
                'restrictions': [{'cred_def_id': government['PropertyDetails_cred_def_id']}],
            },
            'predicate4_referent': {
                'name': 'student_since_year',
                'p_type': '<=',
                'p_value': 2023,  # Maximum year
                'restrictions': [{'cred_def_id': naa['bonafide_cred_def_id']}],
            },
        },
    })

    # Rajesh gets the proof request
    print("CBDC Bank sends proof request to rajesh")
    _Rajesh['loan_application_proof_request'] = cbdc_bank["loan_application_proof_request"]
    
    # Rajesh gets credentials for the proof request
    print('Rajesh gets credentials for the proof request')
    search_for_loan_application_proof_request = \
        await anoncreds.prover_search_credentials_for_proof_req(_Rajesh['wallet'],
                                                                _Rajesh['loan_application_proof_request'], None)
    
    # Rajesh gets the credentials for the attributes in the proof request
    print(search_for_loan_application_proof_request)
    cred_for_attr3 = await get_credential_for_referent(search_for_loan_application_proof_request, 'attr3_referent')
    cred_for_attr4 = await get_credential_for_referent(search_for_loan_application_proof_request, 'attr4_referent')
    cred_for_attr5 = await get_credential_for_referent(search_for_loan_application_proof_request, 'attr5_referent')
    cred_for_predicate1 = await get_credential_for_referent(search_for_loan_application_proof_request, 'predicate1_referent')
    cred_for_predicate2 = await get_credential_for_referent(search_for_loan_application_proof_request, 'predicate2_referent')
    cred_for_predicate3 = await get_credential_for_referent(search_for_loan_application_proof_request, 'predicate3_referent')
    cred_for_predicate4 = await get_credential_for_referent(search_for_loan_application_proof_request, 'predicate4_referent')

    # Rajesh closes the credentials search
    await anoncreds.prover_close_credentials_search_for_proof_req(search_for_loan_application_proof_request)

    # Rajesh creates the proof for the proof request
    _Rajesh['creds_for_loan_application_proof'] = { cred_for_attr3['referent']: cred_for_attr3,
                                                    cred_for_attr4['referent']: cred_for_attr4,
                                                    cred_for_attr5['referent']: cred_for_attr5,
                                                    cred_for_predicate1['referent']: cred_for_predicate1,
                                                    cred_for_predicate2['referent']: cred_for_predicate2,
                                                    cred_for_predicate3['referent']: cred_for_predicate3,
                                                    cred_for_predicate4['referent']: cred_for_predicate4}
    
    print(_Rajesh['creds_for_loan_application_proof'])

    # Rajesh gets the schemas, credential definitions and revocation registries for the proof request
    _Rajesh['schemas_for_loan_application'], _Rajesh['cred_defs_for_loan_application'], \
    _Rajesh['revoc_states_for_loan_application'] = \
        await prover_get_entities_from_ledger(_Rajesh['pool'], _Rajesh['did'],
                                                _Rajesh['creds_for_loan_application_proof'], _Rajesh['name'])
    
    print("\"Rajesh creates loan application proof")

    # Rajesh creates the proof
    _Rajesh['loan_application_requested_creds'] = json.dumps({
        'self_attested_attributes': {
            "attr1_referent": "Rajesh",
            "attr2_referent": "Kumar"
        },
        'requested_attributes': {
            'attr3_referent': {'cred_id': cred_for_attr3['referent'], 'revealed': True},
            'attr4_referent': {'cred_id': cred_for_attr4['referent'], 'revealed': True},
            'attr5_referent': {'cred_id': cred_for_attr5['referent'], 'revealed': True}
        
        },
        'requested_predicates': {
            'predicate1_referent': {'cred_id': cred_for_predicate1['referent']},
            'predicate2_referent': {'cred_id': cred_for_predicate2['referent']},
            'predicate3_referent': {'cred_id': cred_for_predicate3['referent']},
            'predicate4_referent': {'cred_id': cred_for_predicate4['referent']}

        }
    })

    # Rajesh creates the proof
    try:
        _Rajesh['loan_application_proof'] = await anoncreds.prover_create_proof(_Rajesh['wallet'], _Rajesh['loan_application_proof_request'],
                                        _Rajesh['loan_application_requested_creds'], _Rajesh['master_secret_id'],
                                        _Rajesh['schemas_for_loan_application'],
                                        _Rajesh['cred_defs_for_loan_application'],
                                        _Rajesh['revoc_states_for_loan_application'])
    except IndyError as e:
        print(f"An error occurred: {e.error_code} - {e.message}")

    print(_Rajesh['loan_application_proof'])
    print("\"Rajesh\" send proof to cdbc bank")

    cbdc_bank['loan_application_proof'] = _Rajesh['loan_application_proof']

    print("\n\n--------------------------------------------\n\n")
    
    
    print("PHASE 10: Bank validates Rajesh Claims")

    job_application_proof_object = json.loads(cbdc_bank['loan_application_proof'])

    cbdc_bank['schemas_for_loan_application'], cbdc_bank['cred_defs_for_loan_application'], \
    cbdc_bank['revoc_ref_defs_for_loan_application'], cbdc_bank['revoc_regs_for_loan_application'] = \
        await verifier_get_entities_from_ledger(cbdc_bank['pool'], cbdc_bank['did'],
                                                job_application_proof_object['identifiers'], cbdc_bank['name'])
    
    print("\"CBDC Bank\" -> Verify \"Loan Application\" proof from Rajesh")
    
    # Verify the proof provided by Rajesh
    try:
        assert 'Rajesh' == job_application_proof_object['requested_proof']['self_attested_attrs']['attr1_referent']
        assert 'Kumar' == job_application_proof_object['requested_proof']['self_attested_attrs']['attr2_referent']
        assert 'Pilot Training Programme' == job_application_proof_object['requested_proof']['revealed_attrs']['attr3_referent']['raw']
        assert 'Malancha Road, Kharagpur' == job_application_proof_object['requested_proof']['revealed_attrs']['attr4_referent']['raw']
        assert '2010' == job_application_proof_object['requested_proof']['revealed_attrs']['attr5_referent']['raw']

        assert await anoncreds.verifier_verify_proof(cbdc_bank['loan_application_proof_request'], cbdc_bank['loan_application_proof'],
                                                cbdc_bank['schemas_for_loan_application'],
                                                cbdc_bank['cred_defs_for_loan_application'],
                                                cbdc_bank['revoc_ref_defs_for_loan_application'],
                                                cbdc_bank['revoc_regs_for_loan_application'])
        print("Verification of proof successful!!")
    except AssertionError as e:
        print("Proof Verification Failed!!")

# Run the asyncio event loop to execute the program
loop = asyncio.get_event_loop()
loop.run_until_complete(run())
 