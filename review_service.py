"""
Service for processing PR reviews and posting comments.
"""
import logging
import hashlib
import json
from typing import Dict, Set
from azure_devops_client import AzureDevOpsClient
from ai_reviewer import AIReviewer

logger = logging.getLogger(__name__)


class ReviewService:
    """Service to orchestrate PR reviews and commenting."""
    
    def __init__(self, client: AzureDevOpsClient, reviewer: AIReviewer):
        """
        Initialize review service.
        
        Args:
            client: Azure DevOps client
            reviewer: AI reviewer instance
        """
        self.client = client
        self.reviewer = reviewer
        self.reviewed_prs: Set[str] = set()  # Track reviewed PRs to avoid duplicates
        self.review_cache_file = 'reviewed_prs.json'
        self._load_reviewed_prs()
    
    def _load_reviewed_prs(self):
        """Load previously reviewed PRs from cache."""
        try:
            with open(self.review_cache_file, 'r') as f:
                data = json.load(f)
                self.reviewed_prs = set(data.get('prs', []))
                logger.info(f"Loaded {len(self.reviewed_prs)} previously reviewed PRs")
        except FileNotFoundError:
            logger.info("No previous review cache found")
            self.reviewed_prs = set()
        except Exception as e:
            logger.error(f"Error loading review cache: {str(e)}")
            self.reviewed_prs = set()
    
    def _save_reviewed_prs(self):
        """Save reviewed PRs to cache."""
        try:
            with open(self.review_cache_file, 'w') as f:
                json.dump({'prs': list(self.reviewed_prs)}, f)
        except Exception as e:
            logger.error(f"Error saving review cache: {str(e)}")
    
    def _get_pr_hash(self, repository_id: str, pull_request_id: int) -> str:
        """Generate a unique hash for a PR."""
        return hashlib.md5(f"{repository_id}_{pull_request_id}".encode()).hexdigest()
    
    def process_all_active_prs(self) -> int:
        """
        Process all active pull requests.
        
        Returns:
            Number of PRs processed
        """
        # Determine current sprint window (start, end) if available
        sprint_window = self.client.get_current_sprint_window()
        active_prs = self.client.get_active_pull_requests(date_window=sprint_window)
        processed_count = 0
        
        for pr in active_prs:
            pr_hash = self._get_pr_hash(pr.repository.id, pr.pull_request_id)
            
            if pr_hash not in self.reviewed_prs:
                try:
                    self.review_pull_request(pr)
                    self.reviewed_prs.add(pr_hash)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing PR {pr.pull_request_id}: {str(e)}")
        
        self._save_reviewed_prs()
        return processed_count
    
    def review_pull_request(self, pr):
        """
        Review a single pull request.
        
        Args:
            pr: GitPullRequest object
        """
        logger.info(f"Reviewing PR #{pr.pull_request_id}: {pr.title}")
        
        repository_id = pr.repository.id
        
        # Get file changes
        file_contents = self.client.get_file_content_with_diff(
            repository_id=repository_id,
            pr=pr
        )
        
        if not file_contents:
            logger.info(f"No file changes found for PR #{pr.pull_request_id}")
            return
        
        # Review each file
        total_comments = 0
        for file_path, file_info in file_contents.items():
            logger.info(f"Reviewing file: {file_path}")
            
            # Review the code
            comments = self.reviewer.review_code(
                file_path=file_path,
                content=file_info.get('content', ''),
                old_content=file_info.get('old_content'),
                change_type=file_info.get('change_type', 'edit')
            )
            
            # Post comments
            for comment in comments:
                success = self.client.post_line_comment(
                    repository_id=repository_id,
                    pull_request_id=pr.pull_request_id,
                    file_path=comment['file_path'],
                    line_number=comment['line'],
                    comment=comment['text']
                )
                
                if success:
                    total_comments += 1
            
            # If there are many issues, post a summary
            if len(comments) >= 5:
                summary = self._generate_summary(file_path, comments)
                self.client.post_file_comment(
                    repository_id=repository_id,
                    pull_request_id=pr.pull_request_id,
                    comment=summary
                )
        
        # Post overall summary
        if total_comments > 0:
            summary = self._generate_pr_summary(pr, total_comments)
            self.client.post_file_comment(
                repository_id=repository_id,
                pull_request_id=pr.pull_request_id,
                comment=summary
            )
        
        logger.info(f"Review completed for PR #{pr.pull_request_id}. Posted {total_comments} comments")
    
    def _generate_summary(self, file_path: str, comments: list) -> str:
        """Generate a summary for a file with many comments."""
        severity_count = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        
        for comment in comments:
            severity = comment.get('severity', 'medium')
            severity_count[severity] = severity_count.get(severity, 0) + 1
        
        summary = f"## Review Summary for {file_path}\n\n"
        summary += f"Found {len(comments)} issues:\n"
        
        if severity_count['critical'] > 0:
            summary += f"- 🔴 {severity_count['critical']} critical issues\n"
        if severity_count['high'] > 0:
            summary += f"- ⚠️ {severity_count['high']} high priority issues\n"
        if severity_count['medium'] > 0:
            summary += f"- ℹ️ {severity_count['medium']} medium priority issues\n"
        if severity_count['low'] > 0:
            summary += f"- 💡 {severity_count['low']} low priority suggestions\n"
        
        summary += "\nPlease review the inline comments for detailed feedback."
        
        return summary
    
    def _generate_pr_summary(self, pr, total_comments: int) -> str:
        """Generate an overall summary for the PR."""
        summary = f"""## 🤖 AI Code Review Summary

**PR:** #{pr.pull_request_id} - {pr.title}

**Review Results:**
- Total comments posted: {total_comments}
- Review status: {'Requires attention' if total_comments > 0 else 'Looks good!'}

"""
        
        if total_comments > 0:
            summary += "This PR has been automatically reviewed by an AI agent. "
            summary += "Please address the inline comments before merging.\n\n"
            summary += "---\n"
            summary += "*Review powered by AI Agent*"
        else:
            summary += "No issues detected. Ready to merge! 🎉"
        
        return summary

