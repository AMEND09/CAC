from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.http import HttpResponse
from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from .models import Completion, Notification, Student, Organization, VolunteerOpportunities, Contact, SignupRequest, PendingOrganization
from django.utils import timezone
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from django.contrib.auth import logout
from django.core.mail import send_mail
from django.conf import settings
import random
import logging
from datetime import datetime, timedelta
import re
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)  # Add logging for debugging

class Constants:
    @property
    def randomnum(self):
        digits = list(range(10))
        random.shuffle(digits)
        random_number = int(''.join(map(str, digits[:6])))
        return random_number
constants = Constants()

def index(request):
    return render(request, 'website/index.html')

def register(request):
    if request.method == "POST":
        fname = request.POST.get('fname')
        lname = request.POST.get('lname')
        school = request.POST.get('school')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        verification_code = constants.randomnum

        if password == password2:
            if User.objects.filter(email=email).exists():
                messages.info(request, 'Email Already In Use!')
                return redirect('register')
            elif not email.lower().endswith("@stu.jefferson.kyschools.us"):
                messages.info(request, 'Must be a JCPS email address!')
                return redirect('register')
            else:
                # Save data in session
                request.session['verification_code'] = verification_code
                request.session['first_name'] = fname
                request.session['last_name'] = lname
                request.session['email'] = email
                request.session['school'] = school
                request.session['phone'] = phone
                request.session['password'] = password

                # Send email
                send_mail(
                    'Verification Code',
                    f"Hello, {fname}\nYour verification code is {verification_code}",
                    'servesyncinc@gmail.com',
                    [email],
                    fail_silently=False,
                )
                return redirect('code')
        else:
            messages.info(request, "Password Doesn't Match!")
            return redirect('register')
    return render(request, 'website/register.html')

def code(request):
    # Retrieve session data
    verification_code = request.session.get('verification_code')
    first_name = request.session.get('first_name')
    last_name = request.session.get('last_name')
    email = request.session.get('email')
    school = request.session.get('school')
    phone = request.session.get('phone')

    # If session data is missing, redirect to start
    if not (verification_code and first_name and last_name and email):
        messages.error(request, "Session expired. Please start again.")
        return redirect('index')

    if request.method == "POST":
        # Validate the code
        code = request.POST.get('code')

        if int(code) == verification_code:
            # Code is correct, create the User and Student objects
            user = User.objects.create_user(
                username=email,
                email=email,
                password=request.session.get('password'),
                first_name=first_name,
                last_name=last_name,
            )
            student = Student.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                school=school,
                phone=phone,
                hours_volunteered=0,
                people_helped=0,
                opportunities_completed=0,
                goal_hours=0,
                applied=0,
                accept=0,
                decline=0,
                badge="",
                next_badge="",
            )

            # Save the created objects
            user.save()
            student.save()

            # Clear session data and show success message
            request.session.flush()
            messages.success(request, "Verification Successful!")
            return redirect('student')
        else:
            # Code is incorrect, clear session and show error
            request.session.flush()
            messages.error(request, "Verification Failed! Please try again.")
            return redirect('index')

    return render(request, 'website/code.html')

def login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        
        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)
            # Redirect based on user type
            if Student.objects.filter(email=user.email).exists():
                print("worked")
                return redirect('student')
            elif Organization.objects.filter(contact_email=user.email).exists():
                return redirect('organization')
            else:
                messages.error(request, 'No student or organization profile found.')
                return redirect('login')
        else:
            messages.info(request, 'Credentials Invalid')
            return redirect('login')
    return render(request, 'website/login.html')

@login_required
def setting(request):
    if not Student.objects.filter(email=request.user.email).exists():
        
        return redirect('unauthorized')

    try:
        student = Student.objects.get(email=request.user.email)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('index')

    if request.method == 'POST':
        student.first_name = request.POST.get('first_name', student.first_name)
        student.last_name = request.POST.get('last_name', student.last_name)
        student.school = request.POST.get('school', student.school)
        student.email = request.POST.get('email', student.email)
        student.phone = request.POST.get('phone', student.phone)
        student.age = request.POST.get('age', student.age)
        student.bio = request.POST.get('bio', student.bio)
        student.interests = request.POST.get('interests', student.interests)

        if 'profile_picture' in request.FILES:
            student.profile_picture = request.FILES['profile_picture']

        student.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('setting')

    return render(request, 'website/settings.html', {'student': student})

