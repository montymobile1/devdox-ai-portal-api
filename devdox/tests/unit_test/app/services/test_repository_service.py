import uuid
from types import SimpleNamespace
import pytest

from app.schemas.basic import RequiredPaginationParams
from app.utils.auth import UserClaims
from devdox_ai_git.schema.repo import NormalizedGitRepo
from models_src.dto.repo import GitHosting, RepoRequestDTO
from models_src.dto.git_label import GitLabelResponseDTO
from models_src.dto.user import UserResponseDTO
from models_src.exceptions.utils import RepoErrors
from app.exceptions.base_exceptions import DevDoxAPIException
from app.exceptions.local_exceptions import ResourceNotFound
from app.exceptions import exception_constants
from models_src.models.repo import StatusTypes
import app.services.repository as repo_mod


# -------------------------
# Test Doubles / Stubs
# -------------------------

class StubEncryption:
    def decrypt_for_user(self, encrypted, salt_b64):
        return "decrypted_token"

    def decrypt(self, encrypted_text: str):
        return "decrypt"


class StubTransformer:
    def __init__(self, name_seed="test"):
        self._name_seed = name_seed

    def from_git(self, data):
        # "data" can be any object; we just produce a stable NormalizedGitRepo
        return NormalizedGitRepo(
            id=str(uuid.uuid4()),
            repo_name=f"{self._name_seed}",
            description=None,
            html_url="url",
            default_branch="main",
            forks_count=1,
            stargazers_count=2,
            size=100,
            repo_created_at=None,
            private=True,
            visibility="private",
            relative_path="relative_url",
        )


class StubFetcher:
    """
    Minimal fetcher that cooperates with retrieve_git_fetcher_or_die()
    by exposing get_components(provider) -> (fetcher, transformer).
    Also implements the calls used by services.
    """
    def __init__(self, supported=(GitHosting.GITHUB.value, GitHosting.GITLAB.value), name_seed="test"):
        self.supported = set(supported)
        self.provider = None
        self._name_seed = name_seed
        self.fetch_user_repositories_calls = []
        self.fetch_single_repo_calls = []
        self.fetch_repo_user_calls = []

        # Defaults (override per-test if needed)
        self._user_repos_payload = {"data_count": 0, "data": []}
        self._single_repo_payload = (object(), ["Python"])

        # GitHub-like user object by default
        class _GHEmail:
            def __init__(self, email, primary, verified):
                self.email = email
                self.primary = primary
                self.verified = verified

        class _GHUser:
            login = "octocat"
            def get_emails(self):
                return [
                    _GHEmail("shadow@users.noreply.github.com", primary=False, verified=True),
                    _GHEmail("octo@github.com", primary=True, verified=True),
                ]

        self._repo_user_github = _GHUser()
        self._repo_user_gitlab = {"username": "labuser", "commit_email": "lab@users.noreply.gitlab.com"}

    def set_user_repos_payload(self, payload: dict):
        self._user_repos_payload = payload

    def set_single_repo_payload(self, repo_obj, langs):
        self._single_repo_payload = (repo_obj, langs)

    def get_components(self, provider):
        self.provider = provider
        if provider in self.supported:
            return self, StubTransformer(name_seed=self._name_seed)
        return None, None

    # Used by RepoProviderService
    def fetch_user_repositories(self, token, offset, limit):
        self.fetch_user_repositories_calls.append((token, offset, limit))
        return self._user_repos_payload

    # Used by RepoManipulationService.add_repo_from_provider (not directly tested here)
    def fetch_single_repo(self, token, relative_path):
        self.fetch_single_repo_calls.append((token, relative_path))
        return self._single_repo_payload

    def fetch_repo_user(self, token):
        self.fetch_repo_user_calls.append(token)
        if self.provider == GitHosting.GITHUB.value:
            return self._repo_user_github
        return self._repo_user_gitlab


