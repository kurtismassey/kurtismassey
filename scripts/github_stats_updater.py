import os
from datetime import datetime, timedelta
from github import Github
import re
from collections import defaultdict

def get_commit_time_data(user):
    hourly_commits = defaultdict(lambda: defaultdict(int))  # day -> hour -> count
    daily_commits = defaultdict(int)  # day -> count
    
    # Get commits from the last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    for repo in user.get_repos():
        try:
            commits = repo.get_commits(since=thirty_days_ago, author=user.login)
            for commit in commits:
                commit_time = commit.commit.author.date
                day_name = commit_time.strftime('%a')
                hour = commit_time.hour
                
                hourly_commits[day_name][hour] += 1
                daily_commits[day_name] += 1
        except:
            continue
    
    return hourly_commits, daily_commits

def create_daily_commit_bars(daily_commits):
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    max_commits = max(daily_commits.values()) if daily_commits else 1
    
    bars = []
    for day in days:
        commits = daily_commits.get(day, 0)
        hours = round(commits * 24 / max_commits) if max_commits > 0 else 0
        bar_length = round(commits * 20 / max_commits) if max_commits > 0 else 0
        bar = '═' * bar_length
        bars.append(f"{day:<8} ╠{bar}╣ {hours}hrs")
    
    scale = "         0   4   8   12   16   20   24"
    return "\n".join(bars + [scale])

def create_heatmap(hourly_commits):
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    hours = range(24)
    
    # Create intensity map
    max_commits = max(
        commits
        for day_commits in hourly_commits.values()
        for commits in day_commits.values()
    ) if hourly_commits else 1
    
    intensity_chars = ['░░', '▒░', '▒▒', '█░', '█▒', '█▓', '██']
    
    # Create header
    heatmap = ['     ' + ' '.join(f'{h:02d}' for h in hours)]
    
    # Create heatmap rows
    for day in days:
        row = [f"{day:<5}"]
        for hour in hours:
            commits = hourly_commits.get(day, {}).get(hour, 0)
            intensity = int((commits * (len(intensity_chars) - 1)) / max_commits) if max_commits > 0 else 0
            row.append(intensity_chars[intensity])
        heatmap.append(' '.join(row))
        
    return '\n'.join(heatmap)

def get_github_stats(token):
    g = Github(token)
    user = g.get_user()
    
    # Get basic stats
    stats = {
        'stars': sum(repo.stargazers_count for repo in user.get_repos()),
        'prs': len(list(user.get_pulls())),
        'issues': len(list(user.get_issues())),
        'contributions': 0,
    }
    
    # Get commits for current year
    current_year = datetime.now().year
    commits = 0
    for repo in user.get_repos():
        try:
            commits += repo.get_commits(since=datetime(current_year, 1, 1)).totalCount
        except:
            continue
    
    stats['commits'] = commits
    
    # Get commit time data
    hourly_commits, daily_commits = get_commit_time_data(user)
    stats['hourly_commits'] = hourly_commits
    stats['daily_commits'] = daily_commits
    
    # Count contributed repositories in the last year
    contributed_repos = set()
    events = user.get_events()
    year_ago = datetime.now().replace(year=datetime.now().year - 1)
    
    for event in events:
        if event.created_at < year_ago:
            break
        if event.type in ['PushEvent', 'PullRequestEvent']:
            contributed_repos.add(event.repo.name)
    
    stats['contributed_to'] = len(contributed_repos)
    
    return stats

def create_stats_section(stats):
    daily_bars = create_daily_commit_bars(stats['daily_commits'])
    heatmap = create_heatmap(stats['hourly_commits'])
    
    stats_section = f"""
```txt
GitHub Stats Summary
╔══════════════════════════════════════╗
║ Total Stars Earned:     {str(stats['stars']).ljust(12)} ║
║ Total Commits ({datetime.now().year}):   {str(stats['commits']).ljust(12)} ║
║ Total PRs:              {str(stats['prs']).ljust(12)} ║
║ Total Issues:           {str(stats['issues']).ljust(12)} ║
║ Contributed to:         {str(stats['contributed_to']).ljust(12)} ║
╚══════════════════════════════════════╝

Commit Activity (Last 30 Days)
{daily_bars}

Commit Time Distribution
{heatmap}
```
"""
    return stats_section

def update_readme(stats):
    with open('README.md', 'r') as f:
        content = f.read()
    
    # Create the stats section
    stats_section = create_stats_section(stats)
    
    # Define the markers
    start_marker = '<!--START_SECTION:github_stats-->'
    end_marker = '<!--END_SECTION:github_stats-->'
    
    # Create the pattern
    pattern = f'({start_marker}).*({end_marker})'
    
    # If markers don't exist, add them
    if start_marker not in content:
        content += f'\n{start_marker}\n{stats_section}\n{end_marker}\n'
    else:
        # Replace the existing section
        content = re.sub(
            pattern,
            f'{start_marker}\n{stats_section}\n{end_marker}',
            content,
            flags=re.DOTALL
        )
    
    with open('README.md', 'w') as f:
        f.write(content)

def main():
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        raise ValueError("GitHub token not found")
    
    stats = get_github_stats(token)
    update_readme(stats)

if __name__ == "__main__":
    main() 