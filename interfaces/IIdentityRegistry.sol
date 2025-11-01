// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title IIdentityRegistry
 * @dev Interface for the Identity Registry
 */
interface IIdentityRegistry {
    // ============ Structs ============

    struct AgentInfo {
        uint256 agentId;
        string agentDomain;
        address agentAddress;
        string metadataUri;
    }

    // ============ Events ============

    event AgentRegistered(
        uint256 indexed agentId,
        string agentDomain,
        address indexed agentAddress
    );

    event AgentUpdated(
        uint256 indexed agentId,
        string newAgentDomain,
        address indexed newAgentAddress
    );

    // ============ Errors ============

    error InvalidDomain();
    error InvalidAddress();
    error DomainAlreadyRegistered();
    error AddressAlreadyRegistered();
    error InsufficientFee();
    error AgentNotFound();
    error UnauthorizedUpdate();

    // ============ Functions ============

    function newAgent(
        string calldata agentDomain,
        address agentAddress,
        string calldata metadataUri
    ) external payable returns (uint256 agentId);

    function updateAgent(
        uint256 agentId,
        string calldata newAgentDomain,
        address newAgentAddress
    ) external returns (bool success);

    function getAgent(uint256 agentId) external view returns (AgentInfo memory agentInfo);

    function resolveByDomain(string calldata agentDomain) external view returns (AgentInfo memory agentInfo);

    function resolveByAddress(address agentAddress) external view returns (AgentInfo memory agentInfo);

    function getAgentCount() external view returns (uint256 count);

    function agentExists(uint256 agentId) external view returns (bool exists);
}