class CapturingRepoStore:
    """Minimal repo store for analyze_repo and save calls."""
    def __init__(self):
        self.saved = []
        self.by_id_result = None
        self.by_id_exception = None
        self.updated = []
        self.count_by_user = 0
        self.find_all = []

    async def save(self, dto: RepoRequestDTO):
        self.saved.append(dto)
        return SimpleNamespace(id=uuid.uuid4())

    async def get_by_id(self, _id):
        if self.by_id_exception:
            raise self.by_id_exception
        return self.by_id_result

    async def update_analysis_metadata_by_id(self, **kwargs):
        self.updated.append(kwargs)
        return True

    async def count_by_user_id(self, user_id: str) -> int:
        return self.count_by_user

    async def find_all_by_user_id(self, user_id: str, offset: int, limit: int):
        return self.find_all


class StubUserStore:
    def __init__(self):
        self.result = None
        self.exc = None

    def set_output(self, val):
        self.result = val

    def set_exception(self, exc: Exception):
        self.exc = exc

    async def find_by_user_id(self, user_id: str):
        if self.exc:
            raise self.exc
        return self.result


class StubGitLabelStore:
    def __init__(self):
        self.by_id_user = None

    def set_output(self, val):
        self.by_id_user = val

    async def find_by_token_id_and_user(self, token_id: str, user_id: str):
        return self.by_id_user

    async def find_git_hostings_by_ids(self, token_ids):
        # For RepoQueryService tests you already wrote; not needed here
        return []


# -------------------------
# RepoProviderService.get_all_provider_repos
# -------------------------

class TestRepoProviderService_GetAllProviderRepos:

    @pytest.mark.asyncio
    async def test_user_not_found(self):
        user_store = StubUserStore()  # returns None
        label_store = StubGitLabelStore()
        fetcher = StubFetcher()
        service = repo_mod.RepoProviderService(
            git_label_repository=label_store,
            user_repository=user_store,
            encryption=StubEncryption(),
            git_fetcher=fetcher,
        )

        with pytest.raises(ResourceNotFound):
            await service.get_all_provider_repos(
                token_id="t1",
                user_claims=UserClaims(sub="u1"),
                pagination=RequiredPaginationParams(limit=10, offset=0),
            )

    @pytest.mark.asyncio
    async def test_label_not_found(self):
        user_store = StubUserStore()
        user_store.set_output(UserResponseDTO(encryption_salt="salt=="))

        label_store = StubGitLabelStore()  # returns None
        fetcher = StubFetcher()

        service = repo_mod.RepoProviderService(
            git_label_repository=label_store,
            user_repository=user_store,
            encryption=StubEncryption(),
            git_fetcher=fetcher,
        )

        with pytest.raises(ResourceNotFound):
            await service.get_all_provider_repos(
                token_id="missing",
                user_claims=UserClaims(sub="u1"),
                pagination=RequiredPaginationParams(limit=10, offset=0),
            )

    @pytest.mark.asyncio
    async def test_empty_fetch_returns_zero_and_empty_list(self):
        user_store = StubUserStore()
        user_store.set_output(UserResponseDTO(encryption_salt="salt=="))

        label_store = StubGitLabelStore()
        label_store.set_output(GitLabelResponseDTO(
            id=uuid.uuid4(), user_id="u1", label="L", git_hosting=GitHosting.GITHUB.value,
            username="u", token_value="enc", masked_token="***"
        ))

        fetcher = StubFetcher()
        fetcher.set_user_repos_payload({"data_count": 0, "data": []})

        service = repo_mod.RepoProviderService(
            git_label_repository=label_store,
            user_repository=user_store,
            encryption=StubEncryption(),
            git_fetcher=fetcher,
        )

        total, items = await service.get_all_provider_repos(
            token_id="t1",
            user_claims=UserClaims(sub="u1"),
            pagination=RequiredPaginationParams(limit=5, offset=0),
        )

        assert total == 0
        assert items == []
        assert fetcher.provider == GitHosting.GITHUB.value  # ensure correct provider flowed through

    @pytest.mark.asyncio
    async def test_happy_path_maps_results(self):
        user_store = StubUserStore()
        user_store.set_output(UserResponseDTO(encryption_salt="salt=="))

        label_store = StubGitLabelStore()
        label_store.set_output(GitLabelResponseDTO(
            id=uuid.uuid4(), user_id="u1", label="L", git_hosting=GitHosting.GITLAB.value,
            username="u", token_value="enc", masked_token="***"
        ))

        fetcher = StubFetcher(name_seed="mapped")
        fetcher.set_user_repos_payload({"data_count": 2, "data": [object(), object()]})

        service = repo_mod.RepoProviderService(
            git_label_repository=label_store,
            user_repository=user_store,
            encryption=StubEncryption(),
            git_fetcher=fetcher,
        )

        total, items = await service.get_all_provider_repos(
            token_id="t1",
            user_claims=UserClaims(sub="u1"),
            pagination=RequiredPaginationParams(limit=5, offset=0),
        )

        assert total == 2
        assert len(items) == 2
        assert all(hasattr(x, "repo_name") and x.repo_name == "mapped" for x in items)


