from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('about/', views.about, name='about'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('teams/', views.teams, name='teams'),
    path('calendar/', views.calendar, name='calendar'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('create_team/', views.create_team, name='create_team'),
    path('team/<uuid:pk>/', views.team_detail, name='team_detail'),
    path('team/<uuid:pk>/edit/', views.edit_team, name='edit_team'),
    path('team/<uuid:pk>/delete/', views.delete_team, name='delete_team'),
    path('team/<uuid:pk>/join/', views.join_team, name='join_team'),
    path('team/<uuid:pk>/leave/', views.leave_team, name='leave_team'),
    path('team/<uuid:pk>/add_message/', views.add_message, name='add_message'),
    path('team/<uuid:pk>/clear_messages/', views.clear_messages, name='clear_messages'),
    path('team/<uuid:team_id>/accept/<uuid:member_id>/', views.accept_member, name='accept_member'),
    path('team/<uuid:team_id>/deny/<uuid:member_id>/', views.deny_member, name='deny_member'),
    path('team/<uuid:team_id>/remove/<uuid:member_id>/', views.remove_member, name='remove_member'),
    path('team/<uuid:team_id>/transfer/<uuid:member_id>/', views.transfer_ownership, name='transfer_ownership'),
    path('load_user/', views.load_user, name='load_user'),
    path('team/<uuid:pk>/stage_file/', views.stage_file, name='stage_file'), #View to stage a file to be uploaded
    path('team/<uuid:team_id>/upload/', views.upload_team_file, name='upload_team_file'), #View to actually upload the file
    path('teams/<uuid:team_id>/view-content/<str:file_name>/', views.view_content, name='view_content'),
    path('teams/<uuid:team_id>/pdf/<str:file_name>/', views.stream_pdf, name='stream_pdf'),
    path('teams/<uuid:team_id>/delete/<str:file_name>', views.delete_team_file, name='delete_team_file'),
    path('user/<uuid:user_id>/', views.user_detail, name='user_detail'),
]
