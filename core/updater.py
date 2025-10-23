from git import Repo, GitCommandError
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent

def update_repository():
    try:
        if not (REPO_DIR / ".git").exists():
            return "FAILED", "Not a git repository. Cannot update."

        repo = Repo(REPO_DIR)
        origin = repo.remotes.origin
        
        origin.fetch()
        
        local_commit = repo.head.commit
        remote_commit = origin.refs[repo.active_branch.name].commit
        
        if local_commit == remote_commit:
            return "UP_TO_DATE", "You are already on the latest version."
        
        origin.pull()
        
        return "UPDATED", "CLARA has been updated successfully."

    except GitCommandError as e:
        return "FAILED", f"An error occurred during the update:\n\n{e}"
    except Exception as e:
        return "FAILED", f"An unexpected error occurred:\n\n{e}"

if __name__ == "__main__":
    status, message = update_repository()
    print(f"Status: {status}\nMessage: {message}")