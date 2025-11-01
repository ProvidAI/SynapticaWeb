# Identity Registry Setup Guide

## Overview

The Identity Registry is an on-chain smart contract deployed on Hedera testnet that allows agents to register their identities in a decentralized manner.

**Contract Address**: `0x34Db979B201a7e5ddCD430C89b63031A574bA4DA`
**Network**: Hedera Testnet
**RPC URL**: `https://testnet.hashio.io/api`

## Quick Start

### 1. Install Dependencies

```bash
pip install web3
```

### 2. Configure Environment

Add to your `.env` file:

```bash
# Hedera Configuration
HEDERA_RPC_URL=https://testnet.hashio.io/api
HEDERA_PRIVATE_KEY=0xyour_private_key_here
IDENTITY_REGISTRY_ADDRESS=0x34Db979B201a7e5ddCD430C89b63031A574bA4DA
```

### 3. Get Testnet HBAR

Visit [Hedera Portal](https://portal.hedera.com/) to get testnet HBAR tokens.

## Registration Script

A comprehensive registration script has been created:

```bash
# Show help
python scripts/register_agents_on_chain.py

# Test registration with one agent
python scripts/register_agents_on_chain.py test

# List registered agents
python scripts/register_agents_on_chain.py list

# Register all agents from database
python scripts/register_agents_on_chain.py register
```

## Contract Functions

### Write Functions (require HBAR payment)

- **`newAgent(string agentDomain, address agentAddress)`** - Register a new agent
  - Fee: 0.005 HBAR
  - Returns: agent ID

- **`updateAgent(uint256 agentId, string newAgentDomain, address newAgentAddress)`** - Update existing agent
  - Free (only agent owner can update)

### Read Functions (free)

- **`getAgent(uint256 agentId)`** - Get agent details by ID
- **`resolveByDomain(string agentDomain)`** - Look up agent by domain
- **`resolveByAddress(address agentAddress)`** - Look up agent by address
- **`getAgentCount()`** - Get total number of registered agents
- **`agentExists(uint256 agentId)`** - Check if agent ID exists
- **`REGISTRATION_FEE()`** - Get current registration fee

## Known Issues

### Issue: `InsufficientFee` Error (0x025dbdd4)

**Status**: Under Investigation

**Description**: When attempting to register agents, the transaction fails with an `InsufficientFee` custom error, even when sending the exact fee amount returned by `REGISTRATION_FEE()` (0.005 HBAR).

**Error Code**: `0x025dbdd4` (InsufficientFee selector)

**Status**: ⚠️  **CONFIRMED CONTRACT BUG**

**Root Cause**: After comprehensive testing, this is confirmed to be a defect in the deployed contract's Solidity code. The contract ALWAYS reverts with `InsufficientFee`, even when sending 10x the required fee.

**Test Results**:
```python
# ALL of these fail with InsufficientFee (0x025dbdd4):
✅ Exact fee:     5000000000000000 wei (0.005 HBAR)  → ❌ InsufficientFee
✅ Double fee:   10000000000000000 wei (0.010 HBAR)  → ❌ InsufficientFee
✅ 10x fee:      50000000000000000 wei (0.050 HBAR)  → ❌ InsufficientFee
✅ Tinybars:     500000 (0.005 HBAR in tinybars)     → ❌ InsufficientFee
```

**Contract Status**:
- ✅ Contract IS deployed (3977 bytes bytecode)
- ✅ Read functions work (getAgentCount, REGISTRATION_FEE)
- ✅ Fee constant (0.005 HBAR) embedded in bytecode
- ❌ Write function (newAgent) ALWAYS fails
- 📊 Zero successful registrations on-chain
- 🔗 View on [Hedera Explorer](https://hashscan.io/testnet/contract/0x34Db979B201a7e5ddCD430C89b63031A574bA4DA)

**Likely Bug in Solidity**:
The contract's `newAgent` function probably has broken fee checking logic:
```solidity
function newAgent(string memory domain, address addr) external payable {
    // BUG: This check always fails
    if (msg.value < REGISTRATION_FEE) {
        revert InsufficientFee();  // Always executes
    }
    // Rest of code never reached
}
```

**Required Fix**:
1. Audit source code to find the fee check bug
2. Redeploy corrected contract
3. Update `IDENTITY_REGISTRY_ADDRESS` in `.env`

**Workaround**: Use local database registration instead:
```bash
python scripts/register_all_agents.py  # Register locally
python scripts/list_all_agents.py      # View agents
```

## Testing

### Test Contract Connectivity

```bash
python -c "
from web3 import Web3
web3 = Web3(Web3.HTTPProvider('https://testnet.hashio.io/api'))
print('Connected:', web3.is_connected())
print('Latest block:', web3.eth.block_number)
"
```

### Read Contract Data

```bash
python -c "
import json
from web3 import Web3

web3 = Web3(Web3.HTTPProvider('https://testnet.hashio.io/api'))

with open('shared/contracts/IdentityRegistry.sol/IdentityRegistry.json') as f:
    abi = json.load(f)['abi']

contract = web3.eth.contract(
    address='0x34Db979B201a7e5ddCD430C89b63031A574bA4DA',
    abi=abi
)

print('Agent Count:', contract.functions.getAgentCount().call())
print('Registration Fee:', web3.from_wei(contract.functions.REGISTRATION_FEE().call(), 'ether'), 'HBAR')
"
```

## Using the Handler Functions

The handler functions in `shared/handlers/identity_registry_handlers.py` provide a Python interface:

```python
from shared.handlers.identity_registry_handlers import (
    register_agent,
    get_agent,
    resolve_by_domain,
    get_agent_count
)

# Register an agent (requires HBAR)
receipt = register_agent("my-agent-001", "0xYourAgentAddress")

# Look up agent
agent = get_agent(1)
agent = resolve_by_domain("my-agent-001")

# Get statistics
count = get_agent_count()
```

## Next Steps

1. **Debug Hedera EVM Value Transfer**
   - Contact Hedera support about `msg.value` handling
   - Review Hedera EVM documentation for payment patterns
   - Test with a simpler contract that just accepts payment

2. **Alternative Registration Method**
   - Consider using Hedera SDK directly instead of web3.py
   - Use Hedera's native smart contract service

3. **Contract Redeployment**
   - Review and potentially redeploy contract with additional logging
   - Add events for debugging fee checks
   - Consider making registration free initially for testing

## Resources

- [Hedera Testnet Portal](https://portal.hedera.com/)
- [Hedera EVM Documentation](https://docs.hedera.com/hedera/core-concepts/smart-contracts)
- [Hashio JSON-RPC Relay](https://docs.hedera.com/hedera/tutorials/smart-contracts/deploy-a-contract-using-the-hedera-json-rpc-relay)

## Support

For issues or questions:
- Check [Hedera Discord](https://hedera.com/discord)
- Review [Hedera GitHub](https://github.com/hashgraph)
- Open an issue in this repository
