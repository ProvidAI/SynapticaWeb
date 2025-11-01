# Hedera - Building an Agent-first Digital Economy

> **Agentic Economy Solutions** — Build agentic AI-driven solutions using ERC-8004 and x402 payments for trustless, autonomous agent interactions on the Hedera testnet

---

## Challenge Summary

**Goal**: Build a working prototype of an agentic system that uses **ERC-8004 for agent discovery and trust**, integrated with **x402 for secure on-chain payments**, showcasing autonomous agent-to-agent transactions on the Hedera testnet.

**Expected Final Product**: A unified agentic system that demonstrates how agents can discover each other, establish trust, and execute payments seamlessly on the Hedera testnet, fostering a decentralized digital economy.

> **📖 IMPORTANT**: Before diving into the code, please read this **README.md** document first. It contains essential context, detailed requirements, and additional guidance that will help you build a winning solution.

---

## 📋 The Problem We're Solving

### Current State
- AI agents lack standardized, trustless mechanisms for communication and payments, leading to silos and security risks
- Autonomous interactions face inefficiencies where real-time, verifiable transactions are essential
- **Cross-functional friction**: AI agents struggle to discover each other, establish trust, and execute payments seamlessly
- **High operational risk**: Manual processes and lack of interoperability limit the potential of autonomous agent-driven services

### What You're Building
- **Unified Agentic Economy Platform**
  - Implement ERC-8004 protocol for agent discovery and capability queries
  - Enable A2A (Agent-to-Agent) communication with trust establishment
  - Integrate x402 payments for secure on-chain transactions
  - Provide agent interaction logs using Hedera Consensus Service
  - Support autonomous agent-to-agent transactions and negotiations
  - Enable stablecoin transfers and crypto payments on Hedera testnet

### Who Benefits
- AI x web3 developers building agentic applications, businesses integrating autonomous systems, and end-users benefiting from seamless agent-driven services like automated payments or negotiations.

---

## 🎯 What You're Building

A unified agentic system that enables autonomous agent interactions:

```
┌─────────────────────────────────────────────────────────────────┐
│  ERC-8004 Agent Discovery & Trust                               │
│  ↓ Agent discovery → Capability queries → Trust establishment    │
├─────────────────────────────────────────────────────────────────┤
│  x402 Payment Integration                                       │
│  ↓ Secure payments → On-chain transactions → Verification      │
├─────────────────────────────────────────────────────────────────┤
│  Unified Agentic Digital Economy                               │
│  ↓ Autonomous agent-to-agent transactions & negotiations       │
├─────────────────────────────────────────────────────────────────┤
```

---

## 🏗️ Solution Components — Step-by-Step Build Guide

### Unified Agentic Economy System

**What it does**: Creates a seamless integration of ERC-8004 agent discovery and x402 payments to enable autonomous agent-to-agent transactions on the Hedera testnet.

**Key Components**:

#### 1. ERC-8004 Agent Discovery & Trust
- **Agent discovery**: Implement ERC-8004 protocol for agent discovery and capability queries
- **Trust establishment**: Enable secure A2A communication mechanisms
- **Capability registry**: Maintain registry of agent capabilities and services
- **Service discovery**: Enable agents to find relevant services and capabilities
- **Identity verification**: Verify agent identities and capabilities

#### 2. x402 Payment Integration
- **Payment processing**: Handle stablecoin transfers and crypto payments
- **Transaction validation**: Verify payment authenticity and completeness
- **Multi-currency support**: Support various payment tokens and stablecoins
- **Payment routing**: Optimize payment paths and minimize fees
- **Conditional payments**: Enable payments based on specific conditions

#### 3. Hedera Testnet Integration
- **Network connectivity**: Connect to Hedera testnet using provided APIs
- **Transaction submission**: Submit and track payment transactions
- **Mirror node integration**: Access real-time network data and transaction history
- **Account management**: Handle agent account creation and management
- **Consensus logging**: Log agent interactions using Hedera Consensus Service

#### 4. Autonomous Transaction Engine
- **A2A messaging**: Enable secure agent-to-agent communication
- **Transaction intents**: Process and validate agent transaction intentions
- **Smart contracts**: Implement automated payment logic
- **Escrow mechanisms**: Support secure escrow and release protocols
- **Micropayment optimization**: Handle small-value transactions efficiently

#### 5. Trust & Security Layer
- **Permission management**: Control access to agent services and data
- **Audit trails**: Maintain comprehensive logs of agent interactions
- **Security protocols**: Implement secure communication channels
- **Error handling**: Manage failed transactions and retry mechanisms
- **Performance monitoring**: Track agent performance and availability

**Deliverables**:
- [ ] Working ERC-8004 integration system
- [ ] Agent discovery and capability registry
- [ ] Secure A2A communication protocols
- [ ] x402 payment integration
- [ ] Hedera testnet connectivity and transaction management
- [ ] Real-time payment verification system
- [ ] Comprehensive audit trails for all activities
- [ ] Autonomous transaction execution capabilities