@login_required
def stats(request):
    if not Student.objects.filter(email=request.user.email).exists():
        
        return redirect('unauthorized')

    email = request.user.email
    student = get_object_or_404(Student, email=email)
    if student.hours_volunteered <= 20:
        student.badge = "Beginner Volunteer"
        student.next_badge = "Amateur Volunteer"
    elif student.hours_volunteered <= 40:
        student.badge = "Amateur Volunteer"
        student.next_badge = "Intermediate Volunteer"
    elif student.hours_volunteered <= 60:
        student.badge = "Intermediate Volunteer"
        student.next_badge = "Experienced Volunteer"
    elif student.hours_volunteered <= 80:
        student.badge = "Experienced Volunteer"
        student.next_badge = "Pro Volunteer"
    elif student.hours_volunteered <= 100:
        student.badge = "Pro Volunteer"
        student.next_badge = "Expert Volunteer"
    else:
        student.badge = "Expert Volunteer"
        student.next_badge = "Maxed Out!"

    student.save()
    x = student.accept
    y = student.applied
    if y != 0:
        rate = (x / y) * 100
    else:
        rate = 0

    return render(request, "website/stats.html", {'student': student, 'rate': rate})

@login_required
def update_goal_hours(request):
    if not Student.objects.filter(email=request.user.email).exists():
        
        return redirect('unauthorized')

    if request.method == 'POST':
        email = request.user.email
        student = get_object_or_404(Student, email=email)
        try:
            goal_hours = int(request.POST.get('goal_hours', 0))
            if goal_hours >= 0:
                student.goal_hours = goal_hours
                student.save()
        except ValueError:
            pass
    return redirect('stats')

def organization_register(request):
    if request.method == "POST":
        name = request.POST['organization_name']
        legal_name = request.POST['legal_name']
        registration_number = request.POST['registration_number']
        address = request.POST['address']
        phone = request.POST['phone']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']
        document = request.FILES.get('document')

        if password == password2:
            if User.objects.filter(email=email).exists():
                messages.info(request, 'Email Already In Use!')
                return redirect('organization_register')
            elif not document:
                messages.info(request, 'Please upload a verification document!')
                return redirect('organization_register')
            else:
                verification_code = constants.randomnum
                
                pending_org = PendingOrganization(
                    organization_name=name,
                    legal_name=legal_name,
                    registration_number=registration_number,
                    address=address,
                    contact_phone=phone,
                    contact_email=email,
                    password=password,
                    document=document,
                    verification_code=verification_code
                )
                pending_org.save()

                logger.info(f"Registered pending org: {name}, Email: {email}")

                send_mail(
                    'ServeSync Organization Registration Submitted',
                    f"Hello,\nYour registration for {name} has been submitted. An admin will review your details and notify you within the next week.",
                    'servesyncinc@gmail.com',
                    [email],
                    fail_silently=False,
                )

                send_mail(
                    'New Organization Registration Pending Review',
                    f"A new organization ({name}) has registered. Please review their details and document at /pending_organization_verify/.",
                    'servesyncinc@gmail.com',
                    ['admin@example.com'],
                    fail_silently=False,
                )

                messages.info(request, "Registration submitted! You will be notified within the next week on your status.")
                return redirect('organization_login')
        else:
            messages.info(request, "Passwords Don't Match!")
            return redirect('organization_register')
    return render(request, 'website/organization_registration.html')

def organization_login(request):
    if request.method == "POST":
        username = request.POST['email']
        password = request.POST['password']
        
        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)
            if Organization.objects.filter(contact_email=user.email).exists():
                return redirect('organization')
            else:
                messages.error(request, 'No organization profile found.')
                return redirect('organization_login')
        else:
            messages.info(request, 'Credentials Invalid')
            return redirect('organization_login')
    return render(request, 'website/organization_login.html')

