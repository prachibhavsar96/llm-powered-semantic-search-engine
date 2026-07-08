import random

from locust import HttpUser, between, task

TEST_EMAIL = "locust-load-test@example.com"
TEST_PASSWORD = "locust-test-password"

SAMPLE_QUERIES = [
    "How can caching improve performance?",
    "What is dependency injection?",
    "Explain how authentication works",
    "How do I upload a document?",
    "What is semantic search?",
]


class SearchUser(HttpUser):
    """
    Simulates a logged-in user repeatedly searching documents.
    """

    wait_time = between(1, 3)

    def on_start(self):
        # Ignore failures here: the account may already exist from a
        # previous run or another simulated user creating it first.
        self.client.post(
            "/auth/signup",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )

        response = self.client.post(
            "/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        token = response.json()["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task
    def search(self):
        query = random.choice(SAMPLE_QUERIES)
        self.client.post("/search", json={"query": query, "top_k": 3})
