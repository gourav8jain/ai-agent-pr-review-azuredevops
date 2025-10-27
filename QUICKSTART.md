# Quick Start Guide

Get the AI PR Review Agent up and running in 5 minutes!

## Prerequisites

You'll need:
- Python 3.8+
- Azure DevOps Personal Access Token (PAT)
- OpenAI API key

## Step 1: Get Your Credentials

### Azure DevOps PAT

1. Go to Azure DevOps → User Settings → Personal Access Tokens
2. Click "New Token"
3. Select scopes:
   - Code (read & write)
   - Pull requests (read & write)
4. Copy the token

### Google Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign up/Login with your Google account
3. Click "Get API Key" or "Create API Key"
4. Copy the API key
5. Note: Free tier includes 60 requests/min, 1,500/day

## Step 2: Setup the Agent

### Option A: Automated Setup (Recommended)

```bash
# Run the setup script
./setup.sh

# Edit configuration
nano config.env  # or use your preferred editor
```

### Option B: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit config
cp config.env.example config.env
nano config.env  # or use your preferred editor
```

## Step 3: Configure

Edit `config.env` with your credentials:

```env
# Azure DevOps
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-organization
AZURE_DEVOPS_PERSONAL_ACCESS_TOKEN=your_pat_token_here
AZURE_DEVOPS_PROJECT=your-project-name

# Google Gemini AI
GOOGLE_AI_API_KEY=your_google_ai_api_key_here
AI_MODEL=gemini-2.0-flash-exp  # Free and fast!

# Optional: Tune these settings
REVIEW_MODE=detailed
COMMENT_THRESHOLD=medium
POLL_INTERVAL_SECONDS=30
```

## Step 4: Run

### Test Run (Foreground)

```bash
# Activate virtual environment
source venv/bin/activate

# Run the agent
python main.py
```

You should see:
```
============================================================
Azure DevOps PR Review Agent Starting...
============================================================
Configuration loaded:
  Organization: https://dev.azure.com/your-org
  Project: your-project
  Model: gpt-4
  Poll Interval: 30s
...
Starting main loop...
```

### Production Run (Background)

**Using Docker:**

```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

**Using systemd (Linux):**

```bash
# Create service file
sudo cp systemd.service /etc/systemd/system/pr-review-agent.service

# Edit the paths in the service file
sudo nano /etc/systemd/system/pr-review-agent.service

# Enable and start
sudo systemctl enable pr-review-agent
sudo systemctl start pr-review-agent

# Check status
sudo systemctl status pr-review-agent
```

## Step 5: Test

1. Create a test PR in your Azure DevOps repository
2. Wait for the agent to pick it up (up to 30 seconds)
3. Check the PR comments - you should see AI-generated reviews!

## Common Issues

### "Authentication failed"

- Check your PAT token is valid
- Ensure you have the correct permissions
- Verify organization and project names are correct

### "Google AI API error"

- Verify your API key is correct
- Check you have remaining quota (free: 1,500 requests/day)
- Try using `gemini-1.5-flash` for higher rate limits

- Read logs: `tail -f pr_review_agent.log`

### "No PRs found"

- Verify the project name is correct
- Check you have access to the repositories
- Look at the logs: `tail -f pr_review_agent.log`

### "Import errors"

- Make sure virtual environment is activated
- Install dependencies: `pip install -r requirements.txt`
- Check Python version: `python3 --version` (need 3.8+)

## Next Steps

- Adjust `POLL_INTERVAL_SECONDS` if you want more/less frequent checks
- Change `REVIEW_MODE` to `quick` for faster reviews
- Set `COMMENT_THRESHOLD` to `high` to only show critical issues
- Monitor costs in your OpenAI dashboard
- Check logs: `tail -f pr_review_agent.log`

## Need Help?

Check the full README.md for detailed documentation.

