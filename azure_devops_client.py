"""
Azure DevOps API Client for interacting with PRs, repositories, and code.
"""
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
from azure.devops.connection import Connection
from azure.devops.v7_0.git import GitPullRequest
from azure.devops.v7_0.git.models import Comment, CommentPosition, CommentThread
from msrest.authentication import BasicAuthentication
import logging

logger = logging.getLogger(__name__)


class AzureDevOpsClient:
    """Client for interacting with Azure DevOps API."""
    
    def __init__(self, org_url: str, personal_access_token: str, project_name: str):
        """
        Initialize Azure DevOps client.
        
        Args:
            org_url: Organization URL (e.g., https://dev.azure.com/your-org)
            personal_access_token: Azure DevOps PAT
            project_name: Project name
        """
        self.org_url = org_url
        self.project_name = project_name
        
        # Create connection
        credentials = BasicAuthentication('', personal_access_token)
        self.connection = Connection(base_url=org_url, creds=credentials)
        
        # Get clients
        self.git_client = self.connection.clients.get_git_client()
        self.core_client = self.connection.clients.get_core_client()
        self.work_client = self.connection.clients.get_work_client()
        
        logger.info(f"Initialized Azure DevOps client for {project_name}")
    
    def get_active_pull_requests(self, date_window: Optional[Tuple] = None) -> List[GitPullRequest]:
        """Get all active pull requests in the project.

        Args:
            date_window: Optional tuple (start_datetime, end_datetime) to filter PRs created/updated within sprint
        """
        try:
            repos = self.git_client.get_repositories(project=self.project_name)
            all_prs = []
            
            for repo in repos:
                try:
                    # Use the get_pull_requests method with proper parameters
                    # Note: Different API versions have different signatures
                    prs = self.git_client.get_pull_requests(repository_id=repo.id)
                    
                    # Filter for active PRs (status = 'active' or status = 0) and within date window if provided
                    for pr in prs:
                        status = getattr(pr, 'status', None)
                        if status is None or status == 0 or str(status).lower() == 'active':
                            if self._is_pr_in_window(pr, date_window):
                                all_prs.append(pr)
                    
                except TypeError as te:
                    # Different API version, try without search_criteria
                    try:
                        prs = self.git_client.get_pull_requests(
                            repository_id=repo.id,
                            search_criteria=None
                        )
                        for pr in prs:
                            status = getattr(pr, 'status', None)
                            if status is None or status == 0:
                                if self._is_pr_in_window(pr, date_window):
                                    all_prs.append(pr)
                    except Exception as e:
                        logger.debug(f"Alternative method failed for repo {repo.name}: {str(e)}")
                except Exception as e:
                    logger.debug(f"Error fetching PRs from repo {repo.name}: {str(e)}")
            
            logger.info(f"Found {len(all_prs)} active pull requests")
            return all_prs
        except Exception as e:
            logger.error(f"Error fetching active PRs: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _is_pr_in_window(self, pr: GitPullRequest, date_window: Optional[Tuple]) -> bool:
        """Return True if PR falls within the given (start, end) window.

        Uses PR creation or last updated date for inclusion.
        """
        if not date_window:
            return True
        start_dt, end_dt = date_window
        pr_created = getattr(pr, 'creation_date', None)
        pr_updated = getattr(pr, 'closed_date', None) or getattr(pr, 'last_merge_source_commit', None)
        # Fallback to created date when updated isn't available
        candidate = pr_created
        try:
            if pr_updated and hasattr(pr_updated, 'date'):
                candidate = pr_updated
        except Exception:
            pass
        try:
            return (candidate is not None) and (candidate >= start_dt) and (candidate <= end_dt)
        except Exception:
            return True

    def get_current_sprint_window(self) -> Optional[Tuple]:
        """Fetch current sprint window (start, end) for the project based on current date.
        
        Finds the iteration/sprint that contains today's date by checking all teams
        and their iterations.
        
        Returns:
            Tuple of (start_date, end_date) for the current iteration, or None if not found
        """
        try:
            from azure.devops.v7_0.work.models import TeamContext
            
            # Get current date (timezone-aware if possible)
            current_date = datetime.now(timezone.utc).date()
            logger.debug(f"Looking for sprint containing date: {current_date}")
            
            # Get all teams for the project
            teams = self.core_client.get_teams(project_id=self.project_name)
            if not teams:
                logger.warning(f"No teams found for project {self.project_name}")
                return None
            
            # Try each team to find the current iteration
            for team in teams:
                try:
                    team_name = team.name
                    logger.debug(f"Checking team: {team_name}")
                    
                    # Build team context
                    team_context = TeamContext(project=self.project_name, team=team_name)
                    
                    # Get iterations (current and future) to ensure we find the right one
                    # We check both because Azure DevOps 'current' might not always align with today's date
                    all_iterations = []
                    for timeframe in ['current', 'future']:
                        try:
                            iterations = self.work_client.get_team_iterations(
                                team_context=team_context, 
                                timeframe=timeframe
                            )
                            if iterations:
                                all_iterations.extend(iterations)
                        except Exception as e:
                            logger.debug(f"Could not get {timeframe} iterations for team {team_name}: {str(e)}")
                            continue
                    
                    # If still no match, try past iterations (in case of date configuration issues)
                    if not all_iterations:
                        try:
                            past_iterations = self.work_client.get_team_iterations(
                                team_context=team_context, 
                                timeframe='past'
                            )
                            if past_iterations:
                                all_iterations.extend(past_iterations[-5:])  # Only check last 5 past iterations
                        except Exception as e:
                            logger.debug(f"Could not get past iterations for team {team_name}: {str(e)}")
                    
                    # Find the iteration that contains the current date
                    for iteration in all_iterations:
                        if iteration.attributes and hasattr(iteration.attributes, 'start_date') and hasattr(iteration.attributes, 'finish_date'):
                            start_date = iteration.attributes.start_date
                            finish_date = iteration.attributes.finish_date
                            
                            # Convert dates to date objects if they're datetime objects
                            if isinstance(start_date, datetime):
                                start_date = start_date.date()
                            if isinstance(finish_date, datetime):
                                finish_date = finish_date.date()
                            
                            # Check if current date falls within this iteration
                            if start_date and finish_date:
                                if start_date <= current_date <= finish_date:
                                    logger.info(f"Found current sprint: {iteration.name} ({start_date} to {finish_date}) for team {team_name}")
                                    # Return as datetime objects for consistency
                                    start_dt = datetime.combine(start_date, datetime.min.time())
                                    finish_dt = datetime.combine(finish_date, datetime.max.time())
                                    # Make timezone-aware if needed
                                    if start_dt.tzinfo is None:
                                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                                    if finish_dt.tzinfo is None:
                                        finish_dt = finish_dt.replace(tzinfo=timezone.utc)
                                    return (start_dt, finish_dt)
                    
                except Exception as e:
                    logger.debug(f"Error checking team {team.name if hasattr(team, 'name') else 'unknown'}: {str(e)}")
                    continue
            
            # If no iteration found, try using the 'current' timeframe on first team
            logger.info("No iteration found containing current date, trying 'current' timeframe...")
            first_team = teams[0]
            team_context = TeamContext(project=self.project_name, team=first_team.name)
            iterations = self.work_client.get_team_iterations(team_context=team_context, timeframe='current')
            if iterations and len(iterations) > 0:
                it = iterations[0]
                if it.attributes and hasattr(it.attributes, 'start_date') and hasattr(it.attributes, 'finish_date'):
                    start_date = it.attributes.start_date
                    finish_date = it.attributes.finish_date
                    logger.info(f"Using 'current' sprint: {it.name} ({start_date} to {finish_date})")
                    return (start_date, finish_date)
            
            logger.info("No current sprint found for any team; defaulting to all dates")
            return None
            
        except Exception as e:
            logger.warning(f"Could not get current sprint window: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def get_pull_request_changes(self, repository_id: str, pull_request_id: int) -> List[Dict]:
        """
        Get the file changes for a pull request.
        
        Returns:
            List of dictionaries with file change information
        """
        try:
            # Get PR details
            pr = self.git_client.get_pull_request(
                project=self.project_name,
                repository_id=repository_id,
                pull_request_id=pull_request_id
            )
            
            # Get file differences
            source_version = pr.source_ref_name.replace('refs/heads/', '')
            target_version = pr.target_ref_name.replace('refs/heads/', '')
            
            # Get commits in the PR
            commits = self.git_client.get_pull_request_commits(
                project=self.project_name,
                repository_id=repository_id,
                pull_request_id=pull_request_id
            )
            
            if not commits:
                return []
            
            # Get changes for the latest commit
            latest_commit_id = commits[0].commit_id
            
            # Get file diffs
            changes = self.git_client.get_commit_diffs(
                project=self.project_name,
                repository_id=repository_id,
                base_version=target_version,
                target_version=source_version
            )
            
            file_changes = []
            if changes and hasattr(changes, 'change_entries'):
                for entry in changes.change_entries:
                    file_change = {
                        'path': entry.item.path,
                        'change_type': entry.change_type,
                        'git_object_type': entry.item.git_object_type
                    }
                    
                    # Get the file content if it's a text file
                    if entry.item.git_object_type == 'blob' and entry.change_type in ['add', 'edit']:
                        try:
                            # Get file content
                            item = self.git_client.get_item(
                                project=self.project_name,
                                repository_id=repository_id,
                                path=entry.item.path,
                                version=latest_commit_id
                            )
                            file_change['content'] = item.content
                        except:
                            file_change['content'] = None
                    
                    file_changes.append(file_change)
            
            return file_changes
            
        except Exception as e:
            logger.error(f"Error fetching PR changes: {str(e)}")
            return []
    
    def get_file_content_with_diff(self, repository_id: str, pr: GitPullRequest) -> Dict[str, Dict]:
        """
        Get file contents with diff information.
        
        Returns:
            Dictionary mapping file paths to their content and line information
        """
        try:
            source_version = pr.source_ref_name.replace('refs/heads/', '')
            target_version = pr.target_ref_name.replace('refs/heads/', '')
            
            # Get the diff
            diffs = self.git_client.get_commit_diffs(
                project=self.project_name,
                repository_id=repository_id,
                base_version=target_version,
                target_version=source_version,
                top=10000,
                skip=0
            )
            
            file_contents = {}
            
            if diffs and hasattr(diffs, 'change_entries'):
                for entry in diffs.change_entries:
                    if entry.item.git_object_type == 'blob' and entry.change_type in ['add', 'edit']:
                        try:
                            # Get the file content for the source version
                            item = self.git_client.get_item_content(
                                project=self.project_name,
                                repository_id=repository_id,
                                path=entry.item.path,
                                version_descriptor={'version': source_version, 'version_type': 'branch'}
                            )
                            
                            # Parse content
                            if isinstance(item, bytes):
                                content = item.decode('utf-8')
                            else:
                                content = str(item)
                            
                            # Get the old version for diff
                            old_content = None
                            try:
                                old_item = self.git_client.get_item_content(
                                    project=self.project_name,
                                    repository_id=repository_id,
                                    path=entry.item.path,
                                    version_descriptor={'version': target_version, 'version_type': 'branch'}
                                )
                                if isinstance(old_item, bytes):
                                    old_content = old_item.decode('utf-8')
                                else:
                                    old_content = str(old_item)
                            except:
                                old_content = ""
                            
                            file_contents[entry.item.path] = {
                                'content': content,
                                'old_content': old_content,
                                'change_type': entry.change_type,
                                'lines_added': len(content.splitlines()),
                                'lines_removed': len(old_content.splitlines()) if old_content else 0
                            }
                        except Exception as e:
                            logger.warning(f"Could not get content for {entry.item.path}: {str(e)}")
                            continue
            
            return file_contents
            
        except Exception as e:
            logger.error(f"Error getting file content with diff: {str(e)}")
            return {}
    
    def post_line_comment(
        self,
        repository_id: str,
        pull_request_id: int,
        file_path: str,
        line_number: int,
        comment: str,
        comment_thread_id: int = None
    ) -> bool:
        """
        Post a comment on a specific line of code.
        
        Args:
            repository_id: Repository ID
            pull_request_id: Pull request ID
            file_path: Path to the file
            line_number: Line number (1-indexed)
            comment: Comment text
            comment_thread_id: Optional thread ID for replies
        
        Returns:
            True if successful
        """
        try:
            # Create comment position
            position = CommentPosition(
                line=line_number
            )
            
            # Create the comment
            new_comment = Comment(
                content=comment
            )
            
            # Create or update thread
            if comment_thread_id:
                # Reply to existing thread
                self.git_client.update_pull_request_thread(
                    project=self.project_name,
                    repository_id=repository_id,
                    pull_request_id=pull_request_id,
                    thread_id=comment_thread_id,
                    comment=Comment(content=comment)
                )
            else:
                # Create new thread
                thread = CommentThread(
                    comments=[new_comment],
                    status='active',
                    file_path=file_path
                )
                
                self.git_client.create_thread(
                    project=self.project_name,
                    repository_id=repository_id,
                    pull_request_id=pull_request_id,
                    thread=thread
                )
            
            logger.info(f"Posted comment on line {line_number} of {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error posting comment: {str(e)}")
            return False
    
    def post_file_comment(
        self,
        repository_id: str,
        pull_request_id: int,
        comment: str
    ) -> bool:
        """
        Post a general comment on the PR (not line-specific).
        
        Args:
            repository_id: Repository ID
            pull_request_id: Pull request ID
            comment: Comment text
        
        Returns:
            True if successful
        """
        try:
            # Create a comment thread for the entire PR
            thread = CommentThread(
                comments=[Comment(content=comment)],
                status='active'
            )
            
            self.git_client.create_thread(
                project=self.project_name,
                repository_id=repository_id,
                pull_request_id=pull_request_id,
                thread=thread
            )
            
            logger.info(f"Posted file comment on PR {pull_request_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error posting file comment: {str(e)}")
            return False