@login_required
def student(request):
    if not Student.objects.filter(email=request.user.email).exists():
        
        return redirect('unauthorized')

    try:
        user_email = request.user.email
        student = Student.objects.get(email=user_email)
        user_name = student.first_name 
        listings = VolunteerOpportunities.objects.all()
        random_listings = listings.order_by('?')[:3]

        signup_requests = SignupRequest.objects.filter(user=request.user).order_by('-timestamp')[:5]
        completions = Completion.objects.filter(signup__user=request.user).order_by('-signup__timestamp')[:5]
        
        recent_activities = []
        
        for signup in signup_requests:
            title = signup.opportunity.title[:30] + "..." if len(signup.opportunity.title) > 30 else signup.opportunity.title
            if signup.status == "Pending":
                description = f"Signed up for '{title}'"
            elif signup.status == "Accepted":
                description = f"Accepted for '{title}'"
            elif signup.status == "Declined":
                description = f"Declined for '{title}'"
            recent_activities.append({
                'description': description,
                'timestamp': signup.timestamp
            })
        
        for completion in completions:
            title = completion.signup.opportunity.title[:30] + "..." if len(completion.signup.opportunity.title) > 30 else completion.signup.opportunity.title
            description = f"Completed '{title}' ({completion.hours_credited}h)"
            recent_activities.append({
                'description': description,
                'timestamp': completion.signup.timestamp
            })
        
        recent_activities = sorted(recent_activities, key=lambda x: x['timestamp'], reverse=True)[:3]

    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('index')
    except Exception as e:
        logger.error(f"Error in student view: {e}")
        return redirect('index')

    return render(request, 'website/student.html', {
        'user_name': user_name,
        'student': student,
        'listings': listings,
        'random_listings': random_listings,
        'recent_activities': recent_activities
    })

@login_required
def organization(request):
    if not Organization.objects.filter(contact_email=request.user.email).exists():
        
        return redirect('unauthorized')

    try:
        user_email = request.user.email
        logger.debug(f"Fetching organization for email: {user_email}")
        organization = Organization.objects.get(contact_email=user_email)
        orgname = organization.organization_name

        active_opportunities = VolunteerOpportunities.objects.filter(
            posted_by=organization,
            time__gte=timezone.now()
        ).count()
        logger.debug(f"Active opportunities: {active_opportunities}")

        total_volunteers = SignupRequest.objects.filter(
            organization=organization
        ).values('user').distinct().count()
        logger.debug(f"Total volunteers: {total_volunteers}")

        try:
            total_hours_result = Completion.objects.filter(
                signup__organization=organization
            ).aggregate(total_hours=models.Sum('hours_credited'))
            total_hours = total_hours_result['total_hours'] if total_hours_result['total_hours'] is not None else 0
            logger.debug(f"Total hours calculated: {total_hours}")
        except Exception as e:
            logger.error(f"Error calculating total_hours: {e}")
            total_hours = 0

        recent_applications = SignupRequest.objects.filter(
            organization=organization
        ).select_related('user', 'opportunity').order_by('-timestamp')[:5]
        logger.debug(f"Recent applications count: {recent_applications.count()}")

        for application in recent_applications:
            try:
                student = Student.objects.get(email=application.user.email)
                application.student_name = f"{student.first_name} {student.last_name}".strip()
            except Student.DoesNotExist:
                application.student_name = application.user.username

    except Organization.DoesNotExist:
        logger.warning(f"No organization found for email: {user_email}")
        return redirect('index')
    except Exception as e:
        logger.error(f"Error in organization view: {e}")
        return redirect('index')

    return render(request, 'website/organization.html', {
        'organization': organization,
        'org': orgname,
        'active_opportunities': active_opportunities,
        'total_volunteers': total_volunteers,
        'total_hours': total_hours,
        'recent_applications': recent_applications
    })

@login_required
def studentcontact(request):
    if not Student.objects.filter(email=request.user.email).exists():
        
        return redirect('unauthorized')

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        contact_submission = Contact(
            full_name=full_name,
            email=email,
            message=message
        )
        contact_submission.save()
        messages.info(request, "Message Received! We'll get back to you shortly.")
        
    return render(request, 'website/student_contact.html')

@login_required
def studentorgview(request):
    if not Student.objects.filter(email=request.user.email).exists():
        
        return redirect('unauthorized')

    query = request.GET.get('search', '')
    if query:
        organizations = Organization.objects.filter(organization_name__icontains=query)
    else:
        organizations = Organization.objects.all()
    return render(request, 'website/student_organizationview.html', {'organizations': organizations, 'query': query})

