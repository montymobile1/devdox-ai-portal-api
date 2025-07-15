import pytest
import requests
from github import GithubException
from gitlab import GitlabError

from app.exceptions.custom_exceptions import DevDoxAPIException
from app.exceptions.exception_constants import GIT_PROJECT_FETCH_FAILED
from app.utils.git_managers import (
    AuthenticatedGitHubManager,
    AuthenticatedGitLabManager,
    GITHUB_REPOSITORY_NAME,
    GitHubManager,
    GITLAB_REPOSITORY_NAME,
    GitLabManager,
)

real_module_path = "app.utils.git_managers"


class DummyGitHubRepo:
    id = 100
    name = "repo"
    full_name = "org/repo"
    description = "description"
    private = True
    html_url = "https://github.com/org/repo"
    clone_url = "https://github.com/org/repo.git"
    ssh_url = "git@github.com:org/repo.git"
    default_branch = "main"
    language = "Python"
    size = 1234
    stargazers_count = 10
    watchers_count = 5
    forks_count = 1
    open_issues_count = 0
    created_at = None
    updated_at = None
    pushed_at = None
    owner = type("Owner", (), {"login": "dev", "id": 1, "type": "User"})
    permissions = type("Perms", (), {"admin": True, "push": False, "pull": True})()


class DummyGitHubUser:
    login = "dev"
    id = 1
    name = "Dev"
    email = "dev@example.com"
    avatar_url = "https://avatar"
    html_url = "https://github.com/dev"

    def get_repos(self, **kwargs):
        class DummyPaginated:
            totalCount = 1
            per_page = 2

            def get_page(self, page_index):
                return [DummyGitHubRepo()]

        return DummyPaginated()


class TestGitHubManager:
    def test_extract_repo_info(self):
        repo = DummyGitHubRepo()
        info = GitHubManager.extract_repo_info(repo)
        assert info["id"] == 100
        assert info["permissions"] == {"admin": True, "push": False, "pull": True}

    def test_authenticated_repo_pagination_bounds(self):
        assert GitHubManager.validate_per_page(200) == 30  # default fallback
        assert GitHubManager.validate_page(-1) == 1

    def test_authenticate_failure(self, monkeypatch):
        class FailingGithub:
            def __init__(*args, **kwargs):
                raise GithubException(401, "Unauthorized", None)

        monkeypatch.setattr(f"{real_module_path}.Github", FailingGithub)

        manager = GitHubManager()
        with pytest.raises(DevDoxAPIException) as exc_info:
            manager.authenticate("bad-token")
        assert "GitHub authentication failed" in str(exc_info.value)

    def test_get_user_repositories_raises(self, monkeypatch):
        class FailingUser:
            def get_repos(self, **kwargs):
                class Bad:
                    def get_page(self, i):
                        raise GithubException(500, "Fail", None)

                    per_page = 2
                    totalCount = 1

                return Bad()

        class Client:
            def get_user(self):
                return FailingUser()

        manager = AuthenticatedGitHubManager("https://api.github.com", Client())

        with pytest.raises(DevDoxAPIException) as exc_info:
            manager.get_user_repositories()
        assert GIT_PROJECT_FETCH_FAILED.format(repository=GITHUB_REPOSITORY_NAME) in str(exc_info.value)


class TestAuthenticatedGitHubManager:
    def test_github_manager_authenticate_default(self, monkeypatch):
        dummy_auth = AuthenticatedGitHubManager(
            "https://api.github.com", "dummy_client"
        )

        class DummyGitHub:
            def __init__(self, token):
                assert token == "valid"

            def authenticate(self, token):
                return dummy_auth

        monkeypatch.setattr(f"{real_module_path}.Github", DummyGitHub)

        manager = GitHubManager()
        auth = manager.authenticate("valid")
        assert isinstance(auth, AuthenticatedGitHubManager)

    def test_authenticated_manager_get_user(self, monkeypatch):
        dummy_user = DummyGitHubUser()

        dummy_client = type("Client", (), {"get_user": lambda self: dummy_user})()
        manager = AuthenticatedGitHubManager("https://api.github.com", dummy_client)

        user_info = manager.get_user()
        assert user_info.login == "dev"
        assert hasattr(user_info, "html_url")

    def test_authenticated_manager_repositories(self, monkeypatch):
        dummy_client = type(
            "Client", (), {"get_user": lambda self: DummyGitHubUser()}
        )()
        manager = AuthenticatedGitHubManager("https://api.github.com", dummy_client)

        result = manager.get_user_repositories(page=2, per_page=5)
        assert result["pagination_info"]["current_page"] == 2
        assert isinstance(result["repositories"], list)

    def test_authenticate_custom_url(self, monkeypatch):
        dummy_auth = AuthenticatedGitHubManager("https://custom.api", "client")

        class DummyGitHub:
            def __init__(self, base_url, login_or_token):
                assert base_url == "https://custom.api"
                assert login_or_token == "valid"

        monkeypatch.setattr(f"{real_module_path}.Github", DummyGitHub)

        manager = GitHubManager(base_url="https://custom.api")
        manager.authenticate("valid")


