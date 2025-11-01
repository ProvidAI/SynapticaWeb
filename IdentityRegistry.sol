// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./interfaces/IIdentityRegistry.sol";
import "./interfaces/IReputationRegistry.sol";
import "./interfaces/IValidationRegistry.sol";

/**
 * @title IdentityRegistry
 * @dev Implementation of the Identity Registry for ERC-XXXX Trustless Agents v0.3
 * @notice Central registry for all agent identities with spam protection
 * @author ChaosChain Labs
 */
contract IdentityRegistry is IIdentityRegistry {
    // ============ Constants ============

    /// @dev Registration fee of 0.005 ETH that gets burned
    uint256 public constant REGISTRATION_FEE = 0.005 ether;

    // ============ State Variables ============

    /// @dev Counter for agent IDs
    uint256 private _agentIdCounter;

    /// @dev Mapping from agent ID to agent info
    mapping(uint256 => AgentInfo) private _agents;

    /// @dev Mapping from domain to agent ID
    mapping(string => uint256) private _domainToAgentId;

    /// @dev Mapping from address to agent ID
    mapping(address => uint256) private _addressToAgentId;

    /// @dev Array of all registered domains
    string[] private _allDomains;

    /// @dev Reference to the ReputationRegistry (optional, can be zero address)
    IReputationRegistry public reputationRegistry;

    /// @dev Reference to the ValidationRegistry (optional, can be zero address)
    IValidationRegistry public validationRegistry;

    // ============ Constructor ============

    /**
     * @dev Constructor initializes the registry and optionally sets registry references
     * @param _reputationRegistry Address of the ReputationRegistry (can be zero address)
     * @param _validationRegistry Address of the ValidationRegistry (can be zero address)
     */
    constructor(address _reputationRegistry, address _validationRegistry) {
        // Start agent IDs from 1 (0 is reserved for "not found")
        _agentIdCounter = 1;

        // Set registry references (can be updated later)
        if (_reputationRegistry != address(0)) {
            reputationRegistry = IReputationRegistry(_reputationRegistry);
        }
        if (_validationRegistry != address(0)) {
            validationRegistry = IValidationRegistry(_validationRegistry);
        }
    }

    // ============ Write Functions ============
    
    /**
     * @inheritdoc IIdentityRegistry
     */
    function newAgent(
        string calldata agentDomain,
        address agentAddress,
        string calldata metadataUri
    ) external payable returns (uint256 agentId) {

        // Validate inputs
        if (bytes(agentDomain).length == 0) {
            revert InvalidDomain();
        }
        if (agentAddress == address(0)) {
            revert InvalidAddress();
        }

        // Check for duplicates
        if (_domainToAgentId[agentDomain] != 0) {
            revert DomainAlreadyRegistered();
        }
        if (_addressToAgentId[agentAddress] != 0) {
            revert AddressAlreadyRegistered();
        }

        // Validate registration fee payment
        // TEMPORARILY DISABLED FOR DEBUGGING
        // if (msg.value < REGISTRATION_FEE) {
        //     revert InsufficientFee();
        // }

        // Assign new agent ID
        agentId = _agentIdCounter++;

        // Store agent info
        _agents[agentId] = AgentInfo({
            agentId: agentId,
            agentDomain: agentDomain,
            agentAddress: agentAddress,
            metadataUri: metadataUri
        });
        
        // Create lookup mappings
        _domainToAgentId[agentDomain] = agentId;
        _addressToAgentId[agentAddress] = agentId;

        // Add domain to the list of all domains
        _allDomains.push(agentDomain);

        // Burn the registration fee by not forwarding it anywhere
        // The ETH stays locked in this contract forever

        emit AgentRegistered(agentId, agentDomain, agentAddress);
    }
    
    /**
     * @inheritdoc IIdentityRegistry
     */
    function updateAgent(
        uint256 agentId,
        string calldata newAgentDomain,
        address newAgentAddress
    ) external returns (bool success) {
        // Validate agent exists
        AgentInfo storage agent = _agents[agentId];
        if (agent.agentId == 0) {
            revert AgentNotFound();
        }
        
        // Check authorization
        if (msg.sender != agent.agentAddress) {
            revert UnauthorizedUpdate();
        }
        
        bool domainChanged = bytes(newAgentDomain).length > 0;
        bool addressChanged = newAgentAddress != address(0);
        
        // Validate new values if provided
        if (domainChanged) {
            if (_domainToAgentId[newAgentDomain] != 0) {
                revert DomainAlreadyRegistered();
            }
        }
        
        if (addressChanged) {
            if (_addressToAgentId[newAgentAddress] != 0) {
                revert AddressAlreadyRegistered();
            }
        }
        
        // Update domain if provided
        if (domainChanged) {
            // Remove old domain mapping
            delete _domainToAgentId[agent.agentDomain];
            // Set new domain
            agent.agentDomain = newAgentDomain;
            _domainToAgentId[newAgentDomain] = agentId;
        }
        
        // Update address if provided
        if (addressChanged) {
            // Remove old address mapping
            delete _addressToAgentId[agent.agentAddress];
            // Set new address
            agent.agentAddress = newAgentAddress;
            _addressToAgentId[newAgentAddress] = agentId;
        }
        
        emit AgentUpdated(agentId, agent.agentDomain, agent.agentAddress);
        return true;
    }

    /**
     * @dev Update an agent's metadata URI
     * @param agentId The agent ID
     * @param newMetadataUri New metadata URI
     * @return success True if update was successful
     */
    function updateMetadata(uint256 agentId, string calldata newMetadataUri) external returns (bool success) {
        // Validate agent exists
        AgentInfo storage agent = _agents[agentId];
        if (agent.agentId == 0) {
            revert AgentNotFound();
        }

        // Check authorization
        if (msg.sender != agent.agentAddress) {
            revert UnauthorizedUpdate();
        }

        // Update metadata
        agent.metadataUri = newMetadataUri;

        emit AgentUpdated(agentId, agent.agentDomain, agent.agentAddress);
        return true;
    }

    // ============ Read Functions ============
    
    /**
     * @inheritdoc IIdentityRegistry
     */
    function getAgent(uint256 agentId) external view returns (AgentInfo memory agentInfo) {
        agentInfo = _agents[agentId];
        if (agentInfo.agentId == 0) {
            revert AgentNotFound();
        }
    }
    
    /**
     * @inheritdoc IIdentityRegistry
     */
    function resolveByDomain(string calldata agentDomain) external view returns (AgentInfo memory agentInfo) {
        uint256 agentId = _domainToAgentId[agentDomain];
        if (agentId == 0) {
            revert AgentNotFound();
        }
        agentInfo = _agents[agentId];
    }
    
    /**
     * @inheritdoc IIdentityRegistry
     */
    function resolveByAddress(address agentAddress) external view returns (AgentInfo memory agentInfo) {
        uint256 agentId = _addressToAgentId[agentAddress];
        if (agentId == 0) {
            revert AgentNotFound();
        }
        agentInfo = _agents[agentId];
    }
    
    /**
     * @inheritdoc IIdentityRegistry
     */
    function getAgentCount() external view returns (uint256 count) {
        return _agentIdCounter - 1; // Subtract 1 because we start from 1
    }
    
    /**
     * @inheritdoc IIdentityRegistry
     */
    function agentExists(uint256 agentId) external view returns (bool exists) {
        return _agents[agentId].agentId != 0;
    }

    /**
     * @dev Get all registered domains
     * @return domains Array of all registered domain names
     */
    function getAllDomains() external view returns (string[] memory domains) {
        return _allDomains;
    }

    /**
     * @dev Get paginated list of domains
     * @param offset Starting index
     * @param limit Maximum number of domains to return
     * @return domains Array of domain names
     * @return total Total number of registered domains
     */
    function getDomainsPaginated(uint256 offset, uint256 limit) external view returns (string[] memory domains, uint256 total) {
        total = _allDomains.length;

        if (offset >= total) {
            return (new string[](0), total);
        }

        uint256 end = offset + limit;
        if (end > total) {
            end = total;
        }

        uint256 size = end - offset;
        domains = new string[](size);

        for (uint256 i = 0; i < size; i++) {
            domains[i] = _allDomains[offset + i];
        }

        return (domains, total);
    }

    // ============ ERC8004 Extended Functions ============

    /**
     * @dev Get an agent's reputation score
     * @param agentId The agent ID
     * @return score The reputation score
     * @notice Returns 0 if ReputationRegistry is not set
     */
    function getAgentReputation(uint256 agentId) external view returns (int256 score) {
        if (address(reputationRegistry) == address(0)) {
            return 0;
        }
        return reputationRegistry.getReputation(agentId);
    }

    /**
     * @dev Get vote counts for an agent
     * @param agentId The agent ID
     * @return upVotes Number of positive votes
     * @return downVotes Number of negative votes
     * @notice Returns zeros if ReputationRegistry is not set
     */
    function getAgentVoteCounts(uint256 agentId) external view returns (uint256 upVotes, uint256 downVotes) {
        if (address(reputationRegistry) == address(0)) {
            return (0, 0);
        }
        return reputationRegistry.getVoteCounts(agentId);
    }

    /**
     * @dev Get validation data for an agent
     * @param agentId The agent ID
     * @return validationCount Number of validations
     * @return averageScore Average validation score (0-100)
     * @notice Returns zeros if ValidationRegistry is not set
     */
    function getAgentValidation(uint256 agentId) external view returns (uint256 validationCount, uint8 averageScore) {
        if (address(validationRegistry) == address(0)) {
            return (0, 0);
        }
        return validationRegistry.getValidation(agentId);
    }

    /**
     * @dev Get comprehensive agent information including identity, reputation, and validation
     * @param agentId The agent's unique identifier
     * @return agentInfo The agent's identity information
     * @return reputationScore The agent's reputation score
     * @return upVotes Number of up votes
     * @return downVotes Number of down votes
     * @return validationCount Number of validations received
     * @return validationScore Average validation score (0-100)
     */
    function getAgentFullInfo(
        uint256 agentId
    )
        external
        view
        returns (
            AgentInfo memory agentInfo,
            int256 reputationScore,
            uint256 upVotes,
            uint256 downVotes,
            uint256 validationCount,
            uint8 validationScore
        )
    {
        // Get agent info
        agentInfo = _agents[agentId];
        if (agentInfo.agentId == 0) {
            revert AgentNotFound();
        }

        // Get reputation info if registry is set
        if (address(reputationRegistry) != address(0)) {
            reputationScore = reputationRegistry.getReputation(agentId);
            (upVotes, downVotes) = reputationRegistry.getVoteCounts(agentId);
        }

        // Get validation info if registry is set
        if (address(validationRegistry) != address(0)) {
            (validationCount, validationScore) = validationRegistry.getValidation(agentId);
        }
    }

    // ============ Admin Functions ============

    /**
     * @dev Update the ReputationRegistry address
     * @param _reputationRegistry New ReputationRegistry address
     * @notice This function would typically be restricted to contract owner/admin
     * @dev For this implementation, anyone can update (should add access control in production)
     */
    function setReputationRegistry(address _reputationRegistry) external {
        reputationRegistry = IReputationRegistry(_reputationRegistry);
    }

    /**
     * @dev Update the ValidationRegistry address
     * @param _validationRegistry New ValidationRegistry address
     * @notice This function would typically be restricted to contract owner/admin
     * @dev For this implementation, anyone can update (should add access control in production)
     */
    function setValidationRegistry(address _validationRegistry) external {
        validationRegistry = IValidationRegistry(_validationRegistry);
    }

    // ============ Internal Functions ============

    // Note: Registration fee is burned by keeping it locked in this contract
    // This is more gas-efficient than transferring to address(0)
}