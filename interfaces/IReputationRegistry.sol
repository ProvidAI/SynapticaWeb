// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title IReputationRegistry
 * @dev Interface for the Reputation Registry
 */
interface IReputationRegistry {
    /**
     * @dev Get an agent's reputation score
     * @param agentId The agent ID
     * @return score The reputation score
     */
    function getReputation(uint256 agentId) external view returns (int256 score);

    /**
     * @dev Get vote counts for an agent
     * @param agentId The agent ID
     * @return upVotes Number of positive votes
     * @return downVotes Number of negative votes
     */
    function getVoteCounts(uint256 agentId) external view returns (uint256 upVotes, uint256 downVotes);
}
