class RateLimiter:
    def __init__(self, limit=100):
        self.limit = limit
        self.requests = {}

    def allow(self, key):
        count = self.requests.get(key, 0) + 1
        self.requests[key] = count
        return count <= self.limit
