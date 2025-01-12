import uuid
from django.utils import timezone
from django.db import models


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_joined = models.DateTimeField(auto_now_add=True)
    google_pfpURL = models.URLField(max_length=200, blank=True, null=True)
    is_pma = models.BooleanField(default=False)
    nickname = models.CharField(max_length=50, blank=True, null=True)
    phone_number = models.CharField(max_length=10, blank=True, null=True,default="Not set.")
    bio = models.TextField(blank=True, null=True, default="No bio provided.")
    location = models.CharField(max_length=50, blank=True, null=True, default="Charlottesville, VA")

    def change_nickname(self, new_nickname):
        """Changes the User's nickname"""
        self.nickname = new_nickname

    def change_phone_number(self, new_phone_number):
        """Changes the User's phone number"""
        self.phone_number = new_phone_number

    def change_bio(self, new_bio):
        """Changes the User's bio"""
        self.bio = new_bio

    def change_location(self, new_location):
        """Changes the User's location"""
        self.location = new_location


    def date(self):
        local_time = timezone.localtime(self.date_joined)
        return local_time.strftime("%m/%d/%Y")

    def get_full_name(self):
        """Returns the User's full name"""
        if self.nickname and self.nickname != 'Not set.':
            return f"{self.first_name} '{self.nickname}' {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def get_teams(self):
        """Returns a list of all the User's teams"""
        return self.teams.all()

    def get_owned_teams(self):
        """Returns a list of all the teams this User owns"""
        return self.owned_teams.all()

    def leave_team(self, team):
        """Removes a given team from the User's list of teams, and removes self from the given Team's list of members"""
        self.teams.remove(team)
        team.remove_member(self)

    def delete_team(self, team):
        """Deletes a team from the database if and only if self is the owner of the specified team"""
        if self.owned_teams.contains(team):
            Team.objects.filter(team=team).delete()

    def is_pma_administrator(self):
        """Returns True if the User is a PMA administrator, False otherwise"""
        return self.is_pma

    def get_email(self):
        """Returns the User's email"""
        return self.email
    
    def get_pfpURL(self):
        """Returns the User's profile picture URL"""
        return self.google_pfpURL
    
    def add_pfpURL(self, pfpURL):
        """Sets the User's profile picture URL"""
        self.google_pfpURL = pfpURL

    def get_join_date(self):
        """Returns the User's join date"""
        return self.date_joined

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# Represents a singular "practice". Occurs on a specific day of the week from a specific start to end time.
class PracticeSession(models.Model):
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def military_start_time(self):
        return self.start_time.strftime("%H:%M")
    
    def military_end_time(self):
        return self.end_time.strftime("%H:%M")

    def __str__(self):
        return f"Practice on {self.day_of_week}: {self.start_time} - {self.end_time}"


# Represents a Team's complete practice schedule, potentially consisting of many PracticeSessions
class PracticeSchedule(models.Model):
    sessions = models.ManyToManyField(PracticeSession)

    def get_sessions(self):
        return self.sessions.all()

    def deleted_team(self):
        """deletes all sessions in the schedule and the schedule itself"""
        for session in self.sessions.all():
            session.delete()
        
        self.delete()

    def delete_all_sessions(self):
        """deletes all sessions in the schedule"""
        for session in self.sessions.all():
            session.delete()

    def __str__(self):
        return f"Schedule with {self.sessions.count()} practice session(s)"





class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    associated_sport = models.CharField(max_length=100)
    members = models.ManyToManyField(User, related_name='teams')
    prospective_members = models.ManyToManyField(User, related_name='team_applications')
    practice_schedule = models.OneToOneField(PracticeSchedule, on_delete=models.CASCADE, null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_teams')

    def get_members(self):
        """Returns a list of all the Team's members"""
        return self.members.all()
    
    def get_prospective_members(self):
        """Returns a list of all the Team's prospective members"""
        return self.prospective_members.all()
    
    def add_prospective_member(self, user):
        """Adds a User to the Team's list of prospective members"""
        self.prospective_members.add(user)

    def add_member(self, user):
        """Adds a User to the Team's list of members"""
        self.members.add(user)

    def transfer_ownership(self, new_owner):
        """Transfers ownership of the Team to a new User"""
        self.owner = new_owner

    def remove_member(self, user):
        """Removes a User from the Team's list of members"""
        self.members.remove(user)

    def get_practice_days(self):
        """Returns a list of all the days the Team practices"""
        schedule = self.practice_schedule
        practices = schedule.get_sessions()
        ret = ""
        for practice in practices:
            if practice.day_of_week not in ret:
                ret+=practice.day_of_week + ", "
        return ret[:-2]

    def send_message(self, message, sender):
        """Send a message to the current team"""
        message = Message(author=sender, team=self, message_body=message)
        message.save()

    def get_messages(self, load_all=False):
        """Return messages for the current team. Optionally return all messages."""
        if load_all:
            return Message.objects.filter(team=self).order_by('timestamp')  # Order by timestamp for all messages
        else:
            messages = Message.objects.filter(team=self).order_by('-timestamp')[:10]
            return messages[::-1]  # Return the most recent 10 in chronological order

    def get_message_count(self):
        """Return the number of messages for the current team"""
        return len(Message.objects.filter(team=self))
    
    def clear_messages(self):
        """Clear all messages for the current team"""
        Message.objects.filter(team=self).delete()

    def delete_team(self):
        """Deletes a team from the database if and only if self is the owner of the team"""
        self.practice_schedule.deleted_team()
        self.delete()

    def get_owner(self):
        """Returns the User who owns the Team"""
        return self.owner

    def accept_member(self, member):
        """Accepts a prospective member into the team"""
        self.prospective_members.remove(member)
        self.members.add(member)

    def deny_member(self, member):
        """Denies a prospective member from joining the team"""
        self.prospective_members.remove(member)

    def __str__(self):
        return f"{self.name} — {self.description}"
    
class Message(models.Model):
    author = models.ForeignKey(User, related_name='from_user', on_delete=models.CASCADE)
    team = models.ForeignKey(Team, related_name='team', on_delete=models.CASCADE, default="aassdsdafdafasa")
    message_body = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def content(self):
        return self.message_body
    
    def date(self):
        local_time = timezone.localtime(self.timestamp)
        return local_time.strftime("%m/%d, %I:%M %p")
    
    def __str__(self):
        return self.message_body
        