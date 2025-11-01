# ProvidAI Setup Guide

This guide will help you configure ProvidAI with your OpenAI API keys and Hedera testnet account.

## Prerequisites

- Python 3.11 or higher
- OpenAI API key (get from https://platform.openai.com/api-keys)
- Hedera testnet account (create at https://portal.hedera.com/)

## Step 1: Clone Repository

```bash
git clone <repository-url>
cd ProvidAI
```

## Step 2: Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Configure Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` file and add your credentials:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Your OpenAI API key

# Hedera Testnet Configuration
HEDERA_NETWORK=testnet
HEDERA_ACCOUNT_ID=0.0.1234567  # Your Hedera account ID (e.g., 0.0.1234567)
HEDERA_PRIVATE_KEY=302exxxxxxxxxx  # Your Hedera private key (DER-encoded hex string)

# Database (using SQLite for simplicity)
DATABASE_URL=sqlite:///./hedera_marketplace.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32

# ERC-8004 Registry Contract (Hedera testnet example)
ERC8004_REGISTRY_ADDRESS=0x1234567890abcdef1234567890abcdef12345678
ERC8004_RPC_URL=https://testnet.hashio.io/api

# Agent Configuration (OpenAI Models)
ORCHESTRATOR_MODEL=gpt-4-turbo-preview
NEGOTIATOR_MODEL=gpt-4-turbo-preview
EXECUTOR_MODEL=gpt-4-turbo-preview
VERIFIER_MODEL=gpt-4-turbo-preview
# Alternative models: gpt-4, gpt-3.5-turbo (cheaper but less capable)

# Logging
LOG_LEVEL=INFO
```

### Getting Your Credentials

#### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Add it to your `.env` file

#### Hedera Testnet Account
1. Go to https://portal.hedera.com/
2. Click "Create testnet account"
3. Sign up and verify your email
4. Your account will be created with:
   - Account ID (e.g., `0.0.1234567`)
   - Private key (DER-encoded hex string)
   - 10,000 test HBAR automatically funded
5. Add these to your `.env` file

## Step 5: Initialize Database

```bash
# Create database tables
python -c "from shared.database import Base, engine; Base.metadata.create_all(engine)"
```

## Step 6: Test the Setup

### Test Individual Components

```bash
# Test database connection
python -c "from shared.database import SessionLocal; db = SessionLocal(); print('✅ Database connection successful'); db.close()"

# Test OpenAI connection (this will use a small amount of credits)
python -c "
import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
response = client.chat.completions.create(
    model='gpt-3.5-turbo',
    messages=[{'role': 'user', 'content': 'Say hello'}],
    max_tokens=10
)
print('✅ OpenAI connection successful')
print('Response:', response.choices[0].message.content)
"

# Test Hedera connection (optional - requires web3)
python -c "
import os
from web3 import Web3
w3 = Web3(Web3.HTTPProvider(os.getenv('ERC8004_RPC_URL', 'https://testnet.hashio.io/api')))
print('✅ Connected to Hedera testnet' if w3.is_connected() else '❌ Failed to connect')
print(f'Chain ID: {w3.eth.chain_id}')
"
```

## Step 7: Run the Research Pipeline Demo

```bash
# Run the full research pipeline demo
python scripts/demo_research_pipeline.py

# Or test individual agents
python scripts/demo_research_pipeline.py --agents
```

## Expected Output

When running successfully, you should see:

```
Starting Research Pipeline Demo...

================================================================================
ProvidAI Research Pipeline Demo
Demonstrating autonomous agent-to-agent research with micropayments
================================================================================

🔧 Initializing database...
✅ Database ready

📚 Research Query:
   What is the quantitative impact of blockchain-based micropayment systems
   on the adoption rate and operational efficiency of autonomous AI agent marketplaces?

🚀 Starting research pipeline...
✅ Pipeline initialized with ID: abc-123-def
   Budget: 5.0 HBAR
   Phases: ideation, knowledge_retrieval, experimentation, interpretation, publication

[... continues with phase execution ...]
```

## OpenAI Model Selection Guide

Choose your models based on needs and budget:

### Recommended for Best Results
- **gpt-4-turbo-preview**: Latest GPT-4 model, best for complex research tasks
- Cost: ~$0.01 per 1K input tokens, $0.03 per 1K output tokens

### Budget-Friendly Option
- **gpt-3.5-turbo**: Fast and cheaper, good for simpler tasks
- Cost: ~$0.0005 per 1K input tokens, $0.0015 per 1K output tokens

### Model Configuration
You can mix models for different agents to optimize cost:

```bash
# In .env - Use GPT-4 for complex agents, GPT-3.5 for simpler ones
ORCHESTRATOR_MODEL=gpt-4-turbo-preview  # Needs complex coordination
NEGOTIATOR_MODEL=gpt-3.5-turbo         # Simpler discovery tasks
EXECUTOR_MODEL=gpt-3.5-turbo           # Tool execution
VERIFIER_MODEL=gpt-4-turbo-preview     # Needs careful validation
```

## API Cost Estimation

For a complete research pipeline run:
- **GPT-4-turbo**: ~$0.50 - $1.00 per complete pipeline
- **GPT-3.5-turbo**: ~$0.05 - $0.10 per complete pipeline
- **Mixed**: ~$0.20 - $0.40 per complete pipeline

## Troubleshooting

### OpenAI API Key Issues
- **Error: "OPENAI_API_KEY not set"**: Make sure your `.env` file contains the key
- **Error: "Invalid API key"**: Check that your key starts with `sk-` and is copied correctly
- **Error: "Insufficient credits"**: Add credits to your OpenAI account

### Hedera Connection Issues
- **Error: "Invalid account ID"**: Format should be `0.0.1234567` (three numbers separated by dots)
- **Error: "Invalid private key"**: Ensure it's the DER-encoded hex string from Hedera portal

### Database Issues
- **Error: "No such table"**: Run the database initialization command again
- **Permission errors**: Make sure the directory is writable

## Running the API Server

To start the FastAPI server for the orchestrator:

```bash
python -m api.main
```

The API will be available at:
- API endpoints: http://localhost:8000
- Interactive docs: http://localhost:8000/docs

## Next Steps

1. **Test the pipeline**: Run the demo script to see the research pipeline in action
2. **Monitor costs**: Check your OpenAI usage at https://platform.openai.com/usage
3. **Customize agents**: Modify system prompts in `agents/research/` directories
4. **Add more agents**: Implement the remaining 13 research agents
5. **Deploy to production**: Set up PostgreSQL and deploy to a cloud provider

## Support

For issues or questions:
1. Check the error messages in the console
2. Review the logs in the terminal
3. Ensure all environment variables are set correctly
4. Open an issue on GitHub with error details

## Security Notes

- **Never commit your `.env` file** - it's in `.gitignore` for safety
- **Keep your API keys secret** - don't share them publicly
- **Use testnet for development** - real HBAR costs money
- **Monitor API usage** - set usage limits in OpenAI dashboard if needed