@login_required
def studentlistings(request):
    if not Student.objects.filter(email=request.user.email).exists():
        
        return redirect('unauthorized')

    query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    age_requirement = request.GET.get('age_requirement', '')
    hours_expected = request.GET.get('hours_expected', '')

    listings = VolunteerOpportunities.objects.all()

    if query:
        listings = listings.filter(title__icontains=query)

    if category_filter:
        listings = listings.filter(category=category_filter)

    if age_requirement:
        if age_requirement == "13-17":
            listings = listings.filter(age_requirement__gte=13, age_requirement__lte=17)
        elif age_requirement == "18+":
            listings = listings.filter(age_requirement__gte=18)

    if hours_expected:
        if hours_expected == "1-5":
            listings = listings.filter(hours_expected__gte=1, hours_expected__lte=5)
        elif hours_expected == "6-10":
            listings = listings.filter(hours_expected__gte=6, hours_expected__lte=10)
        elif hours_expected == "10+":
            listings = listings.filter(hours_expected__gte=10)

    category_choices = {
        'Community & Social Services': 'Community & Social Services',
        'Education & Literacy': 'Education & Literacy',
        'Health & Wellness': 'Health & Wellness',
        'Environmental & Conservation': 'Environmental & Conservation',
        'Animal Welfare': 'Animal Welfare',
        'Arts, Culture & Heritage': 'Arts, Culture & Heritage',
        'International & Global Causes': 'International & Global Causes',
        'Sports & Recreation': 'Sports & Recreation',
        'Human Rights & Advocacy': 'Human Rights & Advocacy',
        'Emergency & Disaster Relief': 'Emergency & Disaster Relief',
        'Religious & Faith-Based': 'Religious & Faith-Based',
        'Technology & Innovation': 'Technology & Innovation',
        'Civic & Public Service': 'Civic & Public Service',
        'Business, Leadership & Professional Development': 'Business, Leadership & Professional Development',
        'Youth & Children Services': 'Youth & Children Services',
        'Senior Citizens Support': 'Senior Citizens Support',
        'Special Events & Fundraising': 'Special Events & Fundraising',
        'Skill-Based Volunteering': 'Skill-Based Volunteering',
        'Media & Communications': 'Media & Communications',
        'Military & Veterans Support': 'Military & Veterans Support',
    }

    return render(request, 'website/student_listing.html', {
        'listings': listings,
        'query': query,
        'category_choices': category_choices,
        'category_filter': category_filter,
        'age_requirement': age_requirement,
        'hours_expected': hours_expected,
    })

def is_valid_address(address):
    geolocator = Nominatim(user_agent="volunteer_app")
    try:
        location = geolocator.geocode(address, timeout=10)
        return location is not None
    except GeocoderTimedOut:
        return False

@login_required
def create(request):
    if not Organization.objects.filter(contact_email=request.user.email).exists():
        
        return redirect('unauthorized')

    if request.method == 'POST':
        title = request.POST['title']
        description = request.POST['description']
        address = request.POST['address']
        time_input = request.POST['time']
        skills_required = request.POST.get('skills_required', None)
        age_requirement = request.POST.get('age_requirement', None)
        hours_expected = request.POST['hours_expected']
        category = request.POST['category']
        user_email = request.user.email
        org = Organization.objects.get(contact_email=user_email)

        if not is_valid_address(address):
            messages.info(request, 'Please enter a valid address!')
            return render(request, 'website/create.html')

        if VolunteerOpportunities.objects.filter(title=title).exists():
            messages.info(request, 'Title Already Taken!')
            return render(request, 'website/create.html')

        VolunteerOpportunities.objects.create(
            title=title,
            description=description,
            address=address,
            time=time_input,
            skills_required=skills_required,
            age_requirement=age_requirement,
            hours_expected=hours_expected,
            category=category,
            posted_by=org,
            email=user_email
        )
        org.opportunities_created += 1
        org.save()

        messages.info(request, 'Listing Successfully Created!')
        return redirect('create')

    return render(request, 'website/create.html')

@login_required
def listing(request):
    if not Organization.objects.filter(contact_email=request.user.email).exists():
        
        return redirect('unauthorized')

    user_email = request.user.email
    try:
        org = Organization.objects.get(contact_email=user_email)
        listings = org.volunteer_opportunities.all()
    except Organization.DoesNotExist:
        org = None
        listings = None

    if not listings or listings.count() == 0:
        message = "You haven't posted any listings yet."
    else:
        message = None

    return render(request, 'website/listing.html', {
        'listings': listings,
        'message': message
    })

