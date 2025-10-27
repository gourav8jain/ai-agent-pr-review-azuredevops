"""
Azure DevOps API Client for interacting with PRs, repositories, and code.
"""
import os
from typing import List, Dict, Optional
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
        
        logger.info(f"Initialized Azure DevOps client for {project_name}")
    
    def get_active_pull_requests(self) -> List[GitPullRequest]:
        """Get all active pull requests in the project."""
        try:
            repos = self.git_client.get_repositories(project=self.project_name)
            all_prs = []
            
            for repo in repos:
                try:
                    # Use the get_pull_requests method with proper parameters
                    # Note: Different API versions have different signatures
                    prs = self.git_client.get_pull_requests(repository_id=repo.id)
                    
                    # Filter for active PRs (status = 'active' or status = 0)
                    for pr in prs:
                        status = getattr(pr, 'status', None)
                        # PR is active if status is None, 0, or the string 'active'
                        if status is None or status == 0 or str(status).lower() == 'active':
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

