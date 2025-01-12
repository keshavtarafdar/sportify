from django.test import TestCase
from sportify.models import User, Team, PracticeSession, PracticeSchedule, Message
from django.utils import timezone
import time

class UserTestCase(TestCase):

    def setUp(self):
        self.user1 = User.objects.create(first_name="John", last_name="Doe", email="john.doe@example.com")
        self.user2 = User.objects.create(first_name="Jane", last_name="Doe", email="jane.doe@example.com")
        self.team = Team.objects.create(name="Virginia Rowing Association", description="Men's Rowing at the University of Virginia", owner=self.user1)

    def test_user_creation(self):
        """Test that User creation works as expected"""
        self.assertEqual(self.user1.get_full_name(), "John Doe")
        self.assertEqual(self.user2.get_full_name(), "Jane Doe")
        self.assertEqual(str(self.user1), "John Doe")

    def test_leave_team(self):
        """Test that a user can leave a team"""
        self.team.add_member(self.user1)
        self.user1.leave_team(self.team)
        self.assertNotIn(self.team, self.user1.get_teams())


class PracticeSessionModelTest(TestCase):

    def setUp(self):
        self.session = PracticeSession.objects.create(day_of_week='Monday', start_time="06:00", end_time="08:00")

    def test_practice_session_creation(self):
        """Test that PracticeSession creation works"""
        self.assertEqual(self.session.day_of_week, 'Monday')
        self.assertEqual(str(self.session), f"Practice on {self.session.day_of_week}: {self.session.start_time} - {self.session.end_time}")


class PracticeScheduleModelTest(TestCase):

    def setUp(self):
        self.schedule = PracticeSchedule.objects.create()
        self.session1 = PracticeSession.objects.create(day_of_week='Monday', start_time="06:00", end_time="08:00")
        self.session2 = PracticeSession.objects.create(day_of_week='Wednesday', start_time="09:00", end_time="11:00")

    def test_add_sessions_to_schedule(self):
        """Test adding sessions to the schedule"""
        self.schedule.sessions.add(self.session1, self.session2)

        self.assertEqual(self.schedule.get_sessions().count(), 2)
        self.assertIn(self.session1, self.schedule.get_sessions())
        self.assertIn(self.session2, self.schedule.get_sessions())

    def test_schedule_str(self):
        """Test the string representation of the schedule"""
        self.schedule.sessions.add(self.session1)
        self.assertEqual(str(self.schedule), "Schedule with 1 practice session(s)")


class TeamModelTest(TestCase):

    def setUp(self):
        # Create some Users
        self.user1 = User.objects.create(first_name="John", last_name="Doe", email="john.doe@example.com")
        self.user2 = User.objects.create(first_name="Jane", last_name="Doe", email="jane.doe@example.com")
        # Create a Team
        self.team = Team.objects.create(name="Virginia Rowing Association", description="Men's Rowing at the University of Virginia", owner=self.user1)
        
        # Create a PracticeSession and PracticeSchedule
        self.schedule = PracticeSchedule.objects.create()
        self.session1 = PracticeSession.objects.create(day_of_week='Tuesday', start_time="06:00", end_time="08:00")
        self.session2 = PracticeSession.objects.create(day_of_week='Thursday', start_time="09:00", end_time="11:00")

    def test_team_creation(self):
        """Test that Team creation works as expected"""
        self.assertEqual(self.team.name, "Virginia Rowing Association")
        self.assertEqual(str(self.team), "Virginia Rowing Association — Men's Rowing at the University of Virginia")

    def test_add_and_remove_team_members(self):
        """Test adding and removing users from a team"""
        self.team.add_member(self.user1)
        self.team.add_member(self.user2)

        # Check that members are added
        self.assertIn(self.user1, self.team.get_members())
        self.assertIn(self.user2, self.team.get_members())

        # Remove a member and check
        self.team.remove_member(self.user2)
        self.assertNotIn(self.user2, self.team.get_members())

    def test_team_practice_schedule(self):
        """Test assigning a practice schedule to a team"""
        self.schedule.sessions.add(self.session1, self.session2)
        self.team.practice_schedule = self.schedule
        self.team.save()

        self.assertEqual(self.team.practice_schedule.get_sessions().count(), 2)
        self.assertIn(self.session1, self.team.practice_schedule.get_sessions())

    def test_delete_team(self):
        """Test that a team can be deleted successfully"""
        self.team.add_member(self.user1)
        self.schedule.sessions.add(self.session1, self.session2)
        self.team.practice_schedule = self.schedule
        self.team.save()
        practiceScheduleID = self.team.practice_schedule.id


        self.assertEqual(Team.objects.filter(id=self.team.id).exists(), True)
        #self.assertEqual(self.team.get_members().count(), 1)
        self.assertEqual(self.team.practice_schedule.get_sessions().count(), 2)
        
        # Delete the team
        self.team.delete_team()

        # Verify the team no longer exists
        self.assertEqual(Team.objects.filter(id=self.team.id).exists(), False)

        # Check that the team is removed from the user's teams
        self.assertNotIn(self.team, self.user1.get_teams())
        
        # Optionally, check that the practice schedule is also deleted if it’s meant to be cascaded
        self.assertEqual(PracticeSchedule.objects.filter(id=practiceScheduleID).exists(), False)



class MessageModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create(first_name="Alice", last_name="Smith", email="alice.smith@example.com")
        self.team = Team.objects.create(name="Mountain Climbers", description="Adventure Club", owner=self.user)
        self.message = Message.objects.create(author=self.user, team=self.team, message_body="Welcome to the team!")

    def test_message_creation(self):
        """Test that Message creation works as expected"""
        self.assertEqual(self.message.content(), "Welcome to the team!")
        self.assertEqual(str(self.message), "Welcome to the team!")
        self.assertEqual(self.message.author, self.user)
        self.assertEqual(self.message.team, self.team)

    def test_message_timestamp_format(self):
        """Test that Message timestamp formatting works"""
        local_time = timezone.localtime(self.message.timestamp)
        expected_format = local_time.strftime("%m/%d, %I:%M %p")
        self.assertEqual(self.message.date(), expected_format)


class TeamProspectiveMembersTest(TestCase):

    def setUp(self):
        self.user1 = User.objects.create(first_name="John", last_name="Doe", email="john.doe@example.com")
        self.user2 = User.objects.create(first_name="Jane", last_name="Doe", email="jane.doe@example.com")
        self.team = Team.objects.create(name="Adventure Seekers", description="A group for outdoor enthusiasts", owner=self.user1)

    def test_add_prospective_member(self):
        """Test adding a prospective member to the team"""
        self.team.add_prospective_member(self.user2)
        self.assertIn(self.user2, self.team.get_prospective_members())

    def test_accept_member(self):
        """Test accepting a prospective member into the team"""
        self.team.add_prospective_member(self.user2)
        self.team.accept_member(self.user2)
        self.assertNotIn(self.user2, self.team.get_prospective_members())
        self.assertIn(self.user2, self.team.get_members())

    def test_deny_member(self):
        """Test denying a prospective member from the team"""
        self.team.add_prospective_member(self.user2)
        self.team.deny_member(self.user2)
        self.assertNotIn(self.user2, self.team.get_prospective_members())
        self.assertNotIn(self.user2, self.team.get_members())


class TeamMessagingTest(TestCase):

    def setUp(self):
        self.user = User.objects.create(first_name="Sam", last_name="Parker", email="sam.parker@example.com")
        self.team = Team.objects.create(name="Cycling Club", description="Community cycling events", owner=self.user)

    def test_send_message(self):
        """Test sending a message to the team"""
        self.team.send_message("Hello Cyclists!", sender=self.user)
        messages = self.team.get_messages(load_all=True)
        self.assertEqual(messages.count(), 1)
        self.assertEqual(messages.first().message_body, "Hello Cyclists!")

    def test_get_recent_messages(self):
        """Test getting the most recent 10 messages"""
        # Send 12 messages
        for i in range(12):
            self.team.send_message(f"Message {i+1}", sender=self.user)
            time.sleep(1)
        
        recent_messages = self.team.get_messages()
        
        self.assertEqual(len(recent_messages), 10)
        self.assertEqual(recent_messages[0].message_body, "Message 3")  # Most recent 10 in chronological order
        self.assertEqual(recent_messages[-1].message_body, "Message 12")

    def test_clear_messages(self):
        """Test clearing all messages from the team"""
        self.team.send_message("Message to be cleared", sender=self.user)
        self.team.clear_messages()
        self.assertEqual(self.team.get_message_count(), 0)


class ExtendedUserTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            first_name="Test",
            last_name="User",
            email="test.user@example.com",
            nickname="Tester",
            phone_number="1234567890",
            bio="Hello, I am a test user.",
        )

    def test_change_details(self):
        """Test changing user details."""
        self.user.change_nickname("UpdatedNickname")
        self.user.change_phone_number("0987654321")
        self.user.change_bio("Updated bio.")
        self.user.change_location("New Location")

        self.assertEqual(self.user.nickname, "UpdatedNickname")
        self.assertEqual(self.user.phone_number, "0987654321")
        self.assertEqual(self.user.bio, "Updated bio.")
        self.assertEqual(self.user.location, "New Location")

    def test_get_email_and_pfp(self):
        """Test email and profile picture URL methods."""
        self.assertEqual(self.user.get_email(), "test.user@example.com")
        self.user.add_pfpURL("http://example.com/image.jpg")
        self.assertEqual(self.user.get_pfpURL(), "http://example.com/image.jpg")

    def test_get_full_name_with_nickname(self):
        """Test full name method with nickname."""
        self.assertEqual(self.user.get_full_name(), "Test 'Tester' User")
        self.user.change_nickname("Not set.")
        self.assertEqual(self.user.get_full_name(), "Test User")