@login_required
def listing_details(request, listing_id):
    if not Organization.objects.filter(contact_email=request.user.email).exists():
        
        return redirect('unauthorized')

    listing = get_object_or_404(VolunteerOpportunities, id=listing_id)
    
    if request.user.email != listing.posted_by.contact_email:
        return HttpResponseForbidden("You are not authorized to edit this listing.")
    
    if request.method == "POST":
        if "edit" in request.POST:
            listing.title = request.POST.get("title")
            listing.address = request.POST.get("address")
            listing.time = request.POST.get("time")
            listing.hours_expected = request.POST.get("hours_expected")
            listing.age_requirement = request.POST.get("age_requirement")
            listing.description = request.POST.get("description")
            listing.save()
            return redirect("listing_details", listing_id=listing.id)
        elif "delete" in request.POST:
            listing.delete()
            return redirect("listing")
    
    return render(request, "website/listing_details.html", {"listing": listing})

@login_required
def listing_detail(request, id):
    if not Student.objects.filter(email=request.user.email).exists():
        
        return redirect('unauthorized')

    listing = get_object_or_404(VolunteerOpportunities, id=id)

    time_range = listing.time
    try:
        hours_match = re.match(r"(\d+)\s*hours", listing.hours_expected)
        if hours_match:
            hours = int(hours_match.group(1))
        else:
            hours = 0

        time_parts = listing.time.split(", ")
        if len(time_parts) >= 3:
            date_part = ", ".join(time_parts[:-1])
            time_part = time_parts[-1]
            start_time = datetime.strptime(f"{date_part} {time_part}", "%B %d, %Y %I:%M %p")
            end_time = start_time + timedelta(hours=hours)
            time_range = f"{date_part}, {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
    except (ValueError, AttributeError):
        time_range = listing.time

    has_signed_up = SignupRequest.objects.filter(user=request.user, opportunity=listing).exists()

    context = {
        'listing': listing,
        'time_range': time_range,
        'has_signed_up': has_signed_up,
    }
    return render(request, 'website/listing_detail.html', context)

@login_required
def listing_detaill(request, id):
    listing = get_object_or_404(VolunteerOpportunities, id=id)

    time_range = listing.time
    try:
        hours_match = re.match(r"(\d+)\s*hours", listing.hours_expected)
        if hours_match:
            hours = int(hours_match.group(1))
        else:
            hours = 0

        time_parts = listing.time.split(", ")
        if len(time_parts) >= 3:
            date_part = ", ".join(time_parts[:-1])
            time_part = time_parts[-1]
            start_time = datetime.strptime(f"{date_part} {time_part}", "%B %d, %Y %I:%M %p")
            end_time = start_time + timedelta(hours=hours)
            time_range = f"{date_part}, {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
    except (ValueError, AttributeError):
        time_range = listing.time

    has_signed_up = SignupRequest.objects.filter(user=request.user, opportunity=listing).exists()

    context = {
        'listing': listing,
        'time_range': time_range,
        'has_signed_up': has_signed_up,
    }
    return render(request, 'website/listing_detaill.html', context)

def contact(request):
    if not Organization.objects.filter(contact_email=request.user.email).exists():
        
        return redirect('unauthorized')
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        contact_submission = Contact(
            full_name=full_name,
            email=email,
            message=message
        )
        contact_submission.save()
        messages.info(request, "Message Received! We'll get back to you shortly.")
        
    return render(request, 'website/contact.html')

@login_required
def dashboard(request):
    if not Organization.objects.filter(contact_email=request.user.email).exists():
        
        return redirect('unauthorized')

    email = request.user.email
    org = get_object_or_404(Organization, contact_email=email)

    if org.facilitated <= 30:
        org.badge = "Beginner Organization"
        org.next_badge = "Amateur Organization"
    elif org.facilitated <= 60:
        org.badge = "Amateur Organization"
        org.next_badge = "Intermediate Organization"
    elif org.facilitated <= 90:
        org.badge = "Intermediate Organization"
        org.next_badge = "Experienced Organization"
    elif org.facilitated <= 120:
        org.badge = "Experienced Organization"
        org.next_badge = "Pro Organization"
    elif org.facilitated <= 150:
        org.badge = "Pro Organization"
        org.next_badge = "Expert Organization"
    else:
        org.badge = "Expert Organization"
        org.next_badge = "Maxed Out!"

    return render(request, 'website/dashboard.html', {'org': org})

