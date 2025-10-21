"""GitHub service for creating pull requests."""
import yaml
from github import Github
from utils.validators import sanitize_filename


class GitHubService:
    """Service for creating GitHub pull requests."""
    
    def __init__(self, token: str):
        """Initialize with GitHub token."""
        self.github = Github(token)
    
    def create_pr_for_events(self, repo_url: str, events: list, 
                            submitted_by: str, submission_id: str) -> str:
        """
        Create a pull request for event submissions.
        
        Returns:
            str: URL of the created pull request
        """
        repo_name = repo_url.split('github.com/')[1]
        repo = self.github.get_repo(repo_name)
        
        branch_name = f'submission-{submission_id[:8]}'
        base_branch = repo.default_branch
        base_ref = repo.get_git_ref(f'heads/{base_branch}')
        
        repo.create_git_ref(f'refs/heads/{branch_name}', base_ref.object.sha)
        
        file_paths = []
        for event in events:
            event_data = {
                'title': event['title'],
                'date': event['date'],
                'time': event['time'],
                'url': event['url'],
                'location': event.get('location', ''),
                'cost': event.get('cost', ''),
                'submitted_by': submitted_by,
                'submitter_link': event.get('submitter_link', '')
            }
            
            if event.get('end_date'):
                event_data['end_date'] = event['end_date']
            
            event_yaml = yaml.dump(event_data, default_flow_style=False)
            safe_title = sanitize_filename(event['title'])
            file_name = f"_single_events/{event['date']}-{safe_title}.yaml"
            
            repo.create_file(
                path=file_name,
                message=f"Add event: {event['title']}",
                content=event_yaml,
                branch=branch_name
            )
            file_paths.append(file_name)
        
        pr_title = "Event Submission: Multiple" if len(events) > 1 else f"Event Submission: {events[0]['title']}"
        pr_body = "Submitted by: {}\nSubmitted via web form\n\nEvents:\n{}".format(
            submitted_by,
            "\n".join(f"- {event['title']} ({event['date']})" for event in events)
        )
        
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=base_branch
        )
        
        return pr.html_url
    
    def create_pr_for_meetup_groups(self, repo_url: str, groups: list, 
                                   submitted_by: str, submitter_link: str,
                                   submission_id: str) -> str:
        """
        Create a pull request for meetup group submissions.
        
        Returns:
            str: URL of the created pull request
        """
        repo_name = repo_url.split('github.com/')[1]
        repo = self.github.get_repo(repo_name)
        
        branch_name = f'submission-{submission_id[:8]}'
        base_branch = repo.default_branch
        base_ref = repo.get_git_ref(f'heads/{base_branch}')
        
        repo.create_git_ref(f'refs/heads/{branch_name}', base_ref.object.sha)
        
        file_paths = []
        for group in groups:
            group_data = {
                'name': group['name'],
                'website': group['url'],
                'rss': f"{group['url'].rstrip('/')}/events/rss/",
                'submitted_by': submitted_by,
                'submitter_link': submitter_link or '',
                'active': True
            }
            
            group_yaml = yaml.dump(group_data, default_flow_style=False)
            safe_name = sanitize_filename(group['name'])
            file_name = f"_groups/meetup-{safe_name}.yaml"
            
            repo.create_file(
                path=file_name,
                message=f"Add Meetup group: {group['name']}",
                content=group_yaml,
                branch=branch_name
            )
            file_paths.append(file_name)
        
        pr_title = "Add Meetup Group" if len(groups) == 1 else "Add Multiple Meetup Groups"
        pr_body = "Submitted by: {}\nSubmitted via web form\n\nGroups:\n{}".format(
            submitted_by,
            "\n".join(f"- {group['name']}" for group in groups)
        )
        
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=base_branch
        )
        
        return pr.html_url
    
    def create_pr_for_ical_feed(self, repo_url: str, group_data: dict, 
                               submission_id: str) -> str:
        """
        Create a pull request for iCal feed submission.
        
        Returns:
            str: URL of the created pull request
        """
        repo_name = repo_url.split('github.com/')[1]
        repo = self.github.get_repo(repo_name)
        
        branch_name = f'submission-{submission_id[:8]}'
        base_branch = repo.default_branch
        base_ref = repo.get_git_ref(f'heads/{base_branch}')
        
        repo.create_git_ref(f'refs/heads/{branch_name}', base_ref.object.sha)
        
        ical_data = {
            'name': group_data['name'],
            'website': group_data['url'],
            'ical': group_data['ical'],
            'fallback_url': group_data.get('fallback_url', ''),
            'submitted_by': group_data['submitted_by'],
            'submitter_link': group_data.get('submitter_link', ''),
            'active': True
        }
        
        ical_yaml = yaml.dump(ical_data, default_flow_style=False)
        safe_name = sanitize_filename(group_data['name'])
        file_name = f"_groups/ical-{safe_name}.yaml"
        
        repo.create_file(
            path=file_name,
            message=f"Add iCal group: {group_data['name']}",
            content=ical_yaml,
            branch=branch_name
        )
        
        pr_title = f"Add iCal Feed: {group_data['name']}"
        pr_body = "Submitted by: {}\nSubmitted via web form\n\nGroup: {}".format(
            group_data['submitted_by'],
            group_data['name']
        )
        
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=base_branch
        )
        
        return pr.html_url
