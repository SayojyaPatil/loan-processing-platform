"""Auth and ownership regression tests. Run with pytest against isolated test Postgres."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.loans.models import LoanApplication
from apps.documents.models import LoanDocument

@pytest.fixture
def users(db):
    User = get_user_model()
    return (User.objects.create_user(username='applicant_a', password='test-password-a'),
            User.objects.create_user(username='applicant_b', password='test-password-b'),
            User.objects.create_user(username='reviewer', password='test-password-c', is_staff=True))

@pytest.fixture
def loan(db, users):
    return LoanApplication.objects.create(owner=users[0], applicant_name='A', applicant_email='a@example.test', requested_amount='5000.00', purpose='Equipment')

@pytest.mark.django_db
def test_anonymous_loan_list_is_rejected():
    assert APIClient().get('/api/loans/').status_code in (401, 403)

@pytest.mark.django_db
def test_users_cannot_list_or_fetch_other_users_loans(users, loan):
    client = APIClient()
    client.force_authenticate(user=users[1])
    r = client.get('/api/loans/')
    assert r.status_code == 200 and r.data['count'] == 0
    assert client.get(f'/api/loans/{loan.pk}/').status_code == 404
    assert client.post(f'/api/loans/{loan.pk}/submit/').status_code == 404

@pytest.mark.django_db
def test_owner_assigned_server_side(users):
    client = APIClient(); client.force_authenticate(user=users[0])
    response = client.post('/api/loans/', {'applicant_name':'A','applicant_email':'a@example.test', 'requested_amount':'1500.00','purpose':'Car'}, format='json')
    assert response.status_code == 201
    assert LoanApplication.objects.get(pk=response.data['id']).owner_id == users[0].pk

@pytest.mark.django_db
def test_staff_can_view_legacy_loan(users):
    legacy = LoanApplication.objects.create(applicant_name='Legacy', applicant_email='legacy@example.test', requested_amount='1000', purpose='Legacy')
    client = APIClient(); client.force_authenticate(user=users[2])
    assert client.get(f'/api/loans/{legacy.pk}/').status_code == 200

@pytest.mark.django_db
def test_document_cannot_link_to_someone_elses_loan(users, loan):
    client = APIClient(); client.force_authenticate(user=users[1])
    response = client.post('/api/documents/', {'loan':str(loan.pk), 'kind':'other', 'filename':'note.txt', 'text_content':'Sample'}, format='json')
    assert response.status_code == 400
    assert LoanDocument.objects.count() == 0

@pytest.mark.django_db
def test_document_size_and_extension_validation(users, loan):
    client = APIClient(); client.force_authenticate(user=users[0])
    base = {'loan': str(loan.pk), 'kind':'other'}
    assert client.post('/api/documents/', {**base, 'filename':'bad.exe', 'text_content':'sample'}, format='json').status_code == 400
    assert client.post('/api/documents/', {**base, 'filename':'good.txt', 'text_content':'x' * (1024 * 1024 + 1)}, format='json').status_code == 400

@pytest.mark.django_db
def test_repeated_submit_is_rejected(users, loan, monkeypatch):
    client=APIClient(); client.force_authenticate(user=users[0])
    LoanDocument.objects.create(loan=loan, kind='other', filename='sample.txt', text_content='sample')
    class Result:
        id='fake-task-id'
    monkeypatch.setattr('apps.loans.views.process_loan.delay', lambda *_: Result())
    first = client.post(f'/api/loans/{loan.pk}/submit/')
    assert first.status_code == 202
    assert client.post(f'/api/loans/{loan.pk}/submit/').status_code == 400
    assert loan.processing_jobs.count() == 1