@login_required
def update_org_goals(request):
    if not Organization.objects.filter(contact_email=request.user.email).exists():
        
        return redirect('unauthorized')

    if request.method == 'POST':
        email = request.user.email
        org = get_object_or_404(Organization, contact_email=email)
        try:
            goals = int(request.POST.get('goals', 0))
            if goals >= 0:
                org.goals = goals
                org.save()
        except ValueError:
            pass
    return redirect('dashboard')

@login_required
def stuorglistview(request, id):
    if not Student.objects.filter(email=request.user.email).exists():
        
        return redirect('unauthorized')

    organization = get_object_or_404(Organization, id=id)
    listings = VolunteerOpportunities.objects.filter(posted_by=organization)

    return render(request, "website/stuorglistview.html", {
        'organization': organization,
        'listings': listings,
    })

@login_required
def logouts(request):
    logout(request)
    return redirect('index')

@login_required
def signup(request):
    if not Organization.objects.filter(contact_email=request.user.email).exists():
        messages.error(request, "You are not authorized to access this page.")
        return redirect('unauthorized')

    org = request.user.email
    organization = get_object_or_404(Organization, contact_email=org)
    opportunities = VolunteerOpportunities.objects.filter(email=org)

    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    opportunity_id = request.GET.get('opportunity_id', '')
    page_number = request.GET.get('page', 1)

    # Use select_related for 'user' only
    signups = SignupRequest.objects.filter(organization=organization).select_related('user').order_by('-timestamp')

    if search:
        signups = signups.filter(
            Q(user__username__icontains=search) | Q(user__email__icontains=search)
        )
    if status:
        if status == 'Completed':
            signups = signups.filter(completed=True)
        else:
            signups = signups.filter(status=status, completed=False)
    if opportunity_id:
        signups = signups.filter(opportunity_id=opportunity_id)

    grouped_signups = {}
    for opportunity in opportunities:
        opp_signups = signups.filter(opportunity=opportunity)
        if opp_signups.exists():
            grouped_signups[opportunity] = opp_signups

    all_signups = []
    for opportunity, opp_signups in grouped_signups.items():
        all_signups.extend(opp_signups)

    # Attach Student to each SignupRequest
    email_to_student = {s.email: s for s in Student.objects.filter(email__in=[s.user.email for s in all_signups])}
    for signup in all_signups:
        signup.student = email_to_student.get(signup.user.email)

    paginator = Paginator(all_signups, 10)
    page_obj = paginator.get_page(page_number)

    page_grouped_signups = {}
    for opportunity in opportunities:
        page_opp_signups = [signup for signup in page_obj.object_list if signup.opportunity == opportunity]
        if page_opp_signups:
            page_grouped_signups[opportunity] = page_opp_signups

    if request.method == 'POST':
        action = request.POST.get('action')
        signup_id = request.POST.get('signup_id')

        if action == 'export_pdf':
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []

            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            title_style.textColor = colors.HexColor('#2A4494')
            normal_style = styles['BodyText']
            normal_style.textColor = colors.HexColor('#1F2A44')

            elements.append(Paragraph(f"Signup Details - {organization.organization_name}", title_style))
            elements.append(Spacer(1, 12))

            data = [['Opportunity', 'Username', 'Email', 'Status', 'Signup Date']]
            for opportunity, opp_signups in grouped_signups.items():
                for signup in opp_signups:
                    status = 'Completed' if signup.completed else signup.status
                    data.append([
                        opportunity.title,
                        signup.user.username,
                        signup.user.email,
                        status,
                        signup.timestamp.strftime('%Y-%m-%d %H:%M')
                    ])

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2A4494')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#F5F7FA')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F7FA')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1F2A44')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#C4C9D4')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#2A4494')),
            ]))
            elements.append(table)

            doc.build(elements)
            buffer.seek(0)
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="signup_details_{organization.organization_name}.pdf"'
            response.write(buffer.getvalue())
            buffer.close()
            return response

        signup = get_object_or_404(SignupRequest, id=signup_id, organization=organization)
        # Fetch Student by email
        stu = Student.objects.filter(email=signup.user.email).first()
        if not stu:
            stu = Student.objects.create(
                email=signup.user.email,
                first_name=signup.user.username,
                accept=0,
                decline=0,
                applied=0,
                hours_volunteered=0,
                people_helped=0,
                opportunities_completed=0,
                goal_hours=0
            )

        query_params = {}
        if search:
            query_params['search'] = search
        if status:
            query_params['status'] = status
        if opportunity_id:
            query_params['opportunity_id'] = opportunity_id

        try:
            if action == 'accept':
                signup.status = "Accepted"
                signup.save()
                organization.accepted += 1
                stu.accept += 1
                stu.save()
                organization.save()
                Notification.objects.create(
                    recipient=signup.user,
                    message=f"Your signup request for {signup.opportunity.title} has been accepted!",
                )
                Completion.objects.get_or_create(
                    signup=signup,
                    defaults={
                        'hours_credited': 0,
                        'people_credited': 0,
                        'task_completed': False,
                    }
                )
                messages.success(request, f"Signup by {signup.user.username} for {signup.opportunity.title} has been accepted.")
            elif action == 'decline':
                signup.status = "Declined"
                signup.save()
                organization.declined += 1
                stu.decline += 1
                stu.save()
                organization.save()
                Notification.objects.create(
                    recipient=signup.user,
                    message=f"Your signup request for {signup.opportunity.title} has been declined.",
                )
                messages.success(request, f"Signup by {signup.user.username} for {signup.opportunity.title} has been declined.")
        except Exception as e:
            messages.error(request, f"Error processing signup: {str(e)}")

        return redirect('signup', **query_params)

    context = {
        'organization': organization,
        'opportunities': opportunities,
        'grouped_signups': page_grouped_signups,
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'opportunity_id': opportunity_id,
    }
    return render(request, 'website/signups.html', context)

