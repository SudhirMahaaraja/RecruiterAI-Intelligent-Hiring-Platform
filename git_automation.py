import os
import subprocess
import random
import logging
from datetime import datetime, timedelta
import calendar

# ─── Configuration ──────────────────────────────────────────────────
# Set your Git identity if not already configured globally
GIT_USER_NAME = "Candidate Name"
GIT_USER_EMAIL = "candidate@example.com"

# Logging setup
logging.basicConfig(
    filename='git_automation.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ─── Task Templates ─────────────────────────────────────────────────
# These are used to generate meaningful commit messages and small changes
COMMIT_TASKS = [
    {"msg": "Refactor assessment logic for better performance", "file": "app.py", "type": "modify"},
    {"msg": "Update candidate dashboard UI styling", "file": "templates/candidate_dashboard.html", "type": "modify"},
    {"msg": "Add logging to coding round submission", "file": "app.py", "type": "modify"},
    {"msg": "Implement security checks for proctoring", "file": "app.py", "type": "modify"},
    {"msg": "Enhance resume parsing for technical skills", "file": "utils/resume_parser.py", "type": "modify"},
    {"msg": "Fix bug in AI match score calculation", "file": "utils/ai_screening.py", "type": "modify"},
    {"msg": "Improve mobile responsiveness of job detail page", "file": "templates/job_detail.html", "type": "modify"},
    {"msg": "Add helper for experience validation", "file": "app.py", "type": "modify"},
    {"msg": "Update pipeline stage labels for clarity", "file": "app.py", "type": "modify"},
    {"msg": "Create initial coding assessment problems", "file": "app.py", "type": "modify"},
    {"msg": "Fix rounding error in assessment scores", "file": "app.py", "type": "modify"},
    {"msg": "Optimize database queries for HR dashboard", "file": "app.py", "type": "modify"},
    {"msg": "Add documentation for proctoring API", "file": "app.py", "type": "modify"},
    {"msg": "Final project completion and cleanup", "file": "README.md", "type": "final"}
]

def run_git_command(command, env=None):
    """Executes a git command and returns output."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, **(env or {})}
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command failed: {' '.join(command)}")
        logging.error(f"Error: {e.stderr}")
        return None

def make_small_change(file_path, message):
    """Appends a comment to a file to simulate a code change."""
    # Ensure directory exists
    dir_name = os.path.dirname(file_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name)
        
    if not os.path.exists(file_path):
        # Create file if it doesn't exist
        with open(file_path, 'w') as f:
            f.write(f"# Project File: {file_path}\n\nInitial commit for {message}")
    
    with open(file_path, 'a') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"\n# Auto-commit: {message} - {timestamp}\n")

def simulate_development():
    """Generates a series of commits spanning the current month."""
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day
    
    last_day = calendar.monthrange(year, month)[1]
    
    # Calculate days to simulate (start from the 1st of the month)
    days_to_simulate = list(range(1, last_day + 1))
    
    logging.info(f"Starting Git automation for {calendar.month_name[month]} {year}")
    
    # Configure Git identity for this repo if needed
    run_git_command(['git', 'init']) # Ensure repo is initialized
    run_git_command(['git', 'config', 'user.name', GIT_USER_NAME])
    run_git_command(['git', 'config', 'user.email', GIT_USER_EMAIL])
    
    # Initial commit
    run_git_command(['git', 'add', '.'])
    init_date = datetime(year, month, 1, 9, 0, 0).strftime('%Y-%m-%dT%H:%M:%S')
    run_git_command(['git', 'commit', '-m', 'Initial project setup'], env={'GIT_AUTHOR_DATE': init_date, 'GIT_COMMITTER_DATE': init_date})
    
    task_idx = 0
    total_tasks = len(COMMIT_TASKS)
    
    for current_day in days_to_simulate:
        # Determine number of commits for today (1-3, more on some days)
        num_commits = random.randint(1, 3)
        if current_day == last_day:
            num_commits = 1 # Just the final commit on the last day
        
        for i in range(num_commits):
            if task_idx >= total_tasks:
                break
                
            task = COMMIT_TASKS[task_idx]
            
            # Generate a random time for the commit (between 9 AM and 8 PM)
            hour = random.randint(9, 20)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            
            commit_date = datetime(year, month, current_day, hour, minute, second)
            date_str = commit_date.strftime('%Y-%m-%dT%H:%M:%S')
            
            # Make the change
            make_small_change(task['file'], task['msg'])
            
            # Stage and commit with backdated timestamp
            run_git_command(['git', 'add', task['file']])
            
            env = {
                'GIT_AUTHOR_DATE': date_str,
                'GIT_COMMITTER_DATE': date_str
            }
            
            msg = task['msg']
            result = run_git_command(['git', 'commit', '-m', msg], env=env)
            
            if result:
                logging.info(f"Created commit on {date_str}: {msg}")
                print(f"Success: {date_str} - {msg}")
            
            task_idx += 1
            
        if task_idx >= total_tasks:
            break

    logging.info("Git automation completed successfully.")
    print("\nAll commits generated. Use 'git log' to verify history.")

if __name__ == "__main__":
    simulate_development()
