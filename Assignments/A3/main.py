import asyncio
import json
import time
from indy import pool, wallet, did, ledger, anoncreds
from indy.error import IndyError, ErrorCode
from os.path import dirname
from indy import blob_storage

async def verifier_get_entities_from_ledger(pool_handle, _did, identifiers, actor, timestamp = None):
    schemas = {}
    cred_defs = {}
    rev_reg_defs = {}
    rev_regs = {}
    for item in identifiers:
        print("\" {} \" -> Get Schema from Ledger".format(actor))
        (received_schema_id, received_schema) = await get_schema(pool_handle, _did, item['schema_id'])
        schemas[received_schema_id] = json.loads(received_schema)

        print("\" {} \" -> Get Credential Definition from Ledger".format(actor))
        (received_cred_def_id, received_cred_def) = \
            await get_cred_def(pool_handle, _did, item['cred_def_id'])
        cred_defs[received_cred_def_id] = json.loads(received_cred_def)

        if 'rev_reg_seq_no' in item and item['rev_reg_seq_no'] is not None:
            print("\" {} \" -> Get Revocation Registry Definition from Ledger".format(actor))
            get_revoc_reg_def_request = await ledger.build_get_revoc_reg_def_request(_did, item['rev_reg_id'])
            get_revoc_reg_def_response = await ensure_previous_request_applied(pool_handle, get_revoc_reg_def_request,
                                                                                 lambda response: response['result']['data'] is not None)
            (rev_reg_id, revoc_reg_def_json) = \
                await ledger.parse_get_revoc_reg_def_response(get_revoc_reg_def_response)
            
            print("\" {} \" -> Get Revocation Registry from Ledger".format(actor))
            if not timestamp: timestamp = item['timestamp']
            get_revoc_reg_request = \
                await ledger.build_get_revoc_reg_request(_did, item['rev_reg_id'], timestamp)
            
            get_revoc_reg_response = \
                await ensure_previous_request_applied(pool_handle, get_revoc_reg_request,
                                                        lambda response: response['result']['data'] is not None)
            
            (rev_reg_id, rev_reg_json, timestamp2) = \
                await ledger.parse_get_revoc_reg_response(get_revoc_reg_response)
            
            rev_regs[rev_reg_id] = {timestamp2: json.loads(rev_reg_json)}
            rev_reg_defs[rev_reg_id] = json.loads(revoc_reg_def_json)
    
    return json.dumps(schemas), json.dumps(cred_defs), json.dumps(rev_reg_defs), json.dumps(rev_regs)

async def prover_get_entities_from_ledger(pool_handle, _did, identifiers, actor, timestamp_from = None, timestamp_to = None):
    schemas = {}
    cred_defs = {}
    rev_states = {}
    for item in identifiers.values():
        print("\" {} \" -> Get Schema from Ledger".format(actor))
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n", item['cred_def_id'])
        (received_schema_id, received_schema) = await get_schema(pool_handle, _did, item['schema_id'])
        schemas[received_schema_id] = json.loads(received_schema)

        print("\" {} \" -> Get Credential Definition from Ledger".format(actor))
        (received_cred_def_id, received_cred_def) = \
            await get_cred_def(pool_handle, _did, item['cred_def_id'])
        cred_defs[received_cred_def_id] = json.loads(received_cred_def)

        if 'rev_reg_seq_no' in item and item['rev_reg_id'] is not None:
            print("\" {} \" -> Get Revocation Registry Definition from Ledger".format(actor))
            get_revoc_reg_def_request = await ledger.build_get_revoc_reg_def_request(_did, item['rev_reg_id'])

            get_revoc_reg_def_response = await ensure_previous_request_applied(pool_handle, get_revoc_reg_def_request,
                                                                                 lambda response: response['result']['data'] is not None)
            (rev_reg_id, revoc_reg_def_json) = \
                await ledger.parse_get_revoc_reg_def_response(get_revoc_reg_def_response)


            print("\" {} \" -> Get Revocation Registry Delta from Ledger".format(actor))
            if not timestamp_to: timestamp_to = int(time.time())
            get_revoc_reg_delta_request = \
                await ledger.build_get_revoc_reg_delta_request(_did, item['rev_reg_id'], timestamp_from, timestamp_to)
            get_revoc_reg_delta_response = \
                await ensure_previous_request_applied(pool_handle, get_revoc_reg_delta_request,
                                                        lambda response: response['result']['data'] is not None)
            (rev_reg_id, revoc_reg_delta_json, t) = \
                await ledger.parse_get_revoc_reg_delta_response(get_revoc_reg_delta_response)
            
            tails_reader_config = json.dumps(
                {
                    'base_dir': dirname(json.loads(revoc_reg_def_json)['value']['tailsLocation']),
                    'uri_pattern': ''
                })
            blob_storage_reader_cfg_handle = await blob_storage.open_reader('default', tails_reader_config)

            print("\" {} \" -> Create Revocation State".format(actor))
            rev_state_json = \
                await anoncreds.verifier_update_revocation_state(blob_storage_reader_cfg_handle, revoc_reg_def_json,
                                                                    revoc_reg_delta_json, item['timestamp'],
                                                                    item['cred_rev_id'])
            rev_states[rev_reg_id] = {t: json.loads(rev_state_json)}
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

