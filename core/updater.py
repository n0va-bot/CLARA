from git import Repo
from pathlib import Path

REPO_URL = "https://github.com/n0va-bot/CLARA"
REPO_DIR = Path(__file__).parent

def update_repository():
    try:
        repo = Repo(REPO_DIR)
        current_branch = repo.active_branch
        
        print(f"Fetching latest changes from {current_branch}...")
        origin = repo.remotes.origin
        origin.fetch()
        
        print(f"Pulling changes for branch {current_branch}...")
        origin.pull()
        
        print("Repository updated successfully.")
        return True
    except Exception as e:
        print(f"Error updating repository: {e}")
        return False

if __name__ == "__main__":
    REPO_DIR = Path(__file__).parent / ".."
    update_repository()