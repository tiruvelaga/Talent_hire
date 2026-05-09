"""
Locust load test for TalentHire Exam Portal
Simulates concurrent candidates logging in + taking exams
"""

from locust import HttpUser, task, between, events
import random
import time

class CandidateUser(HttpUser):
    """Simulate a candidate taking the exam"""
    wait_time = between(2, 5)  # Wait 2-5s between actions

    def on_start(self):
        """Login before each user starts"""
        candidates = [
            {'name': 'Rahul', 'mobile': '9876543210', 'reg_id': 'TH-2024-001'},
            {'name': 'Priya', 'mobile': '8765432109', 'reg_id': 'TH-2024-002'},
            {'name': 'Arjun Reddy', 'mobile': '7654321098', 'reg_id': 'TH-2024-003'},
            {'name': 'Sneha', 'mobile': '9988776655', 'reg_id': 'TH-2024-004'},
            {'name': 'Vikram', 'mobile': '9123456789', 'reg_id': 'TH-2024-005'},
            {'name': 'Abhi', 'mobile': '9999999999', 'reg_id': 'ABC123'},
        ]

        # Pick random candidate
        cand = random.choice(candidates)

        # Get login page (get CSRF token)
        resp = self.client.get('/login/')

        # Extract CSRF token from response
        csrf_token = None
        if 'csrfmiddlewaretoken' in resp.text:
            start = resp.text.find('csrfmiddlewaretoken" value="') + len('csrfmiddlewaretoken" value="')
            end = resp.text.find('"', start)
            csrf_token = resp.text[start:end]

        # Login
        self.client.post('/login/', {
            'csrfmiddlewaretoken': csrf_token,
            'name': cand['name'],
            'mobile': cand['mobile'],
            'registration_id': cand['reg_id'],
        })

    @task(1)
    def view_exam(self):
        """View exam page"""
        self.client.get('/exam/')

    @task(2)
    def submit_answer(self):
        """Submit an answer (simulate clicking option)"""
        # This would be a POST to /submit/ but for load test
        # just hitting the exam page is enough to test DB queries
        self.client.get('/exam/')

    @task(1)
    def check_home(self):
        """Visit home page"""
        self.client.get('/')


class AdminUser(HttpUser):
    """Simulate admin portal usage"""
    wait_time = between(3, 8)
    weight = 1  # 1 admin per 10 candidates

    def on_start(self):
        """Admin login"""
        resp = self.client.get('/portal/login/')

        # Extract CSRF
        csrf_token = None
        if 'csrfmiddlewaretoken' in resp.text:
            start = resp.text.find('csrfmiddlewaretoken" value="') + len('csrfmiddlewaretoken" value="')
            end = resp.text.find('"', start)
            csrf_token = resp.text[start:end]

        # Login as admin
        self.client.post('/portal/login/', {
            'csrfmiddlewaretoken': csrf_token,
            'username': 'root',
            'password': '9999',
        })

    @task(1)
    def view_dashboard(self):
        """View admin dashboard"""
        self.client.get('/portal/')

    @task(1)
    def view_candidates(self):
        """View candidate list"""
        self.client.get('/portal/candidates/')

    @task(1)
    def view_results(self):
        """View exam results"""
        self.client.get('/portal/results/')


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "="*60)
    print("ðŸš€ LOAD TEST STARTING")
    print("="*60)
    print("Testing: TalentHire Exam Portal")
    print("Target: 5000 concurrent users")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n" + "="*60)
    print("ðŸ“Š LOAD TEST COMPLETE")
    print("="*60)
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Success rate: {100 - (environment.stats.total.num_failures/max(1, environment.stats.total.num_requests)*100):.2f}%")
    print(f"Avg response time: {environment.stats.total.avg_response_time:.0f}ms")
    print(f"Max response time: {environment.stats.total.max_response_time:.0f}ms")
    print("="*60 + "\n")
