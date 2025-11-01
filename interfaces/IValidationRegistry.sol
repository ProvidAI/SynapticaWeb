// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title IValidationRegistry
 * @dev Interface for the Validation Registry
 */
interface IValidationRegistry {
    /**
     * @dev Get validation data for an agent
     * @param agentId The agent ID
     * @return validationCount Number of validations
     * @return averageScore Average validation score (0-100)
     */
    function getValidation(uint256 agentId) external view returns (uint256 validationCount, uint8 averageScore);
}