async def get_cred_def(pool_handle, _did, cred_def_id):
    get_cred_def_request = await ledger.build_get_cred_def_request(_did, cred_def_id)
    get_cred_def_response = \
        await ensure_previous_request_applied(pool_handle, get_cred_def_request,
                                              lambda response: response['result']['data'] is not None)
    return await ledger.parse_get_cred_def_response(get_cred_def_response)    

async def get_credential_for_referent(search_handle, referent):
    credentials = json.loads(
        await anoncreds.prover_fetch_credentials_for_proof_req(search_handle, referent, 10))
    return credentials[0]['cred_info']


async def get_schema(pool_handle, _did, schema_id):
    get_schema_request = await ledger.build_get_schema_request(_did, schema_id)
    get_schema_response = \
        await ensure_previous_request_applied(pool_handle, get_schema_request,
                                              lambda response: response['result']['data'] is not None)
    return await ledger.parse_get_schema_response(get_schema_response)

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
    PropertyDetails_details = {
        'name': 'PropertyDetails',
        'version': '1.2',
        'attributes': ['owner_first_name', 'owner_last_name',
        'address_of_property', 'residing_since_year', 'property_value_estimate']
        #'realtion_to_applicant']
    }
    government['PropertyDetails_schema_id'], government['PropertyDetails_schema'] = \
        await anoncreds.issuer_create_schema(government['did'], PropertyDetails_details['name'], PropertyDetails_details['version'],
                                             json.dumps(PropertyDetails_details['attributes']))

    print(government['PropertyDetails_schema'])
    PropertyDetails_id = government['PropertyDetails_schema_id']

    schema_request = await ledger.build_schema_request(government['did'], government['PropertyDetails_schema'])
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

    (government['PropertyDetails_cred_def_id'], government['PropertyDetails_cred_def']) = \
        await anoncreds.issuer_create_and_store_credential_def(government['wallet'], government['did'],
                                                               government['PropertyDetails_schema'], PropertyDetails_cred_def['tag'],
                                                               PropertyDetails_cred_def['type'],
                                                               json.dumps(PropertyDetails_cred_def['config']))
   

    print("\"Government\" -> Send credential definition to the ledger")
    cred_def_request = await ledger.build_cred_def_request(government['did'], government['PropertyDetails_cred_def'])
    await ledger.sign_and_submit_request(government['pool'], government['wallet'], government['did'], cred_def_request)
    print("Government credential definition for PropertyDetails created successfully.")

    # STEP 7: NAA Creates credential definition for Bonafide
    print("\n\n--------------------------------------------\n\n")
    print("STEP 7: NAA Creates credential definition for Bonafide")
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
    (naa['bonafide_cred_def_id'], naa['bonafide_cred_def']) = \
        await anoncreds.issuer_create_and_store_credential_def(naa['wallet'], naa['did'],
                                                               naa['bonafide_schema'], bonafide_cred_def['tag'],
                                                               bonafide_cred_def['type'],
                                                               json.dumps(bonafide_cred_def['config']))
    
    # Send the credential definition to the ledger
    print("\"NAA\" -> Send credential definition to the ledger")
    cred_def_request = await ledger.build_cred_def_request(naa['did'], naa['bonafide_cred_def'])
    await ledger.sign_and_submit_request(naa['pool'], naa['wallet'], naa['did'], cred_def_request)
    print("NAA credential definition for Bonafide created successfully.")

    # Continue with the rest of the code...

    # STEP 8: Government issues PropertyDetails Credentials to Rajesh
    print("\n\n--------------------------------------------\n\n")
    print("STEP 8: Government issues PropertyDetails Credentials to Rajesh")
   
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
    
    # Create and send PropertyDetails credential offer from the government
    print("Government creates and sends PropertyDetails credential offer to Rajesh")
    government['PropertyDetails_cred_offer'] = await anoncreds.issuer_create_credential_offer(government['wallet'], government['PropertyDetails_cred_def_id'])
    
    # Send the PropertyDetails credential offer to Rajesh
    print("Government sends PropertyDetails credential offer to Rajesh")
    _Rajesh['PropertyDetails_cred_offer'] = government['PropertyDetails_cred_offer']
    
    # Rajesh prepares a PropertyDetails credential request
    print("\nRajesh prepares PropertyDetails credential request")
    PropertyDetails_cred_offer_object = json.loads(_Rajesh['PropertyDetails_cred_offer'])
    _Rajesh['PropertyDetails_schema_id'] = PropertyDetails_cred_offer_object['schema_id']
    _Rajesh['PropertyDetails_cred_def_id'] = PropertyDetails_cred_offer_object['cred_def_id']
    
    # Rajesh creates and stores a Master Secret in his wallet
    print("Rajesh creates and stores a Master Secret in Wallet")
    _Rajesh['master_secret_id'] = await anoncreds.prover_create_master_secret(_Rajesh['wallet'], None)
    
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
    print("STEP 9: NAA issues BonafideStudents Credentials to Rajesh")
   
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

    cbdc_bank['loan_application_proof_request'] = json.dumps({
        'nonce': nonce,
        'name': 'Loan Application Proof Request',
        'version': '0.1',
        'requested_attributes': {
            'attr1_referent': {
                'name': 'owner_first_name',    
            },
            'attr2_referent': {
                'name': 'owner_last_name',    
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
                'p_value': 2023,  # Minimum year
                'restrictions': [{'cred_def_id': naa['bonafide_cred_def_id']}],
            },
        },
    })

    print("CBDC Bank sends proof request to rajesh")
    _Rajesh['loan_application_proof_request'] = cbdc_bank["loan_application_proof_request"]
    
    print('Rajesh gets credentials for the proof request')
    search_for_loan_application_proof_request = \
        await anoncreds.prover_search_credentials_for_proof_req(_Rajesh['wallet'],
                                                                _Rajesh['loan_application_proof_request'], None)
    print(search_for_loan_application_proof_request)

    cred_for_attr1 = await get_credential_for_referent(search_for_loan_application_proof_request, 'attr1_referent')
    cred_for_attr2 = await get_credential_for_referent(search_for_loan_application_proof_request, 'attr2_referent')
    cred_for_attr3 = await get_credential_for_referent(search_for_loan_application_proof_request, 'attr3_referent')
    cred_for_attr4 = await get_credential_for_referent(search_for_loan_application_proof_request, 'attr4_referent')
    cred_for_attr5 = await get_credential_for_referent(search_for_loan_application_proof_request, 'attr5_referent')
    cred_for_predicate1 = await get_credential_for_referent(search_for_loan_application_proof_request, 'predicate1_referent')
    cred_for_predicate2 = await get_credential_for_referent(search_for_loan_application_proof_request, 'predicate2_referent')
    cred_for_predicate3 = await get_credential_for_referent(search_for_loan_application_proof_request, 'predicate3_referent')
    cred_for_predicate4 = await get_credential_for_referent(search_for_loan_application_proof_request, 'predicate4_referent')


    await anoncreds.prover_close_credentials_search_for_proof_req(search_for_loan_application_proof_request)

    _Rajesh['creds_for_loan_application_proof'] = { cred_for_attr1['referent']: cred_for_attr1,
                                                    cred_for_attr2['referent']: cred_for_attr2,
                                                    cred_for_attr3['referent']: cred_for_attr3,
                                                    cred_for_attr4['referent']: cred_for_attr4,
                                                    cred_for_attr5['referent']: cred_for_attr5,
                                                    cred_for_predicate1['referent']: cred_for_predicate1,
                                                    cred_for_predicate2['referent']: cred_for_predicate2,
                                                    cred_for_predicate3['referent']: cred_for_predicate3,
                                                    cred_for_predicate4['referent']: cred_for_predicate4}
    
    print(_Rajesh['creds_for_loan_application_proof'])

    _Rajesh['schemas_for_loan_application'], _Rajesh['cred_defs_for_loan_application'], \
    _Rajesh['revoc_states_for_loan_application'] = \
        await prover_get_entities_from_ledger(_Rajesh['pool'], _Rajesh['did'],
                                                _Rajesh['creds_for_loan_application_proof'], _Rajesh['name'])
    
    print("\"Rajesh creates loan application proof")

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
    print("STEP 10: Bank validates Rajesh Claims")

    job_application_proof_object = json.loads(cbdc_bank['loan_application_proof'])

    cbdc_bank['schemas_for_loan_application'], cbdc_bank['cred_defs_for_loan_application'], \
    cbdc_bank['revoc_ref_defs_for_loan_application'], cbdc_bank['revoc_regs_for_loan_application'] = \
        await verifier_get_entities_from_ledger(cbdc_bank['pool'], cbdc_bank['did'],
                                                job_application_proof_object['identifiers'], cbdc_bank['name'])
    
    print("\"CBDC Bank\" -> Verify \"Loan Application\" proof from Rajesh")
    assert 'Rajesh' == \
           job_application_proof_object['requested_proof']['self_attested_attrs']['attr1_referent']
    assert 'Kumar' == \
              job_application_proof_object['requested_proof']['self_attested_attrs']['attr2_referent']
    assert 'Pilot Training Programme' == \
                job_application_proof_object['requested_proof']['revealed_attrs']['attr3_referent']['raw']
    assert 'Malancha Road, Kharagpur' == \
                job_application_proof_object['requested_proof']['revealed_attrs']['attr4_referent']['raw']
    assert '2010' == \
                job_application_proof_object['requested_proof']['revealed_attrs']['attr5_referent']['raw']
    
    assert await anoncreds.verifier_verify_proof(cbdc_bank['loan_application_proof_request'], cbdc_bank['loan_application_proof'],
                                                cbdc_bank['schemas_for_loan_application'],
                                                cbdc_bank['cred_defs_for_loan_application'],
                                                cbdc_bank['revoc_ref_defs_for_loan_application'],
                                                cbdc_bank['revoc_regs_for_loan_application'])
    


# Run the asyncio event loop to execute the program
loop = asyncio.get_event_loop()
loop.run_until_complete(run())
 
