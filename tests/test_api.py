"""
Tests for the Mergington High School API endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    # Clear all participants
    for activity in activities.values():
        activity["participants"] = []
    
    # Add back the default participants for specific activities
    activities["Chess Club"]["participants"] = ["michael@mergington.edu", "daniel@mergington.edu"]
    activities["Programming Class"]["participants"] = ["emma@mergington.edu", "sophia@mergington.edu"]
    activities["Gym Class"]["participants"] = ["john@mergington.edu", "olivia@mergington.edu"]
    
    yield


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Basketball Team" in data
        assert "Soccer Club" in data
        assert "Chess Club" in data
    
    def test_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        # Check a sample activity has all required fields
        basketball = data["Basketball Team"]
        assert "description" in basketball
        assert "schedule" in basketball
        assert "max_participants" in basketball
        assert "participants" in basketball
        assert isinstance(basketball["participants"], list)
    
    def test_default_participants(self, client):
        """Test that some activities have default participants"""
        response = client.get("/activities")
        data = response.json()
        
        assert len(data["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert len(data["Basketball Team"]["participants"]) == 0


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball Team/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Basketball Team"]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/Basketball Team/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/Basketball Team/signup?email={email}"
        )
        assert response2.status_code == 400
        
        data = response2.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        response = client.post(
            "/activities/Art%20Club/signup?email=artist@mergington.edu"
        )
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        email = "test@mergington.edu"
        
        # First signup
        client.post(f"/activities/Basketball Team/signup?email={email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/Basketball Team/unregister?email={email}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Basketball Team"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_not_registered(self, client):
        """Test unregister when student is not registered"""
        response = client.delete(
            "/activities/Basketball Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering a pre-existing participant"""
        # Chess Club has default participants
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]
        # Other participant should still be there
        assert "daniel@mergington.edu" in activities_data["Chess Club"]["participants"]


class TestEndToEndScenarios:
    """Integration tests for complete workflows"""
    
    def test_signup_and_unregister_workflow(self, client):
        """Test complete signup and unregister workflow"""
        email = "workflow@mergington.edu"
        activity = "Soccer Club"
        
        # Get initial state
        initial = client.get("/activities").json()
        initial_count = len(initial[activity]["participants"])
        
        # Signup
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify added
        after_signup = client.get("/activities").json()
        assert len(after_signup[activity]["participants"]) == initial_count + 1
        assert email in after_signup[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify removed
        after_unregister = client.get("/activities").json()
        assert len(after_unregister[activity]["participants"]) == initial_count
        assert email not in after_unregister[activity]["participants"]
    
    def test_multiple_students_same_activity(self, client):
        """Test multiple students signing up for the same activity"""
        activity = "Drama Club"
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        # Sign up all students
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all are registered
        activities_response = client.get("/activities")
        participants = activities_response.json()[activity]["participants"]
        for email in emails:
            assert email in participants
    
    def test_student_multiple_activities(self, client):
        """Test one student signing up for multiple activities"""
        email = "multitasker@mergington.edu"
        activities_list = ["Basketball Team", "Soccer Club", "Art Club"]
        
        # Sign up for multiple activities
        for activity in activities_list:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify student is in all activities
        all_activities = client.get("/activities").json()
        for activity in activities_list:
            assert email in all_activities[activity]["participants"]
