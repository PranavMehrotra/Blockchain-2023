import asyncio
import json
from indy import pool, wallet, did, ledger
from indy.error import IndyError, ErrorCode

# Function to create a wallet for an identity (steward, government, etc.)
async def create_wallet(identity):
    print('\"{}\" is creating wallet'.format(identity['name']))
    try:
        await wallet.create_wallet(identity['wallet_config'], identity['wallet_credentials'])
    except IndyError as ex:
        if ex.error_code == ErrorCode.WalletAlreadyExistsError:
            pass
    identity['wallet'] = await wallet.open_wallet(identity['wallet_config'], identity['wallet_credentials'])

# Function to set up a Verinym for an identity (DID and key)
async def getting_verinym(from_, to):
    await create_wallet(to)

    (to['did'], to['key']) = await did.create_and_store_my_did(to['wallet'], "{}")

    from_['info'] = {
        'did': to['did'],
        'verkey': to['key'],
        'role': to['role'] or None
    }

    await send_nym(from_['pool'], from_['wallet'], from_['did'], from_['info']['did'], from_['info']['verkey'], from_['info']['role'])

# Function to send a nym request (register a new DID on the ledger)
async def send_nym(pool_handle, wallet_handle, _did, new_did, new_key, role):
    # Build a nym request to register a new DID
    nym_request = await ledger.build_nym_request(_did, new_did, new_key, None, role)
    print(nym_request)
    # Sign and submit the nym request to the ledger
    await ledger.sign_and_submit_request(pool_handle, wallet_handle, _did, nym_request)

# Main function to run the Indy demo program
async def run():
    print("Indy demo program")

    print("STEP1 Connect to pool")
    pool_ = {
        "name": "pool1"
    }
    print("Open Pool Ledger: {}".format(pool_['name']))
    pool_['genesis_txn_path'] = "pool1.txn"
    pool_['config'] = json.dumps({"genesis_txn": str(pool_['genesis_txn_path'])})
    print(pool_)

    # Connecting to the pool and setting the protocol version
    await pool.set_protocol_version(2)

    try:
        await pool.create_pool_ledger_config(pool_['name'], pool_['config'])
    except IndyError as ex:
        if ex.error_code == ErrorCode.PoolLedgerConfigAlreadyExistsError:
            pass
    pool_['handle'] = await pool.open_pool_ledger(pool_['name'], None)

    print(pool_['handle'])

    print("STEP2 Configuring Steward")
    steward = {
        "name": "Sovrin Steward",
        "wallet_config": json.dumps({"id": "sovrin_steward_wallet"}),
        "wallet_credentials": json.dumps({"key": "steward_wallet_key"}),
        "pool": pool_['handle'],
        "seed": "000000000000000000000000Steward1"
    }
    print(steward)

    # Creating a wallet for the steward and generating a DID
    await create_wallet(steward)
    print(steward['wallet'])

    steward['did_info'] = json.dumps({'seed': steward['seed']})
    print(steward['did_info'])

    steward['did'], steward['key'] = await did.create_and_store_my_did(steward['wallet'], steward['did_info'])

    print("STEP3 Register DID for Government")
    print("\n\n\n=================================")
    print("== Government registering verinym  ==")
    print('--------------------------------------')

    government = {
        'name': 'Government',
        "wallet_config": json.dumps({"id": "government_wallet"}),
        "wallet_credentials": json.dumps({"key": "government_wallet_key"}),
        "pool": pool_['handle'],
        "role": "TRUST_ANCHOR"
    }

    # Register a DID (Verinym) for the government
    await getting_verinym(steward, government)

    print("STEP3 Register DID for NAA")
    print("\n\n\n=================================")
    print("== NAA registering verinym  ==")
    print('--------------------------------------')

    naa = {
        'name': 'NAA',
        "wallet_config": json.dumps({"id": "naa_wallet"}),
        "wallet_credentials": json.dumps({"key": "naa_wallet_key"}),
        "pool": pool_['handle'],
        "role": "TRUST_ANCHOR"
    }

    # Register a DID (Verinym) for the naa
    await getting_verinym(steward, naa)

# Run the asyncio event loop to execute the program
loop = asyncio.get_event_loop()
loop.run_until_complete(run())

