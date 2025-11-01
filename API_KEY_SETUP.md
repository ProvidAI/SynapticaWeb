# OpenAI API Key Setup

## ⚠️ Important: API Key Configuration Required

The test shows that your current OpenAI API key is invalid or incorrectly configured.

## How to Fix This:

### 1. Get Your OpenAI API Key

1. Go to: https://platform.openai.com/api-keys
2. Sign in to your OpenAI account (or create one)
3. Click "Create new secret key"
4. Give it a name (e.g., "ProvidAI")
5. Copy the entire key (it starts with `sk-`)

### 2. Add to Your .env File

Edit your `.env` file and replace the existing key:

```bash
# Open .env file
nano .env  # or use your preferred editor

# Replace this line with your actual key:
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Verify Your Key Works

After adding your key, test it:

```bash
# Test OpenAI connection
python scripts/test_openai_integration.py

# Or test directly
python -c "
import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
client = OpenAI()
response = client.chat.completions.create(
    model='gpt-3.5-turbo',
    messages=[{'role': 'user', 'content': 'Hello'}],
    max_tokens=10
)
print('✅ API key works!')
"
```

## API Key Format

Your OpenAI API key should:
- Start with `sk-`
- Be about 50+ characters long
- Look like: `sk-proj-abcdef123456789...`

## Common Issues

### "Invalid API key"
- Make sure you copied the entire key
- Check there are no extra spaces or quotes
- Ensure the key hasn't been revoked

### "Insufficient credits"
- New OpenAI accounts get $5 free credits (expired after 3 months)
- Check your usage: https://platform.openai.com/usage
- Add payment method if needed: https://platform.openai.com/settings/billing

### "Rate limit exceeded"
- Free tier has rate limits
- Wait a minute and try again
- Consider upgrading to paid tier for higher limits

## Cost Estimates

For testing and development:
- **GPT-3.5-turbo**: ~$0.002 per test run
- **GPT-4-turbo**: ~$0.02 per test run
- **Full pipeline demo**: ~$0.10-$0.50 depending on model

## Security Notes

- **Never commit your .env file** (it's in .gitignore)
- **Never share your API key publicly**
- **Rotate keys regularly** for production use
- **Set usage limits** in OpenAI dashboard if needed

## Next Steps

Once your API key is working:

1. Run the test suite:
   ```bash
   python scripts/test_openai_integration.py
   ```

2. Run the demo:
   ```bash
   python scripts/demo_research_pipeline.py
   ```

3. Configure Hedera credentials in .env (see SETUP_GUIDE.md)

## Need Help?

- OpenAI API docs: https://platform.openai.com/docs
- API key issues: https://help.openai.com/en/articles/4936850
- Billing/credits: https://platform.openai.com/settings/billing