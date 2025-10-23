from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('login_choice/', views.login_choice, name='login_choice'),  # New route
    path('register_choice/', views.register_choice, name='register_choice'),  # New route
    path('register/', views.register, name='register'),
    path('code/', views.code, name='code'),
    path('login/', views.login, name='login'),
    path('organization_register/', views.organization_register, name='organization_register'),
    path('organization_login/', views.organization_login, name='organization_login'),
    path('student/', views.student, name='student'),
    path('studentcontact/', views.studentcontact, name='studentcontact'),
    path('studentorgview/', views.studentorgview, name='studentorgview'),
    path('studentlistings/', views.studentlistings, name='studentlistings'),
    path('organization/', views.organization, name='organization'),
    path('listing/', views.listing, name='listing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create, name='create'),
    path('contact/', views.contact, name='contact'),
    path('listing/<int:listing_id>/', views.listing_details, name='listing_details'),
    path('student_listing/<int:id>/', views.listing_detail, name='listing_detail'),
    path('student_listings/<int:id>/', views.listing_detaill, name='listing_detaill'),
    path('organizations/<int:id>/listings/', views.stuorglistview, name='stuorglistview'),
    path('setting/', views.setting, name='setting'),
    path('stats/', views.stats, name='stats'),
    path('logout/', views.logouts, name='logouts'),
    path('signup/', views.signup, name='signup'),
    path("submitsignups/", views.submit_signup, name="submit_signup"),
    path('accept_signup/<int:signup_id>/', views.accept_signup, name='accept_signup'),
    path('submit_completion/<int:signup_id>/', views.submit_completion, name='submit_completion'),
    path('update-goal-hours/', views.update_goal_hours, name='update_goal_hours'),
    path('update-org-goals/', views.update_org_goals, name='update_org_goals'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('unauthorized/', views.unauthorized, name='unauthorized'),
    path('organization_settings/', views.organization_settings, name='organization_settings'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)