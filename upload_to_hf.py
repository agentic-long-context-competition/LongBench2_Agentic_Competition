#!/usr/bin/env python3
import os
import subprocess
from dotenv import load_dotenv
from huggingface_hub import HfApi, create_repo
from pathlib import Path

def get_current_git_commit():
    """Get the shortened commit ID of the currently active branch."""
    try:
        # Run git command to get the shortened commit hash
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        commit_id = result.stdout.strip()
        return commit_id
    except subprocess.CalledProcessError as e:
        print(f"Error getting git commit ID: {e}")
        return None
    except FileNotFoundError:
        print("Git command not found. Make sure git is installed.")
        return None

def upload_to_huggingface():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get Hugging Face token from environment variables
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN not found in .env file")
    
    # Initialize Hugging Face API client
    api = HfApi(token=hf_token)
    
    # Get Hugging Face username from environment variables or from the API
    hf_username = os.getenv("HF_USERNAME")
    if not hf_username:
        print("HF_USERNAME not found in .env file, retrieving from API token...")
        try:
            # Get user info from token
            user_info = api.whoami(token=hf_token)
            hf_username = user_info.get("name")
            if not hf_username:
                raise ValueError("Could not retrieve username from API token. Please set HF_USERNAME in .env file.")
            print(f"Username retrieved: {hf_username}")
        except Exception as e:
            print(f"Error retrieving username from API: {e}")
            raise ValueError("Could not retrieve username from API token. Please set HF_USERNAME in .env file.")
    
    # Get repository name from environment variables or use default
    repo_name = os.getenv("HF_REPO_NAME", "longbench-results")
    
    # Properly format the repository ID as username/repo-name
    repo_id = f"{hf_username}/{repo_name}"
    
    # Get current git commit ID for commit message
    commit_id = get_current_git_commit()
    # Get base commit message prefix - will add file path in the upload loop
    commit_prefix = f"Update from github (commit id) {commit_id}" if commit_id else "update"
    
    # Try to create the repository, handle the case if it already exists
    print(f"Checking/creating repository: {repo_id}")
    try:
        # Try to create the repository
        create_repo(repo_id, repo_type="dataset", private=False, token=hf_token)
        print(f"Repository created successfully")
    except Exception as e:
        # If the error is about the repository already existing, continue
        if "You already created this" in str(e) or "409" in str(e):
            print("Repository already exists, continuing with upload...")
        else:
            # Re-raise any other errors
            print(f"Error while creating repository: {e}")
            raise
    
    # Path to the results directory
    results_dir = Path("results")
    if not results_dir.exists() or not results_dir.is_dir():
        raise ValueError(f"Results directory not found at {results_dir}")
    
    # Upload all files in the results directory
    print(f"Uploading files from {results_dir} to {repo_id}")
    
    # Get all files in the results directory
    files_to_upload = []
    for file_path in results_dir.glob("**/*"):
        if file_path.is_file():
            files_to_upload.append(str(file_path))
    
    # Upload files to Hugging Face with custom commit message
    for file_path in files_to_upload:
        relative_path = os.path.relpath(file_path, start=".")
        # Create a commit message that includes both the git commit ID and file path
        file_commit_message = f"{commit_prefix} - {relative_path}"
        
        print(f"Uploading {relative_path}")
        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=relative_path,
            repo_id=repo_id,
            repo_type="dataset",
            token=hf_token,
            commit_message=file_commit_message,
        )
    
    print(f"Upload complete! Repository available at: https://huggingface.co/datasets/{repo_id}")
    if commit_id:
        print(f"Files were uploaded with commit messages including git commit ID: '{commit_id}'")

if __name__ == "__main__":
    upload_to_huggingface() 