@login_required
def submit_signup(request):
    if not Student.objects.filter(email=request.user.email).exists():
        
        return redirect('unauthorized')

    if request.method == "POST":
        user = request.user
        organization_name = request.POST.get("org")
        organization = get_object_or_404(Organization, organization_name=organization_name)
        organizations = get_object_or_404(User, email=organization.contact_email)
        listing_title = request.POST.get("listing_title")
        opportunity = get_object_or_404(VolunteerOpportunities, title=listing_title)

        if SignupRequest.objects.filter(user=user, opportunity=opportunity).exists():
            messages.error(request, "You have already signed up for this opportunity.")
            return redirect("studentlistings")

        signup_request = SignupRequest.objects.create(
            user=user,
            organization=organization,
            opportunity=opportunity,
            status="Pending",
        )

        stu = get_object_or_404(Student, email=user.email)
        stu.applied += 1
        stu.save()

        Notification.objects.create(
            recipient=organizations,
            message=f"{user.username} signed up for {opportunity.title}.",
        )

        messages.success(request, "Your signup request has been sent!")
        return redirect("studentlistings")
    return render(request, "website/student_listing.html")

@login_required
def accept_signup(request, signup_id):
    if not Organization.objects.filter(contact_email=request.user.email).exists():
        messages.error(request, "You are not authorized to access this page.")
        return redirect('unauthorized')

    signup = get_object_or_404(SignupRequest, id=signup_id)
    email = signup.user.email
    org = signup.organization
    stu = get_object_or_404(Student, email=email)

    completion, created = Completion.objects.get_or_create(
        signup=signup,
        defaults={'hours_credited': 0, 'people_credited': 0, 'task_completed': False}
    )

    if request.method == 'POST':
        hours_credited = request.POST.get('hours_credited')
        people_credited = request.POST.get('people_credited')
        task_completed = request.POST.get('task_completed') == 'on'

        try:
            hours_credited = int(hours_credited)
            people_credited = int(people_credited)
            if hours_credited < 0 or people_credited < 0:
                raise ValueError("Hours and people credited cannot be negative.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid input for hours or people credited.")
            return redirect('accept_signup', signup_id=signup.id)

        # Update Completion
        completion.hours_credited = hours_credited
        completion.people_credited = people_credited
        completion.task_completed = task_completed
        completion.save()

        # Update SignupRequest
        signup.hours_volunteered = hours_credited
        signup.people_helped = people_credited
        signup.completed = task_completed
        signup.status = "Credited"  # Set status to Credited
        signup.save()

        # Update Student
        stu.hours_volunteered += hours_credited
        stu.people_helped += people_credited
        if task_completed:
            stu.opportunities_completed += 1
        stu.save()

        # Update Organization
        org.facilitated += hours_credited
        org.people_helped += people_credited
        if task_completed:
            org.opportunities_completed += 1
        org.save()

        # Notify user
        Notification.objects.create(
            recipient=signup.user,
            message=f"Your signup request for {signup.opportunity.title} has been credited!",
        )

        messages.success(request, f"Signup by {signup.user.username} for {signup.opportunity.title} has been credited.")
        return redirect('signup')

    return render(request, "website/accept_signup.html", {
        "signup": signup,
        "completion": completion,
    })

