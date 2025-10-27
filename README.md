# Azure DevOps AI-Powered PR Review Agent

An intelligent, continuously running agent that automatically reviews pull requests on Azure DevOps and provides detailed, line-by-line feedback with actionable solutions.

## Features

- 🤖 **AI-Powered Reviews**: Uses Google Gemini to analyze code quality, security, and best practices
- 🎯 **Line-by-Line Comments**: Posts inline comments on specific lines with solutions
- 🔄 **Continuous Monitoring**: Runs 24/7, automatically reviewing new PRs
- 📊 **Detailed Feedback**: Identifies bugs, security issues, performance problems, and code quality concerns
- ⚡ **Configurable**: Adjustable review modes (detailed, quick, security-focused)
- 💡 **Actionable Solutions**: Provides code fixes and improvements, not just critiques

## Prerequisites

1. **Azure DevOps Account**
   - Create a Personal Access Token (PAT) with read/write permissions
   - Note: You need permissions to:
     - View pull requests
     - Read repository content
     - Create pull request comments

2. **Google Gemini API Key**
   - Sign up at [Google AI Studio](https://aistudio.google.com/apikey)
   - Create an API key
   - Recommended: gemini-2.0-flash-exp (free tier available, very fast!)

3. **Python 3.8+**
   - Install Python if you don't have it

## Installation

1. **Clone this repository**
   ```bash
   git clone <repository-url>
   cd ai-agent-pr-review-azuredevops
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the agent**
   ```bash
   cp config.env.example config.env
   ```
   
   Edit `config.env` with your credentials:
   ```env
   # Azure DevOps Configuration
   AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-organization
   AZURE_DEVOPS_PERSONAL_ACCESS_TOKEN=your_pat_here
   AZURE_DEVOPS_PROJECT=your-project-name

   # Google Gemini AI Configuration
   GOOGLE_AI_API_KEY=your_google_ai_api_key_here
   AI_MODEL=gemini-2.0-flash-exp

   # Review Settings
   REVIEW_MODE=detailed
   COMMENT_THRESHOLD=medium
   POLL_INTERVAL_SECONDS=30
   ```

## Running the Agent

### Option 1: Direct Run (Development/Testing)

```bash
python main.py
```

### Option 2: Production Deployment

For production, use a process manager like `systemd` (Linux) or `launchd` (macOS):

#### Linux (systemd)

Create `/etc/systemd/system/pr-review-agent.service`:

```ini
[Unit]
Description=Azure DevOps PR Review Agent
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/ai-agent-pr-review-azuredevops
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /path/to/ai-agent-pr-review-azuredevops/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start the service:
```bash
sudo systemctl enable pr-review-agent
sudo systemctl start pr-review-agent
sudo systemctl status pr-review-agent
```

#### macOS (launchd)

Create `~/Library/LaunchAgents/com.prreview.agent.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.prreview.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/ai-agent-pr-review-azuredevops/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/ai-agent-pr-review-azuredevops</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/path/to/ai-agent-pr-review-azuredevops/output.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/ai-agent-pr-review-azuredevops/error.log</string>
</dict>
</plist>
```

Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.prreview.agent.plist
launchctl start com.prreview.agent
```

#### Docker (Alternative)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  pr-review-agent:
    build: .
    env_file:
      - config.env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

Run:
```bash
docker-compose up -d
```

## Configuration Options

### Review Modes

- **`detailed`**: Comprehensive review of code quality, security, performance, and best practices
- **`quick`**: Fast review focusing on critical bugs and security issues
- **`security-focused`**: Emphasizes security vulnerabilities and vulnerabilities

### Comment Threshold

- **`low`**: Includes all suggestions (low, medium, high, critical)
- **`medium`**: Only medium, high, and critical (default)
- **`high`**: Only high and critical issues
- **`critical`**: Only critical issues

### Poll Interval

Adjust `POLL_INTERVAL_SECONDS` to change how often the agent checks for new PRs:
- Default: 30 seconds
- Longer intervals reduce API usage
- Shorter intervals provide faster reviews

## How It Works

1. **Discovery**: The agent polls Azure DevOps for active pull requests
2. **Analysis**: For each new PR:
   - Fetches file changes
   - Gets the diff between source and target branches
   - Sends code to AI for analysis
3. **Review**: AI analyzes code for:
   - Bugs and logical errors
   - Security vulnerabilities
   - Performance issues
   - Code quality and maintainability
   - Best practices adherence
4. **Comments**: Posts inline comments on specific lines with:
   - Issue description
   - Why it's a problem
   - Suggested solution with code example
   - Severity level
5. **Summary**: Posts an overall PR summary with review statistics

## Example Review

When a PR is submitted with insecure code:

```python
# Example of code being reviewed
password = request.GET.get('password')  # Security vulnerability!
```

The agent will post:

> **🔴 HIGH**: Potential password exposure in URL parameters
> 
> **Issue**: Passwords should never be sent in URL parameters as they can be logged, cached, or exposed in browser history.
> 
> **Suggested fix:**
> ```python
> # Use POST request body or environment variables
> password = request.POST.get('password')
> # Or better: use environment variables or secure storage
> ```

## Monitoring

- **Logs**: Check `pr_review_agent.log` for detailed logs
- **Cache**: `reviewed_prs.json` tracks which PRs have been reviewed to avoid duplicates
- **Status**: Monitor service status using your process manager

## Troubleshooting

### Agent not reviewing PRs

1. Check logs: `tail -f pr_review_agent.log`
2. Verify credentials in `config.env`
3. Ensure PAT has correct permissions
4. Check internet connectivity to Azure DevOps and Google AI

### API Rate Limits

- Azure DevOps: 30,000 requests per hour per user (usually sufficient)
- Google Gemini: Free tier includes 60 requests per minute, 1,500 per day
- If hitting limits, increase `POLL_INTERVAL_SECONDS`

### Authentication Issues

- Ensure PAT is valid and not expired
- Verify PAT has "Code (read & write)" scope
- Check organization/project names are correct

## Security Notes

- **Never commit `config.env`**: It's in `.gitignore` for a reason
- **Rotate credentials**: Regularly update your PAT and API keys
- **Monitor costs**: Check usage in Google AI Studio (free tier is usually sufficient)
- **Review AI suggestions**: AI may suggest incorrect fixes - always verify

## Cost Estimation

- **Google Gemini**: FREE on the default tier (60 requests/min, 1,500/day)
- **Azure DevOps**: Free within tier limits
- **Compute**: Negligible for a simple service
- Upgrade to paid tier only if you need higher limits

## License

MIT

## Contributing

Contributions welcome! Areas for improvement:
- Support for more AI providers (Claude, GitHub Copilot, etc.)
- Custom review rules and patterns
- Integration with CI/CD pipelines
- Webhook-based triggering (faster than polling)
- Multi-project support
- Review history and analytics

## Support

For issues or questions:
1. Check the logs first
2. Review configuration
3. Open an issue on GitHub

---

**Made with ❤️ for better code reviews**

