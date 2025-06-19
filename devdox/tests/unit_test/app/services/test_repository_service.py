import datetime
from uuid import uuid4

import pytest

from app.exceptions.custom_exceptions import BadRequest, ResourceNotFound
from app.schemas.basic import PaginationParams, RequiredPaginationParams
from app.schemas.repo import GitRepoResponse, RepoResponse
from app.services.repository_service import RepoProviderService, RepoQueryService
from app.utils.auth import UserClaims


class StubRepo:
    def __init__(self, token_id="t1"):
        self.id = uuid4()
        self.user_id = "user123"
        self.repo_id = "r123"
        self.repo_name = "test"
        self.description = "desc"
        self.html_url = "http://test.com"
        self.default_branch = "main"
        self.forks_count = 1
        self.stargazers_count = 2
        self.is_private = True
        self.visibility = "public"
        self.language = "Python"
        self.size = 100
        self.repo_created_at = datetime.datetime.now()
        self.repo_updated_at = datetime.datetime.now()
        self.created_at = datetime.datetime.now()
        self.updated_at = datetime.datetime.now()
        self.token_id = token_id
        self.git_hosting = None


class StubRepoStore:
    def __init__(self, count=1, repos=None):
        self._count = count
        self._repos = repos or []

    async def count_by_user(self, user_id):
        return self._count

    async def get_all_by_user(self, user_id, offset, limit):
        return self._repos[offset : offset + limit]


class StubLabelStore:
    def __init__(self, labels):
        self.labels = labels

    async def get_git_hosting_map_by_token_id(self, token_ids):
        return self.labels


@pytest.mark.asyncio
class TestRepoQueryService:

    @pytest.fixture
    def pagination(self):
        return PaginationParams(limit=10, offset=0)

    @pytest.fixture
    def user(self):
        return UserClaims(sub="user123", email="u@example.com", name="User")

    async def test_returns_empty_if_no_repo(self, user, pagination):
        service = RepoQueryService(
            repo_store=StubRepoStore(count=0),
            gl_store=StubLabelStore(labels=[])
        )
        total, repos = await service.get_all_user_repositories(user, pagination)
        assert total == 0
        assert repos == []

    async def test_enriches_git_hosting(self, user, pagination):
        repo = StubRepo(token_id="token123")
        service = RepoQueryService(
            repo_store=StubRepoStore(repos=[repo]),
            gl_store=StubLabelStore(labels=[{"id": "token123", "git_hosting": "github"}])
        )
        total, repos = await service.get_all_user_repositories(user, pagination)
        assert total == 1
        assert repos[0].git_hosting == "github"

    async def test_git_hosting_missing_stays_none(self, user, pagination):
        repo = StubRepo(token_id="unknown")
        service = RepoQueryService(
            repo_store=StubRepoStore(repos=[repo]),
            gl_store=StubLabelStore(labels=[])
        )
        total, repos = await service.get_all_user_repositories(user, pagination)
        assert repos[0].git_hosting is None

    async def test_all_fields_transform_correctly(self, user, pagination):
        repo = StubRepo()
        service = RepoQueryService(
            repo_store=StubRepoStore(repos=[repo]),
            gl_store=StubLabelStore(labels=[{"id": "t1", "git_hosting": "gitlab"}])
        )
        total, repos = await service.get_all_user_repositories(user, pagination)
        response = repos[0]
        assert isinstance(response, RepoResponse)
        assert response.repo_name == "test"
        assert response.repo_id == "r123"
        assert response.token_id == "t1"
        assert response.git_hosting == "gitlab"


# === Fakes for RepoProviderService ===
class FakeUser:
    def __init__(self, encryption_salt="fake_salt"):
        self.encryption_salt = encryption_salt


class FakeLabel:
    def __init__(self, token_value="encrypted_token", git_hosting="github"):
        self.token_value = token_value
        self.git_hosting = git_hosting


class FakeLabelWithUnknownHosting:
    def __init__(self):
        self.token_value = "encrypted_token"
        self.git_hosting = "unknown"


class FakeLabelStore:
    async def get_by_token_id_and_user(self, token_id, user_id):
        return FakeLabel()


class FakeLabelStoreWithUnknownHosting:
    async def get_by_token_id_and_user(self, token_id, user_id):
        return FakeLabelWithUnknownHosting()


class FakeNoneLabelStore:
    async def get_by_token_id_and_user(self, token_id, user_id):
        return None


class FakeUserStore:
    async def get_by_user_id(self, user_id):
        return FakeUser()


class FakeNoneUserStore:
    async def get_by_user_id(self, user_id):
        return None


class FakeEncryption:
    def decrypt_for_user(self, encrypted_text, salt_b64):
        assert encrypted_text == "encrypted_token"
        assert salt_b64 == "fake_salt"
        return "decrypted_token"


class FakeFetcher:
    def fetch_user_repositories(self, token, offset, limit):
        return {
            "data_count": 1,
            "data": [
                GitRepoResponse(
                    id="abc123",
                    repo_name="test_repo",
                    description="Test repo",
                    html_url="https://example.com/repo",
                    default_branch="main",
                    forks_count=1,
                    stargazers_count=2,
                    size=100,
                    repo_created_at=datetime.datetime.utcnow(),
                    private=True,
                    visibility=None,
                )
            ],
        }


class FakeRepoFetcher:
    def get(self, provider):
        if provider == "github":
            return FakeFetcher(), lambda x: x
        return None, None


class TestRepoProviderService:
    @pytest.mark.asyncio
    async def test_get_all_provider_repos_success(self):
        service = RepoProviderService(
            label_store=FakeLabelStore(),
            user_store=FakeUserStore(),
            encryption=FakeEncryption(),
            git_fetcher=FakeRepoFetcher(),
        )

        user_claims = UserClaims(sub="user123")
        pagination = RequiredPaginationParams(limit=20, offset=0)

        total, repos = await service.get_all_provider_repos("token123", user_claims, pagination)

        assert total == 1
        assert len(repos) == 1
        assert repos[0].repo_name == "test_repo"

    @pytest.mark.asyncio
    async def test_get_all_provider_repos_user_not_found(self):
        service = RepoProviderService(
            label_store=FakeLabelStore(),
            user_store=FakeNoneUserStore(),
            encryption=FakeEncryption(),
            git_fetcher=FakeRepoFetcher(),
        )

        with pytest.raises(ResourceNotFound, match="User not found"):
            await service.get_all_provider_repos("token123", UserClaims(sub="no-user"), RequiredPaginationParams(limit=20, offset=0))

    @pytest.mark.asyncio
    async def test_get_all_provider_repos_label_not_found(self):
        service = RepoProviderService(
            label_store=FakeNoneLabelStore(),
            user_store=FakeUserStore(),
            encryption=FakeEncryption(),
            git_fetcher=FakeRepoFetcher(),
        )

        with pytest.raises(ResourceNotFound, match="Token not found"):
            await service.get_all_provider_repos("token123", UserClaims(sub="user123"), RequiredPaginationParams(limit=20, offset=0))
            
    @pytest.mark.asyncio
    async def test_get_all_provider_repos_invalid_git_hosting(self):
        service = RepoProviderService(
            label_store=FakeLabelStoreWithUnknownHosting(),
            user_store=FakeUserStore(),
            encryption=FakeEncryption(),
            git_fetcher=FakeRepoFetcher(),
        )

        with pytest.raises(BadRequest, match="Unsupported Git hosting"):
            await service.get_all_provider_repos("token123", UserClaims(sub="user123"), RequiredPaginationParams(limit=20, offset=0))