class DummyGitLab:
    def __init__(self, url, private_token):
        assert private_token == "good-token"
        assert url.startswith("https://gitlab.com")
        self._authenticated = False

    def auth(self):
        self._authenticated = True

    def projects(self):
        """Dummy Project, meant to just mimic the actual operation"""
        pass


class DummyGitLabRepo:
    def __init__(self):
        self._data = [{"id": 1, "name": "test"}]
        self._headers = {"X-Total-Pages": "1", "X-Next-Page": "", "X-Prev-Page": ""}

    def json(self):
        return self._data

    def raise_for_status(self):
        """
        For Testing, should remain empty
        """
        pass

    @property
    def headers(self):
        return self._headers


class DummySession:
    def get(self, url, headers=None):
        return DummyGitLabRepo()


class TestGitLabManager:
    def test_gitlab_authenticate_success(self, monkeypatch):
        monkeypatch.setattr(f"{real_module_path}.gitlab.Gitlab", DummyGitLab)
        manager = GitLabManager()
        auth = manager.authenticate("good-token")
        assert isinstance(auth, AuthenticatedGitLabManager)
        assert auth._git_client._authenticated is True

    def test_gitlab_authenticate_failure(self, monkeypatch):
        def raise_auth(*args, **kwargs):
            raise GitlabError("auth failed")

        monkeypatch.setattr(f"{real_module_path}.gitlab.Gitlab", raise_auth)

        manager = GitLabManager()
        with pytest.raises(DevDoxAPIException) as exc_info:
            manager.authenticate("bad-token")
        assert "GitLab authentication failed" in str(exc_info.value)


class TestAuthenticatedGitLabManager:
    def test_get_user_success(self):
        class DummyRequests:
            def get(self, url, headers=None, *args, **kwargs):
                class Response:
                    def raise_for_status(self):
                        """
                        For Testing, should remain empty
                        """
                        pass

                    def json(self):
                        return {"id": 1, "username": "dev"}

                return Response()

            def Session(self):
                return self

        manager = AuthenticatedGitLabManager(
            "https://gitlab.com",
            DummyGitLab("https://gitlab.com", "good-token"),
            "good-token",
            session=DummyRequests(),
        )
        user = manager.get_user()
        assert user["username"] == "dev"

    def test_get_user_failure(self):
        class DummyRequests:
            def get(self, url, headers=None, *args, **kwargs):
                raise requests.exceptions.RequestException("fail")

            def Session(self):
                return self

        manager = AuthenticatedGitLabManager(
            "https://gitlab.com",
            DummyGitLab("https://gitlab.com", "good-token"),
            "good-token",
            session=DummyRequests(),
        )
        with pytest.raises(DevDoxAPIException) as exc_info:
            manager.get_user()
        assert GIT_PROJECT_FETCH_FAILED.format(repository=GITLAB_REPOSITORY_NAME) in str(exc_info.value)

    def test_get_user_repositories_success(self):
        class DummyRequests:
            def get(self, url, headers=None, *args, **kwargs):
                class Response:
                    def raise_for_status(self):
                        """
                        For Testing, should remain empty
                        """
                        pass

                    def json(self):
                        return [{"id": 42, "name": "repo"}]

                    headers = {
                        "X-Total-Pages": "2",
                        "X-Next-Page": "2",
                        "X-Prev-Page": "",
                    }

                return Response()

            def Session(self):
                return self

        manager = AuthenticatedGitLabManager(
            "https://gitlab.com",
            DummyGitLab("https://gitlab.com", "good-token"),
            "good-token",
            session=DummyRequests(),
        )
        repos = manager.get_user_repositories(page=1, per_page=20)
        assert isinstance(repos["repositories"], list)
        assert repos["pagination_info"]["total_pages"] == 2

    def test_get_user_repositories_failure(self):
        class DummyRequests:
            def get(self, url, headers=None, *args, **kwargs):
                raise requests.exceptions.RequestException("fail")

            def Session(self):
                return self

        manager = AuthenticatedGitLabManager(
            "https://gitlab.com",
            DummyGitLab("https://gitlab.com", "good-token"),
            "good-token",
            session=DummyRequests(),
        )
        with pytest.raises(DevDoxAPIException) as exc_info:
            manager.get_user_repositories()
        assert GIT_PROJECT_FETCH_FAILED.format(repository=GITLAB_REPOSITORY_NAME) in str(exc_info.value)

    def test_get_user_repositories_missing_headers(self):
        class DummyRequests:
            def get(self, url, headers=None, *args, **kwargs):
                class Response:
                    def raise_for_status(self):
                        """
                        For Testing, should remain empty
                        """
                        pass

                    def json(self):
                        return [{"id": 99}]

                    headers = {}

                return Response()

            def Session(self):
                return self

        manager = AuthenticatedGitLabManager(
            "https://gitlab.com",
            DummyGitLab("https://gitlab.com", "good-token"),
            "good-token",
            session=DummyRequests(),
        )
        result = manager.get_user_repositories()
        assert result["pagination_info"]["total_pages"] == 1
