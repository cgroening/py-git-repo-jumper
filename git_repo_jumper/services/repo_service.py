class GitRepoService:
    _storage = None


    def __init__(self, storage):
        self._storage = storage