---

## 🛠️ Technology Stack & Resources

### APIs & Services
- **Hedera Mirror Node Swagger Doc**: For real-time network data and transaction history
  - https://testnet.mirrornode.hedera.com/api/v1/docs/
- **HashScan Explorer**: For browsing transactions and smart contracts
  - https://hashscan.io/testnet/home
- **JSON RPC**: https://testnet.hashio.io/api (CHAIN ID: 296)

### SDKs & Libraries
- **Hedera Agent Kit**: 
  - Overview: https://docs.hedera.com/hedera/open-source-solutions/ai-studio-on-hedera/hedera-ai-agent-kit
  - SDK: https://github.com/hashgraph/hedera-agent-kit-js
  - MCP Server: https://github.com/hashgraph/hedera-agent-kit-js/blob/main/docs/DEVEXAMPLES.md#option-d-try-out-the-mcp-server
- **Hedera x402 repo**: https://github.com/hedera-dev/x402-hedera
- **Hedera SDKs**: JavaScript, Python, Go, Rust, Java, C++
- **ERC-8004 Hedera Deployments**: https://github.com/erc-8004/erc-8004-contracts

### Development Resources
- **Dev Portal**: https://portal.hedera.com/ (Creates account and tops up with testnet hbar)
- **Testnet Faucet**: https://portal.hedera.com/faucet
- **Dev Playground**: https://portal.hedera.com/playground

### Data Sources
- **Agent interaction logs (JSON)**: Data for agent discovery, capability queries, A2A communication
- **Payment data (CSV)**: Timestamped records of x402 transactions on Hedera testnet

---


## 🏆 Judging Criteria

Your submission will be evaluated on:

### Main Hackathon Criteria

| Criteria | Weight | Description |
|----------|--------|-------------|
| **Creativity** | 20% | Innovative integration of ERC-8004 and x402 in agentic workflows |
| **Visual Design** | 10% | Clarity and intuitiveness of the agent interface and transaction visualizations |
| **Feasibility** | 20% | Practicality for real-world deployment on DLT networks |
| **Reachability** | 20% | Potential for broad adoption across various sectors |
| **Technical Depth** | 30% | Effective use of protocols, security measures, and agent autonomy |

---

## 🤝 Support & Contact

**Getting Help**:
- **Technical questions**: Ask during mentor sessions
- **Hedera documentation**: Reference Hedera Developer Portal and SDK documentation
- **ERC-8004 resources**: Check GitHub repository and documentation
- **x402 payments**: Reference Hedera x402 repository and examples

## 🔑 Key Resources

### Hedera Docs & Portals
- **Hedera Developer Portal:** https://portal.hedera.com/
- **Hedera Documentation:** https://docs.hedera.com/

### Agentic / Protocol
- **ERC-8004 Contracts (agent discovery & trust):** https://github.com/erc-8004/erc-8004-contracts
- **Hedera Agent Kit (agent-to-agent + HCS/x402 patterns):** https://github.com/hashgraph/hedera-agent-kit-js

### Hedera SDKs (Hiero)
- **JavaScript/TypeScript:** https://github.com/hiero-ledger/hiero-sdk-js  
- **Python:** https://github.com/hiero-ledger/hiero-sdk-python  
- **Go:** https://github.com/hiero-ledger/hiero-sdk-go  
- **Rust:** https://github.com/hiero-ledger/hiero-sdk-rust  
- **Java:** https://github.com/hiero-ledger/hiero-sdk-java  
- **C++:** https://github.com/hiero-ledger/hiero-sdk-cpp

---

## 📋 Presentation Requirements

### Format
- **Live or recorded demo** showcasing your agentic system

### Key Elements
- **Clear problem articulation**: Define the agentic economy challenges addressed
- **Solution representation**: Showcase the prototype's architecture and key flows
- **Functional highlights**: Demonstrate agent discovery, trust establishment, and payments on the Hedera testnet
- **Decision-making process**: Explain how ERC-8004 and x402 solve the issues
- **Visual Components**: Include diagrams of agent interactions and transaction flows

### Requirements
- **Conciseness**: Keep presentation focused and to the point
- **Comprehensiveness**: Cover all key aspects of your solution
- **Descriptions and definitions**: Provide clear explanations where necessary

---

## 🚀 Getting Started

1. **Set up Hedera testnet account** via the developer portal
2. **Familiarize yourself** with ERC-8004 and x402 protocols
3. **Explore the Hedera Agent Kit** and available SDKs
4. **Design your unified agentic system** architecture
5. **Implement ERC-8004 agent discovery** and trust mechanisms
6. **Integrate x402 payment functionality** for autonomous transactions
7. **Test autonomous agent-to-agent interactions** on Hedera testnet
8. **Prepare comprehensive demo** with visual components and clear explanations

**Remember**: Focus on demonstrating autonomous agent interactions with real payments on the Hedera testnet. The goal is to showcase a working agentic digital economy that seamlessly integrates ERC-8004 and x402!
