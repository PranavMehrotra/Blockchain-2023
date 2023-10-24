import asyncio
import json
import time
from indy import pool, wallet, did, ledger, anoncreds
from indy.error import IndyError, ErrorCode


# Function to create a wallet for an identity (steward, government, etc.)
async def create_wallet(identity):
    try:
        await wallet.create_wallet(identity["wallet_config"], identity["wallet_credentials"])
    except IndyError as ex:
        if ex.error_code == ErrorCode.WalletAlreadyExistsError:
            pass
    identity["wallet"] = await wallet.open_wallet(identity["wallet_config"], identity["wallet_credentials"])

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

# Main function to run the Indy  program
async def run():
    print("Indy program")

    
    pool_ = {
        "name": "pool1"
    }

    print("\n\n--------------------------------------------\n\n")
    print(f"STEP 1: Connect to the pool")
    print(f"Open Pool Ledger: {pool_['name']}")
    
    pool_['genesis_txn_path'] = "pool1.txn"
    pool_['config'] = json.dumps({"genesis_txn": str(pool_['genesis_txn_path'])})
    

    # Connecting to the pool and setting the protocol version
    await pool.set_protocol_version(2)

    try:
        await pool.create_pool_ledger_config(pool_['name'], pool_['config'])
    except IndyError as ex:
        if ex.error_code == ErrorCode.PoolLedgerConfigAlreadyExistsError:
            pass
    print("Connected to the pool successfully.")

    pool_['handle'] = await pool.open_pool_ledger(pool_['name'], None)

    
    steward = {
        "name": "Sovrin Steward",
        "wallet_config": json.dumps({"id": "sovrin_steward_wallet"}),
        "wallet_credentials": json.dumps({"key": "steward_wallet_key"}),
        "pool": pool_['handle'],
        "seed": "000000000000000000000000Steward1"
    }
    
    print("\n\n--------------------------------------------\n\n")
    print("STEP 2: Configure Steward")
    print(f'Creating a wallet for "{steward["name"]}"')

    # Creating a wallet for the steward and generating a DID
    await create_wallet(steward)
    print(steward['wallet'])

    steward['did_info'] = json.dumps({'seed': steward['seed']})
    print(steward['did_info'])

    steward['did'], steward['key'] = await did.create_and_store_my_did(steward['wallet'], steward['did_info'])
    print("Steward configured successfully.")

   
    government = {
        'name': 'Government',
        "wallet_config": json.dumps({"id": "government_wallet"}),
        "wallet_credentials": json.dumps({"key": "government_wallet_key"}),
        "pool": pool_['handle'],
        "role": "TRUST_ANCHOR"
    }

    print("\n\n--------------------------------------------\n\n")
    print("STEP 3: Register DID for Government")
    print(f'Creating a wallet for "{government["name"]}"')

    # Register a DID (Verinym) for the government
    await getting_verinym(steward, government)
    print("Government registered successfully.")
    
    naa = {
        'name': 'NAA',
        "wallet_config": json.dumps({"id": "naa_wallet"}),
        "wallet_credentials": json.dumps({"key": "naa_wallet_key"}),
        "pool": pool_['handle'],
        "role": "TRUST_ANCHOR"
    }

    print("\n\n--------------------------------------------\n\n")
    print("STEP 4: Register DID for NAA")
    print(f'Creating a wallet for "{naa["name"]}"')

    # Register a DID (Verinym) for the naa
    await getting_verinym(steward, naa)
    print("NAA registered successfully.")

    print("\n\n--------------------------------------------\n\n")
    print("STEP 5: Government Creates credential schema")
    print("\"Government\" -> Create \"PropertyDetails\" Schema")
    property_details = {
        'name': 'PropertyDetails',
        'version': '1.2',
        'attributes': ['owner_first_name', 'owner_last_name',
        'address_of_property', 'residing_since_year', 'property_value_estimate',
        'realtion_to_applicant']
    }
    government['property_details_schema_id'], government['property_details_schema'] = \
        await anoncreds.issuer_create_schema(government['did'], property_details['name'], property_details['version'],
                                             json.dumps(property_details['attributes']))

    print(government['property_details_schema'])
    property_details_id = government['property_details_schema_id']

    schema_request = await ledger.build_schema_request(government['did'], government['property_details_schema'])
    await ledger.sign_and_submit_request(government['pool'], government['wallet'], government['did'], schema_request)

    print("\"Government\" -> Create \"BonafideStudent\" Schema")
    bonafide_student = {
        'name': 'BonafideStudent',
        'version': '1.2',
        'attributes': ['student_first_name', 'student_last_name',
        'degree_name', 'student_since_year', 'cgpa']
        }
    government['bonafide_student_schema_id'], government['bonafide_student_schema'] = \
        await anoncreds.issuer_create_schema(government['did'], bonafide_student['name'], bonafide_student['version'],
                                             json.dumps(bonafide_student['attributes']))

    
    bonafide_student_id = government['bonafide_student_schema_id']

    schema_request = await ledger.build_schema_request(government['did'], government['bonafide_student_schema'])
    await ledger.sign_and_submit_request(government['pool'], government['wallet'], government['did'], schema_request)

    print("Government schemas created successfully.")

    # STEP 6: Government Creates credential definition for PropertyDetails
    print("\n\n--------------------------------------------\n\n")
    print("STEP 6: Government Creates credential definition for PropertyDetails")
    print("\"Government\" -> Get the schema from the ledger")
   
    get_schema_request = await ledger.build_get_schema_request(government['did'], property_details_id)
    get_schema_response = await ensure_previous_request_applied(government['pool'], get_schema_request,
                                                                lambda response: response['result']['data'] is not None)
    (government['property_details_schema_id'], government['property_details_schema']) = await ledger.parse_get_schema_response(get_schema_response)


    #transcript credential definition
    print("\"Government\" -> Create and store in the wallet. Credential definition")
    property_cred_def = {
        'tag': 'TAG1',
        'type': "CL",
        "config": {"support_revocation": False}
    }

    (government['property_cred_def_id'], government['property_cred_def']) = \
        await anoncreds.issuer_create_and_store_credential_def(government['wallet'], government['did'],
                                                               government['property_details_schema'], property_cred_def['tag'],
                                                               property_cred_def['type'],
                                                               json.dumps(property_cred_def['config']))
   

    print("\"Government\" -> Send credential definition to the ledger")
    cred_def_request = await ledger.build_cred_def_request(government['did'], government['property_cred_def'])
    await ledger.sign_and_submit_request(government['pool'], government['wallet'], government['did'], cred_def_request)
    print("Government credential definition for PropertyDetails created successfully.")


    # STEP 7: NAA Creates credential definition for Bonafide
    print("\n\n--------------------------------------------\n\n")
    print("STEP 7: NAA Creates credential definition for Bonafide")
    print("\"NAA\" -> Get the schema from the ledger")
   
    get_schema_request = await ledger.build_get_schema_request(naa['did'], bonafide_student_id)
    get_schema_response = await ensure_previous_request_applied(naa['pool'], get_schema_request,
                                                                lambda response: response['result']['data'] is not None)
    (naa['bonafide_details_schema_id'], naa['bonafide_details_schema']) = await ledger.parse_get_schema_response(get_schema_response)


    #transcript credential definition
    print("\"NAA\" -> Create and store in the wallet. Credential definition")
    bonafide_cred_def = {
        'tag': 'TAG1',
        'type': "CL",
        "config": {"support_revocation": False}
    }

    (naa['bonafide_cred_def_id'], naa['bonafide_cred_def']) = \
        await anoncreds.issuer_create_and_store_credential_def(naa['wallet'], naa['did'],
                                                               naa['bonafide_details_schema'], bonafide_cred_def['tag'],
                                                               bonafide_cred_def['type'],
                                                               json.dumps(bonafide_cred_def['config']))
   

    print("\"NAA\" -> Send credential definition to the ledger")
    cred_def_request = await ledger.build_cred_def_request(naa['did'], naa['bonafide_cred_def'])
    await ledger.sign_and_submit_request(naa['pool'], naa['wallet'], naa['did'], cred_def_request)
    print("NAA credential definition for Bonafide created successfully.")


# Run the asyncio event loop to execute the program
loop = asyncio.get_event_loop()
loop.run_until_complete(run())