@login_required
def submit_completion(request, signup_id):
    if not Organization.objects.filter(contact_email=request.user.email).exists():
        
        return redirect('unauthorized')

    signup = get_object_or_404(SignupRequest, id=signup_id)

    if request.method == "POST":
        signup.hours_volunteered = request.POST.get('hours_volunteered')
        signup.people_helped = request.POST.get('people_helped')
        signup.completed = True
        signup.save()

        Notification.objects.create(
            recipient=signup.user,
            message=f"Your volunteering task for {signup.opportunity.title} has been marked as complete!",
        )

        messages.success(request, f"Task completion details for {signup.user.username} have been submitted.")
        return redirect('signup')

def login_choice(request):
    return render(request, 'website/login_choice.html')

def register_choice(request):
    return render(request, 'website/register_choice.html')

@login_required
def leaderboard(request):
    if not Student.objects.filter(email=request.user.email).exists():
        
        return redirect('unauthorized')

    sort_by = request.GET.get('sort_by', 'impact_points')
    badge_filter = request.GET.get('badge', '')

    students = Student.objects.all().order_by('-hours_volunteered')

    if sort_by == 'hours':
        students = students.order_by('-hours_volunteered')
    elif sort_by == 'people':
        students = students.order_by('-people_helped')
    elif sort_by == 'tasks':
        students = students.order_by('-opportunities_completed')
    else:
        students = students.order_by('-hours_volunteered')

    badge_choices = Student.objects.filter(badge__isnull=False).values_list('badge', flat=True).distinct()

    top_students = students[:3]
    other_students = students[3:]

    context = {
        'top_students': top_students,
        'other_students': other_students,
        'sort_by': sort_by,
        'badge_filter': badge_filter,
        'badge_choices': badge_choices,
    }
    return render(request, 'website/leaderboard.html', context)

def unauthorized(request):
    return render(request, 'website/unauthorized.html')

@login_required
def organization_settings(request):
    # Check if the user has an associated Organization profile
    if not Organization.objects.filter(contact_email=request.user.email).exists():
        
        return redirect('unauthorized')

    # Fetch the Organization object
    organization = get_object_or_404(Organization, contact_email=request.user.email)

    if request.method == 'POST':
        # Update fields based on submitted data
        organization.organization_name = request.POST.get('organization_name', organization.organization_name)
        organization.address = request.POST.get('address', organization.address)
        organization.contact_email = request.POST.get('contact_email', organization.contact_email)
        organization.contact_phone = request.POST.get('contact_phone', organization.contact_phone)
        organization.website_url = request.POST.get('website_url', organization.website_url)  # New field

        # Validate email uniqueness (if changed)
        if organization.contact_email != request.user.email and User.objects.filter(email=organization.contact_email).exists():
            messages.error(request, "This email is already in use.")
            return redirect('organization_settings')

        # Update the User email and username if the organization email changes
        if organization.contact_email != request.user.email:
            request.user.email = organization.contact_email
            request.user.username = organization.contact_email
            request.user.save()

        try:
            organization.full_clean()  # Validate all fields, including website_url
            organization.save()
        except ValidationError as e:
            # Handle URL validation errors specifically
            if 'website_url' in e.message_dict:
                messages.error(request, "Please enter a valid URL (e.g., https://example.com).")
            else:
                messages.error(request, "There was an error updating your profile. Please check the form.")
            return redirect('organization_settings')

        organization.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('organization_settings')

    return render(request, 'website/organization_settings.html', {'organization': organization})