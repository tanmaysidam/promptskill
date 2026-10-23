"""
VanaSetu GitHub Push Utility
============================
Pushes the local Git repository directly to GitHub using pure-Python Dulwich.
Supports GitHub Personal Access Token (PAT) via CLI argument or environment variable.

Usage:
    py push_to_github.py <GITHUB_TOKEN>
    # or
    $env:GITHUB_TOKEN="ghp_your_token_here"
    py push_to_github.py
"""

import sys
import os
import dulwich.porcelain as p

REPO_URL = "https://github.com/tanmaysidam/promptskill.git"

def main():
    token = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        token = sys.argv[1].strip()
    else:
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

    if not token:
        print("=" * 70)
        print("GitHub Authentication Required")
        print("=" * 70)
        print("To push to https://github.com/tanmaysidam/promptskill.git, GitHub requires")
        print("a Personal Access Token (PAT) with 'repo' scope.")
        print()
        print("Please run:")
        print("    py push_to_github.py <YOUR_GITHUB_PAT>")
        print()
        print("Or set the environment variable:")
        print("    $env:GITHUB_TOKEN=\"ghp_your_token\"")
        print("    py push_to_github.py")
        print("=" * 70)
        sys.exit(1)

    # Clean token if URL was provided
    token = token.replace("https://", "").replace("@github.com", "").strip()

    # Form authenticated push target
    target_url = f"https://{token}@github.com/tanmaysidam/promptskill.git"

    print(f"Connecting to remote repository: {REPO_URL}...")
    try:
        repo = p.open_repo(".")
        print("Pushing 'main' branch...")
        p.push(repo, target_url, "refs/heads/main")
        print("=" * 70)
        print("SUCCESS! Successfully pushed VanaSetu to:")
        print(f"  {REPO_URL}")
        print("=" * 70)
    except Exception as e:
        print(f"Push failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
