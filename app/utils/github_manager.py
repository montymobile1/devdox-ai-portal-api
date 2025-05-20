from github import Github
from github.GithubException import GithubException
import base64
import traceback


class GitHubManager:
    def __init__(self, base_url="https://api.github.com", owner="", repo="", access_token=""):
        """Initialize GitHub manager with PyGithub."""
        # For GitHub Enterprise, you can specify base_url
        if base_url == "https://api.github.com":
            self.gh = Github(access_token)
        else:
            self.gh = Github(base_url=base_url, login_or_token=access_token)

        self.owner = owner
        self.repo = repo
        self.project = self.get_project()

    def get_project(self):
        """Get the GitHub repository object."""
        if self.owner != "" and self.repo != "":
            try:
                return self.gh.get_repo(f"{self.owner}/{self.repo}")
            except Exception as e:
                print(f"Error getting repository: {e}")
                return None
        else:
            return None

    def get_user(self):
        """Get the authenticated user information using PyGithub."""
        try:
            user = self.gh.get_user()
            return {
                "login": user.login,
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "html_url": user.html_url
            }
        except GithubException as e:
            print(f"Error fetching user: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error fetching user: {e}")
            return False

    def get_repos(self, page=1):
        """Get repositories for the authenticated user using PyGithub."""
        try:
            user = self.gh.get_user()
            # PyGithub uses 0-based indexing for pagination
            repos = user.get_repos(sort="updated", per_page=10)

            # Get the specific page
            repos_list = []
            start_index = (page - 1) * 10
            for i, repo in enumerate(repos):
                if i < start_index:
                    continue
                if i >= start_index + 10:
                    break

                repos_list.append({
                    "id": repo.id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "html_url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "ssh_url": repo.ssh_url,
                    "private": repo.private,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
                })

            return repos_list
        except GithubException as e:
            print(f"Error fetching repos: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching repos: {e}")
            return []


    def ensure_branch_exists(self, branch_name):
        """Ensure the branch exists; creates it if needed using PyGithub."""
        try:
            if not self.project:
                return None

            # Try to get the branch
            try:
                branch = self.project.get_branch(branch_name)
                return branch
            except GithubException:
                # Branch doesn't exist, create it from main
                try:
                    main_branch = self.project.get_branch("main")
                    main_sha = main_branch.commit.sha
                except GithubException:
                    # If main doesn't exist, try master
                    main_branch = self.project.get_branch("master")
                    main_sha = main_branch.commit.sha

                # Create the new branch
                ref = self.project.create_git_ref(
                    ref=f"refs/heads/{branch_name}",
                    sha=main_sha
                )
                return self.project.get_branch(branch_name)

        except GithubException as e:
            self.log_error("GitHub API error ensuring branch exists", e)
            return None
        except Exception as e:
            self.log_error("Unexpected error ensuring branch exists", e)
            return None

    def prepare_file_actions(self, files, branch_name):
        """Prepares file actions for commit using PyGithub."""
        actions = []

        if not self.project:
            return actions

        for file in files:
            file_path = file.get("file_path", "").replace("\\", "/").strip()
            file_content = file.get("content", "")

            if not file_path or file_content is None:
                continue  # Skip invalid files

            try:
                # Try to get the file to see if it exists
                existing_file = self.project.get_contents(file_path, ref=branch_name)
                action_type = "update"
                # Store the SHA for updates
                file["sha"] = existing_file.sha
            except GithubException:
                action_type = "create"
                file["sha"] = None

            actions.append({
                "action": action_type,
                "file_path": file_path,
                "content": file_content,
                "sha": file.get("sha")
            })

        return actions

    def commit_files(self, branch_name, commit_message, actions):
        """Commits all file changes to the branch using PyGithub."""
        try:
            if not self.project:
                return False

            # GitHub API doesn't support batch commits like GitLab
            # We need to commit files one by one using PyGithub
            for action in actions:
                file_path = action["file_path"]
                content = action["content"]
                action_type = action["action"]
                sha = action.get("sha")

                if action_type == "create":
                    self.project.create_file(
                        path=file_path,
                        message=commit_message,
                        content=content,
                        branch=branch_name
                    )
                elif action_type == "update" and sha:
                    self.project.update_file(
                        path=file_path,
                        message=commit_message,
                        content=content,
                        sha=sha,
                        branch=branch_name
                    )

            print("Successfully committed all file changes")
            return True

        except GithubException as e:
            self.log_error("GitHub API error committing files", e)
            return False
        except Exception as e:
            self.log_error("Unexpected error committing files", e)
            return False

    def create_merge_request(self, branch_name, merge_description):
        """Creates a pull request from the feature branch to main using PyGithub."""
        try:
            if not self.project:
                return None

            # Determine the base branch (main or master)
            try:
                self.project.get_branch("main")
                base_branch = "main"
            except GithubException:
                base_branch = "master"

            pr = self.project.create_pull(
                title=merge_description,
                body=merge_description,
                head=branch_name,
                base=base_branch
            )

            print(f"Successfully created pull request #{pr.number}")
            return pr

        except GithubException as e:
            self.log_error("GitHub API error creating pull request", e)
            return None
        except Exception as e:
            self.log_error("Unexpected error creating pull request", e)
            return None

    def log_error(self, message, exception):
        """Logs an error with traceback details."""
        print(f"{message}: {exception}")
        traceback.print_exc()