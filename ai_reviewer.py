"""
AI-powered code review module that analyzes code and provides suggestions.
"""
import os
import logging
from typing import List, Dict, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class AIReviewer:
    """AI reviewer for code analysis and suggestions."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        """
        Initialize AI reviewer using Google Gemini.
        
        Args:
            api_key: Google AI (Gemini) API key
            model: Model to use (gemini-2.0-flash-exp, gemini-pro, etc.)
        """
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)
        self.model = model
        self.review_style = os.getenv('REVIEW_MODE', 'detailed')
        self.comment_threshold = os.getenv('COMMENT_THRESHOLD', 'medium')
        
        logger.info(f"Initialized AI Reviewer with Gemini model: {model}")
    
    def review_code(
        self,
        file_path: str,
        content: str,
        old_content: Optional[str] = None,
        change_type: str = "edit"
    ) -> List[Dict]:
        """
        Review code for a file and return suggestions.
        
        Args:
            file_path: Path to the file
            content: Current file content
            old_content: Previous file content (for diffs)
            change_type: Type of change (add, edit, delete)
        
        Returns:
            List of review comments with line numbers and suggestions
        """
        try:
            # Analyze the code
            analysis = self._analyze_code(file_path, content, old_content, change_type)
            
            # Parse the analysis into line-specific comments
            comments = self._parse_analysis_to_comments(analysis, content, file_path)
            
            # Filter comments based on threshold
            filtered_comments = self._filter_comments(comments)
            
            logger.info(f"Generated {len(filtered_comments)} review comments for {file_path}")
            return filtered_comments
            
        except Exception as e:
            logger.error(f"Error reviewing code: {str(e)}")
            return []
    
    def _analyze_code(
        self,
        file_path: str,
        content: str,
        old_content: Optional[str],
        change_type: str
    ) -> str:
        """Use AI to analyze the code and generate review."""
        
        # Prepare the prompt based on review mode
        prompt = self._build_review_prompt(file_path, content, old_content, change_type)
        
        try:
            # Combine system prompt and user prompt for Gemini
            full_prompt = f"{self._get_system_prompt()}\n\n{prompt}"
            
            # Generate content with Gemini
            response = self.client.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=2000,
                )
            )
            
            analysis = response.text
            return analysis
            
        except Exception as e:
            logger.error(f"Error calling AI API: {str(e)}")
            return f"Error analyzing code: {str(e)}"
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt based on review mode."""
        
        base_prompt = """You are an expert code reviewer with deep knowledge of best practices, 
        security, performance, and code quality. Your task is to review code changes and provide 
        constructive, actionable feedback."""
        
        if self.review_style == 'detailed':
            return f"""{base_prompt}
        
        Review the code thoroughly and identify:
        1. Potential bugs and errors
        2. Security vulnerabilities
        3. Performance issues
        4. Code quality and maintainability
        5. Adherence to best practices and coding standards
        6. Documentation needs
        
        For each issue, provide:
        - The specific line number (if applicable)
        - The issue description
        - Why it's a problem
        - A suggested fix or improvement
        - Code example if helpful
        
        Format your response as:
        LINE_NUM: Issue description | Solution: [solution] | Severity: [low/medium/high]"""
        
        elif self.review_style == 'security-focused':
            return f"""{base_prompt}
        
        Focus primarily on security vulnerabilities:
        1. Injection attacks (SQL, XSS, command)
        2. Authentication and authorization issues
        3. Sensitive data exposure
        4. Insecure dependencies
        5. Misconfiguration
        6. Cryptographic failures
        
        Format your response as:
        LINE_NUM: Security issue | Solution: [solution] | Severity: [low/medium/high/critical]"""
        
        else:  # quick
            return f"""{base_prompt}
        
        Provide a quick review focusing on:
        1. Critical bugs
        2. Security issues
        3. Obvious code quality problems
        
        Be concise but actionable.
        
        Format your response as:
        LINE_NUM: Issue | Solution: [solution] | Severity: [low/medium/high]"""
    
    def _build_review_prompt(
        self,
        file_path: str,
        content: str,
        old_content: Optional[str],
        change_type: str
    ) -> str:
        """Build the review prompt for the AI."""
        
        # Determine file type
        file_ext = file_path.split('.')[-1] if '.' in file_path else ''
        language = self._detect_language(file_ext)
        
        prompt = f"""Please review the following code changes:
        
File: {file_path}
Change Type: {change_type}
Language: {language}

Current Code:
```{language}
{content}
```"""
        
        if old_content and change_type == 'edit':
            prompt += f"""

Previous Version (for comparison):
```{language}
{old_content}
```"""
        
        prompt += f"""

Please review this code and provide feedback. Focus on:
1. Potential bugs
2. Security vulnerabilities
3. Code quality and best practices
4. Performance optimizations

For each issue, specify the LINE_NUM, description, solution, and severity.
Only comment on lines that have actual issues."""
        
        return prompt
    
    def _detect_language(self, extension: str) -> str:
        """Detect programming language from file extension."""
        language_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'java': 'java',
            'go': 'go',
            'rs': 'rust',
            'cpp': 'cpp',
            'c': 'c',
            'cs': 'csharp',
            'rb': 'ruby',
            'php': 'php'
        }
        return language_map.get(extension.lower(), 'text')
    
    def _parse_analysis_to_comments(
        self,
        analysis: str,
        content: str,
        file_path: str
    ) -> List[Dict]:
        """
        Parse AI analysis into structured comments.
        
        Returns:
            List of comment dictionaries with line, text, and suggestion
        """
        comments = []
        lines = content.split('\n')
        
        # Split analysis by line
        analysis_lines = analysis.split('\n')
        
        for line in analysis_lines:
            line = line.strip()
            if not line or not line.startswith('LINE_NUM:'):
                continue
            
            try:
                # Parse the format: LINE_NUM: Issue | Solution: ... | Severity: ...
                parts = line.split('LINE_NUM:')[1].strip()
                
                # Extract line number (first number found)
                import re
                line_match = re.search(r'\d+', parts)
                if line_match:
                    line_num = int(line_match.group())
                    if 1 <= line_num <= len(lines):
                        # Extract the issue
                        issue_part = parts.split('|')[0] if '|' in parts else parts
                        issue = issue_part.split(':')[1].strip() if ':' in issue_part else issue_part
                        
                        # Extract solution
                        solution = ""
                        if 'Solution:' in line:
                            solution_part = line.split('Solution:')[1].split('|')[0].strip()
                            solution = solution_part
                        
                        # Extract severity
                        severity = 'medium'
                        if 'Severity:' in line:
                            severity_part = line.split('Severity:')[1].strip()
                            severity = severity_part.split('|')[0].strip() if '|' in severity_part else severity_part
                        
                        comment_text = f"**{severity.upper()}**: {issue}"
                        if solution:
                            comment_text += f"\n\n**Suggested fix:**\n```{self._detect_language(file_path.split('.')[-1] if '.' in file_path else '')}\n{solution}\n```"
                        
                        comments.append({
                            'line': line_num,
                            'text': comment_text,
                            'severity': severity.lower(),
                            'file_path': file_path
                        })
            except Exception as e:
                logger.warning(f"Could not parse line: {line}. Error: {str(e)}")
                continue
        
        return comments
    
    def _filter_comments(self, comments: List[Dict]) -> List[Dict]:
        """Filter comments based on severity threshold."""
        
        severity_map = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
        
        threshold = severity_map.get(self.comment_threshold.lower(), 2)
        
        filtered = []
        for comment in comments:
            comment_level = severity_map.get(comment.get('severity', 'medium').lower(), 2)
            if comment_level >= threshold:
                filtered.append(comment)
        
        return filtered

