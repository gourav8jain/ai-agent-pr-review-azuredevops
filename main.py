"""
Main service for Azure DevOps PR review automation.
"""
import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from azure_devops_client import AzureDevOpsClient
from ai_reviewer import AIReviewer
from review_service import ReviewService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pr_review_agent.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def load_configuration():
    """Load configuration from environment variables."""
    # Load from .env file if it exists
    if os.path.exists('config.env'):
        load_dotenv('config.env')
    
    config = {
        'org_url': os.getenv('AZURE_DEVOPS_ORG_URL'),
        'pat': os.getenv('AZURE_DEVOPS_PERSONAL_ACCESS_TOKEN'),
        'project': os.getenv('AZURE_DEVOPS_PROJECT'),
        'google_ai_key': os.getenv('GOOGLE_AI_API_KEY'),
        'model': os.getenv('AI_MODEL', 'gemini-2.0-flash-exp'),
        'poll_interval': int(os.getenv('POLL_INTERVAL_SECONDS', '30'))
    }
    
    # Validate required configuration
    required = ['org_url', 'pat', 'project', 'google_ai_key']
    missing = [key for key in required if not config.get(key)]
    
    if missing:
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")
    
    return config


def main():
    """Main service loop."""
    logger.info("="*60)
    logger.info("Azure DevOps PR Review Agent Starting...")
    logger.info("="*60)
    
    try:
        # Load configuration
        config = load_configuration()
        
        logger.info(f"Configuration loaded:")
        logger.info(f"  Organization: {config['org_url']}")
        logger.info(f"  Project: {config['project']}")
        logger.info(f"  Model: {config['model']}")
        logger.info(f"  Poll Interval: {config['poll_interval']}s")
        
        # Initialize clients
        logger.info("Initializing Azure DevOps client...")
        client = AzureDevOpsClient(
            org_url=config['org_url'],
            personal_access_token=config['pat'],
            project_name=config['project']
        )
        
        logger.info("Initializing AI reviewer (Gemini)...")
        reviewer = AIReviewer(
            api_key=config['google_ai_key'],
            model=config['model']
        )
        
        # Initialize review service
        review_service = ReviewService(client, reviewer)
        
        logger.info("Service initialized successfully!")
        logger.info("Starting main loop...")
        logger.info("-"*60)
        
        # Main service loop
        iteration = 0
        while True:
            try:
                iteration += 1
                logger.info(f"\n[{datetime.now()}] Iteration #{iteration}")
                
                # Process all active PRs
                processed = review_service.process_all_active_prs()
                
                if processed > 0:
                    logger.info(f"Processed {processed} new PR(s)")
                else:
                    logger.debug("No new PRs to process")
                
                # Wait before next iteration
                logger.debug(f"Waiting {config['poll_interval']} seconds before next check...")
                time.sleep(config['poll_interval'])
                
            except KeyboardInterrupt:
                logger.info("\nReceived shutdown signal...")
                break
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                logger.info(f"Retrying in {config['poll_interval']} seconds...")
                time.sleep(config['poll_interval'])
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        logger.error("Service cannot start. Please check your configuration.")
        raise
    
    finally:
        logger.info("Service stopped.")
        logger.info("="*60)


if __name__ == "__main__":
    main()

