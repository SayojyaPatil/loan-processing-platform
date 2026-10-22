from locust import HttpUser, task, between
import random

class LoanApiUser(HttpUser):
    wait_time=between(0.05, 0.25)
    @task(5)
    def list_loans(self):
        self.client.get('/api/loans/?page=1', name='GET /api/loans/')
    @task(3)
    def create_loan(self):
        i=random.randint(1,10_000_000)
        self.client.post('/api/loans/', json={
            'applicant_name':f'Load User {i}', 'applicant_email':f'load{i}@example.test',
            'requested_amount':'45000.00','purpose':'debt_consolidation'
        }, name='POST /api/loans/')
    @task(2)
    def list_jobs(self):
        self.client.get('/api/processing-jobs/?page=1', name='GET /api/processing-jobs/')
