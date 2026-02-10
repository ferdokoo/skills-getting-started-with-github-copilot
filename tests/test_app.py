"""Tests for the Mergington High School Activities API"""

import sys
from pathlib import Path

# Add src to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient
from app import app, activities

client = TestClient(app)


class TestGetActivities:
    """Test the GET /activities endpoint"""

    def test_get_all_activities(self):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        # Check that required keys are present in each activity
        for activity_name, activity_info in data.items():
            assert "description" in activity_info
            assert "schedule" in activity_info
            assert "max_participants" in activity_info
            assert "participants" in activity_info
            assert isinstance(activity_info["participants"], list)


class TestActivitySignup:
    """Test the activity signup functionality"""

    def setup_method(self):
        """Reset activities before each test"""
        # Store original state
        self.original_activities = {k: v.copy() for k, v in activities.items()}
        # Clear participants
        for activity in activities.values():
            activity["participants"] = []

    def teardown_method(self):
        """Restore original state after each test"""
        for activity_name, activity_data in self.original_activities.items():
            if activity_name in activities:
                activities[activity_name]["participants"] = activity_data["participants"].copy()

    def test_signup_for_activity(self):
        """Test signing up for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=test@example.com"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@example.com" in activities["Chess Club"]["participants"]

    def test_signup_duplicate_email(self):
        """Test that duplicate signup is rejected"""
        email = "duplicate@example.com"
        # First signup should succeed
        response1 = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response1.status_code == 200

        # Second signup with same email should fail
        response2 = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "already" in data["detail"].lower() or "duplicate" in data["detail"].lower()

    def test_signup_nonexistent_activity(self):
        """Test signing up for a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@example.com"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_signup_multiple_students(self):
        """Test multiple students signing up for the same activity"""
        emails = ["student1@example.com", "student2@example.com", "student3@example.com"]
        for email in emails:
            response = client.post(
                f"/activities/Programming%20Class/signup?email={email}"
            )
            assert response.status_code == 200

        # Verify all students are signed up
        activity_emails = activities["Programming Class"]["participants"]
        for email in emails:
            assert email in activity_emails


class TestActivityUnregister:
    """Test the activity unregister functionality"""

    def setup_method(self):
        """Setup test data before each test"""
        self.original_activities = {k: v.copy() for k, v in activities.items()}
        # Clear and add test participants
        for activity in activities.values():
            activity["participants"] = []
        activities["Chess Club"]["participants"] = ["alice@example.com", "bob@example.com", "charlie@example.com"]

    def teardown_method(self):
        """Restore original state after each test"""
        for activity_name, activity_data in self.original_activities.items():
            if activity_name in activities:
                activities[activity_name]["participants"] = activity_data["participants"].copy()

    def test_unregister_participant(self):
        """Test unregistering a participant from an activity"""
        email = "alice@example.com"
        assert email in activities["Chess Club"]["participants"]

        response = client.delete(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert email not in activities["Chess Club"]["participants"]

    def test_unregister_nonexistent_activity(self):
        """Test unregistering from a non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent%20Activity/signup?email=test@example.com"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_unregister_student_not_signed_up(self):
        """Test unregistering a student who is not signed up"""
        response = client.delete(
            "/activities/Chess%20Club/signup?email=notregistered@example.com"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"].lower()

    def test_unregister_all_participants(self):
        """Test unregistering all participants"""
        emails = ["alice@example.com", "bob@example.com", "charlie@example.com"]
        for email in emails:
            response = client.delete(
                f"/activities/Chess%20Club/signup?email={email}"
            )
            assert response.status_code == 200

        # Verify all are removed
        assert len(activities["Chess Club"]["participants"]) == 0


class TestIntegration:
    """Integration tests for the full workflow"""

    def setup_method(self):
        """Setup test data"""
        self.original_activities = {k: v.copy() for k, v in activities.items()}
        for activity in activities.values():
            activity["participants"] = []

    def teardown_method(self):
        """Restore original state"""
        for activity_name, activity_data in self.original_activities.items():
            if activity_name in activities:
                activities[activity_name]["participants"] = activity_data["participants"].copy()

    def test_signup_and_unregister_workflow(self):
        """Test complete signup and unregister workflow"""
        email = "workflow@example.com"
        activity = "Drama%20Club"

        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        assert email in activities["Drama Club"]["participants"]

        # Get activities and verify participant is listed
        activities_response = client.get("/activities")
        assert activities_response.status_code == 200
        assert email in activities_response.json()["Drama Club"]["participants"]

        # Unregister
        unregister_response = client.delete(f"/activities/{activity}/signup?email={email}")
        assert unregister_response.status_code == 200
        assert email not in activities["Drama Club"]["participants"]

        # Verify participant is gone
        final_response = client.get("/activities")
        assert email not in final_response.json()["Drama Club"]["participants"]