# -------------------------
# Helper functions
# -------------------------

class TestHelpers:

    @pytest.mark.asyncio
    async def test_retrieve_user_by_id_or_die_ok(self):
        user_store = StubUserStore()
        user_store.set_output(UserResponseDTO(encryption_salt="salt=="))
        res = await repo_mod.retrieve_user_by_id_or_die(user_store, "u1")
        assert res.encryption_salt == "salt=="

    @pytest.mark.asyncio
    async def test_retrieve_user_by_id_or_die_not_found(self):
        user_store = StubUserStore()  # returns None
        with pytest.raises(ResourceNotFound):
            await repo_mod.retrieve_user_by_id_or_die(user_store, "u1")

    @pytest.mark.asyncio
    async def test_retrieve_git_label_or_die_ok(self):
        label_store = StubGitLabelStore()
        label_store.set_output(SimpleNamespace(id="t1", user_id="u1"))
        res = await repo_mod.retrieve_git_label_or_die(label_store, "t1", "u1")
        assert res.id == "t1"

    @pytest.mark.asyncio
    async def test_retrieve_git_label_or_die_not_found(self):
        label_store = StubGitLabelStore()  # returns None
        with pytest.raises(ResourceNotFound):
            await repo_mod.retrieve_git_label_or_die(label_store, "t1", "u1")

    @pytest.mark.asyncio
    async def test_retrieve_repo_by_id_translates_models_exception(self, monkeypatch):
        # Create a lightweight dummy that will be caught by the service module's except block
        class DummyDevDoxModelsException(Exception):
            def __init__(self, error_type):
                super().__init__("dummy")
                self.error_type = error_type

        # Swap the imported class inside the module so "except DevDoxModelsException" matches.
        monkeypatch.setattr(repo_mod, "DevDoxModelsException", DummyDevDoxModelsException, raising=True)

        repo_store = CapturingRepoStore()
        repo_store.by_id_exception = DummyDevDoxModelsException(
            RepoErrors.REPOSITORY_DOESNT_EXIST.value["error_type"]
        )

        with pytest.raises(DevDoxAPIException) as exc:
            await repo_mod.retrieve_repo_by_id_or_die(repo_store, "r1")

        # Optional: check it used the constants you expect
        assert exc.value.error_type == exception_constants.REPOSITORY_DOESNT_EXIST_TITLE

    @pytest.mark.asyncio
    async def test_retrieve_repo_by_id_none_raises_resource_not_found(self):
        repo_store = CapturingRepoStore()
        repo_store.by_id_result = None
        with pytest.raises(ResourceNotFound):
            await repo_mod.retrieve_repo_by_id_or_die(repo_store, "r1")

    @pytest.mark.asyncio
    async def test_retrieve_repo_by_id_ok(self):
        repo_store = CapturingRepoStore()
        repo_store.by_id_result = SimpleNamespace(id="db-id", token_id="tok", default_branch="main")
        res = await repo_mod.retrieve_repo_by_id_or_die(repo_store, "r1")
        assert res.id == "db-id"


# -------------------------
# RepoManipulationService.analyze_repo
# -------------------------

