from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now


class Organization(models.Model):
    website_url = models.URLField(max_length=255, blank=True, null=True)  # Added website_url field
    organization_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField(max_length=255)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
    facilitated = models.PositiveIntegerField()
    people_helped = models.PositiveIntegerField()
    opportunities_created = models.PositiveIntegerField()
    opportunities_completed = models.PositiveIntegerField()
    accepted = models.PositiveIntegerField()
    declined = models.PositiveIntegerField()
    goals = models.PositiveIntegerField()
    badge = models.CharField(max_length=255, blank=True, null=True)
    next_badge = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.organization_name

class PendingOrganization(models.Model):
    organization_name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=50)  # e.g., EIN
    address = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField(max_length=255)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
    password = models.CharField(max_length=128)  # Store raw password temporarily
    document = models.FileField(upload_to='org_documents/', blank=True, null=True)
    verification_code = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.organization_name


class Student(models.Model):
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    school = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)  # Short bio or description
    interests = models.TextField(blank=True, null=True)  # Areas of interest or hobbies
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)  # Profile picture
    hours_volunteered = models.PositiveIntegerField()
    people_helped = models.PositiveIntegerField()
    opportunities_completed = models.PositiveIntegerField()
    goal_hours = models.PositiveIntegerField()
    accept = models.PositiveIntegerField()
    decline = models.PositiveIntegerField()
    applied = models.PositiveIntegerField()
    badge = models.CharField(max_length=255, blank=True, null=True)
    next_badge = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"



class VolunteerOpportunities(models.Model):
    CATEGORY_CHOICES = [
        ('Community & Social Services', 'Community & Social Services'),
        ('Education & Literacy', 'Education & Literacy'),
        ('Health & Wellness', 'Health & Wellness'),
        ('Environmental & Conservation', 'Environmental & Conservation'),
        ('Animal Welfare', 'Animal Welfare'),
        ('Arts, Culture & Heritage', 'Arts, Culture & Heritage'),
        ('International & Global Causes', 'International & Global Causes'),
        ('Sports & Recreation', 'Sports & Recreation'),
        ('Human Rights & Advocacy', 'Human Rights & Advocacy'),
        ('Emergency & Disaster Relief', 'Emergency & Disaster Relief'),
        ('Religious & Faith-Based', 'Religious & Faith-Based'),
        ('Technology & Innovation', 'Technology & Innovation'),
        ('Civic & Public Service', 'Civic & Public Service'),
        ('Business, Leadership & Professional Development', 'Business, Leadership & Professional Development'),
        ('Youth & Children Services', 'Youth & Children Services'),
        ('Senior Citizens Support', 'Senior Citizens Support'),
        ('Special Events & Fundraising', 'Special Events & Fundraising'),
        ('Skill-Based Volunteering', 'Skill-Based Volunteering'),
        ('Media & Communications', 'Media & Communications'),
        ('Military & Veterans Support', 'Military & Veterans Support'),
    ]
    
    title = models.CharField(max_length=100)
    description = models.TextField()
    address = models.CharField(max_length=255)
    time = models.DateTimeField()
    skills_required = models.CharField(max_length=255, blank=True, null=True)
    age_requirement = models.PositiveIntegerField(blank=True, null=True)
    hours_expected = models.CharField(max_length=50)  # You can save a range or single number here
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    posted_by = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="volunteer_opportunities")
    email = models.EmailField(max_length=255, null=True)


    def __str__(self):
        return self.title
    
class Contact(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    date_submitted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contact from {self.full_name} ({self.email})"

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.username} - {self.message[:20]}"

class SignupRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="signup_requests")
    opportunity = models.ForeignKey(VolunteerOpportunities, on_delete=models.CASCADE, related_name="signups")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="received_signups")
    timestamp = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Accepted", "Accepted"),
        ("Declined", "Declined"),
        ("Credited", "Credited"),  # New status
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    hours_volunteered = models.PositiveIntegerField(blank=True, null=True)
    people_helped = models.PositiveIntegerField(blank=True, null=True)
    completed = models.BooleanField(default=False)

    def is_complete(self):
        return self.completed and self.hours_volunteered and self.people_helped

    def __str__(self):
        return f"{self.user.username} -> {self.opportunity.title} ({self.status})"


    
class Completion(models.Model):
    signup = models.OneToOneField(SignupRequest, on_delete=models.CASCADE)
    hours_credited = models.PositiveIntegerField()
    people_credited = models.PositiveIntegerField()
    task_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Completion details for {self.signup.user.username}"
