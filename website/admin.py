from django.contrib import admin
from .models import Notification, Organization, Student, VolunteerOpportunities, Contact, SignupRequest, PendingOrganization
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
import logging

# Set up logging
logger = logging.getLogger(__name__)

@admin.register(PendingOrganization)
class PendingOrganizationAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = ('organization_name', 'contact_email', 'contact_phone', 'address', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('organization_name', 'contact_email')
    ordering = ('-created_at',)

    # Custom admin actions
    actions = ['approve_organizations', 'reject_organizations']

    def approve_organizations(self, request, queryset):
        """
        Approve selected PendingOrganization entries:
        - Create User and Organization objects
        - Send approval email
        - Delete PendingOrganization entry
        """
        for pending_org in queryset:
            try:
                # Create User
                user = User.objects.create_user(
                    username=pending_org.contact_email,
                    email=pending_org.contact_email,
                    password=pending_org.password,
                )

                # Create Organization
                organization = Organization.objects.create(
                    organization_name=pending_org.organization_name,
                    address=pending_org.address,
                    contact_email=pending_org.contact_email,
                    contact_phone=pending_org.contact_phone,
                    facilitated=0,
                    people_helped=0,
                    opportunities_created=0,
                    opportunities_completed=0,
                    accepted=0,
                    declined=0,
                    goals=0,
                    badge="",
                    next_badge="",
                )

                # Save objects
                user.save()
                organization.save()

                # Send approval email
                send_mail(
                    'ServeSync Organization Approved',
                    f"Congratulations {pending_org.organization_name},\nYour organization has been approved! You can now log in with your email and password.",
                    'servesyncinc@gmail.com',
                    [pending_org.contact_email],
                    fail_silently=False,
                )

                # Log and delete
                logger.info(f"Approved organization: {pending_org.organization_name}")
                pending_org.delete()
                self.message_user(request, f"Approved {pending_org.organization_name}", level=messages.SUCCESS)

            except Exception as e:
                logger.error(f"Error approving {pending_org.organization_name}: {str(e)}")
                self.message_user(request, f"Error approving {pending_org.organization_name}: {str(e)}", level=messages.ERROR)

    approve_organizations.short_description = "Approve selected organizations"

    def reject_organizations(self, request, queryset):
        """
        Reject selected PendingOrganization entries:
        - Send rejection email
        - Delete PendingOrganization entry
        """
        for pending_org in queryset:
            try:
                # Send rejection email
                send_mail(
                    'ServeSync Organization Registration Rejected',
                    f"Hello {pending_org.organization_name},\nYour registration was not approved. Please contact support for more information.",
                    'servesyncinc@gmail.com',
                    [pending_org.contact_email],
                    fail_silently=False,
                )

                # Log and delete
                logger.info(f"Rejected organization: {pending_org.organization_name}")
                pending_org.delete()
                self.message_user(request, f"Rejected {pending_org.organization_name}", level=messages.SUCCESS)

            except Exception as e:
                logger.error(f"Error rejecting {pending_org.organization_name}: {str(e)}")
                self.message_user(request, f"Error rejecting {pending_org.organization_name}: {str(e)}", level=messages.ERROR)

    reject_organizations.short_description = "Reject selected organizations"

    def get_queryset(self, request):
        """
        Restrict access to staff users only
        """
        qs = super().get_queryset(request)
        if not request.user.is_staff:
            return qs.none()  # Return empty queryset for non-staff users
        return qs

    def has_module_permission(self, request):
        """
        Only allow staff users to see the model in the admin
        """
        return request.user.is_staff


# Register your models here.
admin.site.register(Organization)
admin.site.register(Student)
admin.site.register(VolunteerOpportunities)
admin.site.register(Contact)
admin.site.register(SignupRequest)
admin.site.register(Notification)