class TestRepoManipulationService_AnalyzeRepo:

    @pytest.mark.asyncio
    async def test_analyze_repo_happy_path(self, monkeypatch):
        # Arrange repo record
        repo_store = CapturingRepoStore()
        repo_store.by_id_result = SimpleNamespace(
            id="db-id",
            token_id="tok-1",
            default_branch="main",
            processing_end_time=None,
            total_files=None,
            total_chunks=None,
            total_embeddings=None,
            repo_id="provider-repo-id",
            status=""
        )

        # Git label / token info
        label_store = StubGitLabelStore()
        label_store.set_output(SimpleNamespace(
            id="tok-1", token_value="enc-token", git_hosting="github"
        ))

        # Capture enqueues
        calls = {"args": None}
        class StubQueue:
            async def enqueue(self, queue_name, payload, priority, job_type, user_id):
                calls["args"] = (queue_name, payload, priority, job_type, user_id)
                return True

        # Patch the module-level supabase_queue symbol used by the method
        monkeypatch.setattr(repo_mod, "supabase_queue", StubQueue(), raising=True)

        service = repo_mod.RepoManipulationService(
            git_label_repository=label_store,
            repo_repository=repo_store,
            user_repository=StubUserStore(),         # not used in analyze_repo
            encryption=StubEncryption(),             # not used in analyze_repo
            git_fetcher=StubFetcher(),               # not used in analyze_repo
        )

        await service.analyze_repo(UserClaims(sub="u1"), id="db-id")

        # Assert update happened
        assert repo_store.updated, "update_analysis_metadata_by_id should be called once"
        upd = repo_store.updated[-1]
        assert upd["id"] == "db-id"
        assert upd["status"] == StatusTypes.ANALYSIS_PENDING

        # Assert a job was enqueued with the expected shape
        assert calls["args"] is not None
        qname, payload, priority, job_type, user_id = calls["args"]
        assert qname == "processing"
        assert job_type == "analyze"
        assert user_id == "u1"
        assert payload["payload"]["git_provider"] == "github"
        assert payload["payload"]["token_value"] == "enc-token"
        assert payload["payload"]["repo_id"] == "provider-repo-id"

    @pytest.mark.asyncio
    async def test_analyze_repo_repo_missing_translates_models_exception(self, monkeypatch):
        class DummyDevDoxModelsException(Exception):
            def __init__(self, error_type):
                super().__init__("dummy")
                self.error_type = error_type

        monkeypatch.setattr(repo_mod, "DevDoxModelsException", DummyDevDoxModelsException, raising=True)

        repo_store = CapturingRepoStore()
        repo_store.by_id_exception = DummyDevDoxModelsException(
            RepoErrors.REPOSITORY_DOESNT_EXIST.value["error_type"]
        )

        service = repo_mod.RepoManipulationService(
            git_label_repository=StubGitLabelStore(),
            repo_repository=repo_store,
            user_repository=StubUserStore(),
            encryption=StubEncryption(),
            git_fetcher=StubFetcher(),
        )

        with pytest.raises(DevDoxAPIException):
            await service.analyze_repo(UserClaims(sub="u1"), id="does-not-exist")

    @pytest.mark.asyncio
    async def test_analyze_repo_token_missing_raises_resource_not_found(self, monkeypatch):
        # Valid repo, but token lookup returns None → ResourceNotFound via retrieve_git_label_or_die
        repo_store = CapturingRepoStore()
        repo_store.by_id_result = SimpleNamespace(
            id="db-id", token_id="tok-1",
            default_branch="main", processing_end_time=None,
            total_files=None, total_chunks=None, total_embeddings=None,
            repo_id="provider-repo-id", status=""
        )

        label_store = StubGitLabelStore()  # returns None

        service = repo_mod.RepoManipulationService(
            git_label_repository=label_store,
            repo_repository=repo_store,
            user_repository=StubUserStore(),
            encryption=StubEncryption(),
            git_fetcher=StubFetcher(),
        )

        with pytest.raises(ResourceNotFound):
            await service.analyze_repo(UserClaims(sub="u1"), id="db-id")
