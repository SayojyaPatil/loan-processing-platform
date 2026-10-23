
import os
import random

from locust import HttpUser, task, between


class LoanApiUser(HttpUser):
    wait_time = between(0.05, 0.25)

    def on_start(self):
        username = os.environ.get("LOAD_TEST_USERNAME")
        password = os.environ.get("LOAD_TEST_PASSWORD")

        if not username or not password:
            raise RuntimeError(
                "Set LOAD_TEST_USERNAME and LOAD_TEST_PASSWORD"
            )

        self.client.auth = (username, password)

    @task(5)
    def list_loans(self):
        self.client.get(
            "/api/loans/?page=1",
            name="GET /api/loans/",
        )

    @task(3)
    def create_loan(self):
        number = random.randint(1, 10_000_000)

        self.client.post(
            "/api/loans/",
            json={
                "applicant_name": f"Load User {number}",
                "applicant_email": f"load{number}@example.test",
                "requested_amount": "45000.00",
                "purpose": "debt_consolidation",
            },
            name="POST /api/loans/",
        )

    @task(2)
    def list_jobs(self):
        self.client.get(
            "/api/processing-jobs/?page=1",
            name="GET /api/processing-jobs/",
        )
