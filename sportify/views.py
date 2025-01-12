from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponse
from django.template import loader
from django.contrib import messages
from django.db.models import Count
from django.views.generic.detail import DetailView
from .models import Team, User, PracticeSchedule, PracticeSession
from django.conf import settings
from django.urls import reverse
from django.http import StreamingHttpResponse
from django.utils import timezone
import boto3
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def home(request):
    popular_teams = Team.objects.annotate(num_members=Count('members')).order_by('-num_members')[:10]
    return render(request, 'sportify/home.html', {'popular_teams': popular_teams})


def about(request):
    template = loader.get_template("sportify/about.html")
    context = {}
    return HttpResponse(template.render(context, request))

def teams(request):
    teams = Team.objects.all()
    if request.user.is_authenticated:
        user = User.objects.get(email=request.user.email)
        user_teams = Team.objects.filter(members=user)
        # Exclude the teams the user is already part of from the explore teams list
        explore_teams = Team.objects.exclude(members=user)
        user = User.objects.get(email=request.user.email)
        all_sports = ["Soccer", "Basketball", "Baseball", "Football", "Hockey", "Volleyball", "Ultimate Frisbee"]
        practice_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return render(request, 'sportify/teams.html', {'teams': explore_teams, 'userDjan': user, "user_teams": user_teams, "all_sports": all_sports, "practice_days": practice_days})
    return render(request, 'sportify/teams.html', {'teams': teams})


def create_team(request):
    print("create team")
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to create a team.")
        return redirect('home')
    user = User.objects.get(email=request.user.email)
    if user.is_pma:
        messages.error(request, "You are not authorized to create a team.")
        return redirect('home')

    if request.method == 'POST':
        name = request.POST['name']
        description = request.POST['description']
        associated_sport = request.POST['sport']
        owner = User.objects.get(email=request.user.email)

        practice_schedule = PracticeSchedule.objects.create()
        days = request.POST.getlist('session_day[]')
        start_times = request.POST.getlist('session_start[]')
        end_times = request.POST.getlist('session_end[]')

        for day, start, end in zip(days, start_times, end_times):
            session = PracticeSession.objects.create(
                day_of_week=day,
                start_time=start,
                end_time=end
            )
            practice_schedule.sessions.add(session)

        team = Team.objects.create(
            name=name,
            description=description,
            associated_sport=associated_sport,
            owner=owner,
            practice_schedule=practice_schedule
        )

        s3 = boto3.client(
            's3',
            aws_access_key_id = settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY,
        )
        team_folder = f'teams/{team.id}/'
        s3.put_object(Bucket = settings.AWS_STORAGE_BUCKET_NAME, Key = team_folder)

        team.add_member(User.objects.get(email=request.user.email))
        team.save()

        messages.success(request, 'Team created successfully!')
        return redirect('team_detail', pk=team.id)

    return render(request, 'sportify/create_team.html')

def load_user(request):
    print("redirected successfully")
    email = request.user.email
    first_name = request.user.first_name
    last_name = request.user.last_name
    google_profile_picture_url = request.user.socialaccount_set.filter(provider='google').first().extra_data['picture']
    
    
    user, created = User.objects.get_or_create(email=email, defaults={
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'is_pma': False,
    })
    user.save()
    if google_profile_picture_url:
        user.add_pfpURL(google_profile_picture_url)
        user.save()
    print("user saved")
    if created:
        messages.success(request, 'User created successfully!')

    return redirect('home')

def team_detail(request, pk):
    team = get_object_or_404(Team, pk=pk)
    user = User.objects.get(email=request.user.email)
    if user not in team.members.all() and not user.is_pma_administrator():
        messages.error(request, "You are not authorized to view this team.")
        return redirect('teams')
    context = {}
    context['upload_url'] = reverse('upload_team_file', args=[pk])

    s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    team_folder = f'teams/{pk}/'
    response = s3.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Prefix=team_folder)

    files = response.get('Contents', [])
    file_urls = []

    for file in files:
        file_key = file['Key']
        if file_key == team_folder:
            continue

        file_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': file_key},
            ExpiresIn=3600
        )

        metadata_response = s3.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=file_key
        )

        metadata = metadata_response.get('Metadata', {})
        datetime = metadata.get('upload_datetime')
        description = metadata.get('description')
        tags = []
        for i in range(0, 10):
            tags.append(metadata.get(f'tag{i}'))

        file_data = {
            'name': file_key[len(team_folder):],
            'url': file_url,
            'upload_datetime': datetime,
            'description': description,
            'tags': tags
        }

        file_urls.append(file_data)

    context['files'] = file_urls

    user = User.objects.get(email=request.user.email)
    context['userDjan'] = user

    load_all = request.GET.get('load_all', '0') == '1'
    context['team_messages'] = Team.objects.get(id=pk).get_messages(load_all=load_all)  # Fetch messages based on the parameter
    context['team'] = Team.objects.get(id=pk)

    return render(request, 'sportify/team_detail.html', context)
    
@login_required
def view_content(request, team_id, file_name):
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    
    team = get_object_or_404(Team, id=team_id)
    
    team_folder = f'teams/{team_id}/'
    file_key = f'{team_folder}{file_name}'
    
    file_url = s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': file_key,
        },
        ExpiresIn=3600
    )

    if file_name.endswith('.txt'):
        response = s3.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file_key)
        text_content = response['Body'].read().decode('utf-8')
        context = {
            'file_type': 'txt',
            'text_content': text_content,
            'file_name': file_name,
            'team': team
        }
    elif file_name.endswith('.jpg') or file_name.endswith('.png'):
        context = {
            'file_type': 'image',
            'file_url': file_url,
            'file_name': file_name,
            'team': team
        }
    elif file_name.endswith('.pdf'):
        context = {
            'file_type': 'pdf',
            'file_url': file_url,
            'file_name': file_name,
            'team': team
        }
    else:
        return HttpResponse("Unsupported file type", status=400)
    
    return render(request, 'sportify/view_content.html', context)

@login_required
def stream_pdf(request, team_id, file_name):
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    
    team_folder = f'teams/{team_id}/'
    file_key = f'{team_folder}{file_name}'

    if file_name.endswith('.pdf'):
        file_obj = s3.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file_key)
        pdf_stream = file_obj['Body']

        response = StreamingHttpResponse(
            streaming_content=pdf_stream,
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'inline; filename="{file_name}"'
        return response

    return HttpResponse("Unsupported file type", status=400)


@login_required
def join_team(request, pk):
    team = get_object_or_404(Team, pk=pk)
    prospective_members = team.prospective_members.all()
    user = User.objects.get(email=request.user.email)
    if user not in prospective_members:
        team.add_prospective_member(user)
        team.save()
        messages.success(request, 'Your application to join the team has been submitted!')
    else:
        messages.error(request, 'You have already applied to join this team!')
    return redirect('teams')


@login_required
def leave_team(request, pk):
    team = get_object_or_404(Team, pk=pk)
    user = User.objects.get(email=request.user.email)
    team.remove_member(user)
    team.save()
    messages.success(request, 'You have successfully left the team!')
    return redirect('teams')


@login_required
def edit_team(request, pk):
    team = get_object_or_404(Team, id=pk)
    user = User.objects.get(email=request.user.email)
    # Ensure the user is the owner of the team
    if team.get_owner() != user:
        print(team.owner.get_email," ", request.user.email)
        messages.error(request, "You are not authorized to edit this team.")
        return redirect('team_detail', pk=pk)

    practice_schedule = team.practice_schedule
    practice_sessions = practice_schedule.get_sessions()
    if request.method == 'POST':
        team.name = request.POST['name']
        team.description = request.POST['description']


        team.practice_schedule.delete_all_sessions()
        practice_schedule = PracticeSchedule.objects.create()
        days = request.POST.getlist('session_day[]')
        start_times = request.POST.getlist('session_start[]')
        end_times = request.POST.getlist('session_end[]')

        for day, start, end in zip(days, start_times, end_times):
            session = PracticeSession.objects.create(
                day_of_week=day,
                start_time=start,
                end_time=end
            )
            practice_schedule.sessions.add(session)
        team.practice_schedule = practice_schedule
        team.save()

        messages.success(request, 'Team updated successfully!')
        return redirect('team_detail', pk=pk)

    return render(request, 'sportify/edit_team.html', {'team': team, 'practice_sessions': practice_sessions})



@login_required
def delete_team(request, pk):
    team = get_object_or_404(Team, pk=pk)
    user = User.objects.get(email=request.user.email)
    
    # Ensure the user is the owner of the team
    if team.get_owner() != user and not user.is_pma_administrator:
        print("not deleted")
        messages.error(request, "You are not authorized to delete this team.")
        return redirect('team_detail', pk=pk)
    
    # Delete the S3 folder associated with the team
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    team_folder = f'teams/{team.id}/'
    
    try:
        # List all objects under the folder
        objects = s3.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Prefix=team_folder)
        if 'Contents' in objects:
            for obj in objects['Contents']: # Delete each object
                s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=obj['Key'])
        messages.success(request, 'Team folder deleted successfully from S3.')
    except Exception as e:
        messages.error(request, f'Error deleting team folder from S3: {e}')

    # If the user is authorized, delete the team
    team.delete()
    print("deleted")
    messages.success(request, 'Team deleted successfully!')
    return redirect("teams")

def add_message(request, pk):
    team = get_object_or_404(Team, pk=pk)
    user = User.objects.get(email=request.user.email)
    if request.method == 'POST':
        message = request.POST['content']
        message = message.strip()
        if not message:
            messages.error(request, 'Message cannot be empty!')
        team.send_message(message, user)
        messages.success(request, 'Message sent successfully!')
    return redirect('team_detail', pk=pk)

def clear_messages(request, pk):
    team = get_object_or_404(Team, pk=pk)
    user = User.objects.get(email=request.user.email)
    if user == team.get_owner():
        team.clear_messages()
        messages.success(request, 'Messages cleared successfully!')
    return redirect('team_detail', pk=pk)

def upload_team_file(request, team_id):
    if request.method == 'POST':
        file = request.FILES['file']
        file_extension = file.name.split('.')[-1]
        filename = request.POST.get('filename', file.name)  # Use provided name or file's original name
        filename += ("." + file_extension)
        description = request.POST.get('description', '')
        upload_datetime = timezone.now().isoformat()
        metadata = {
            'file_extension': file_extension,
            'description': description,
            'upload_datetime': upload_datetime
        }

        tags = request.POST.get('tags', '')
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        for index, tag in enumerate(tag_list):
            metadata[f'tag{index}'] = tag

        team_folder = f'teams/{team_id}/'
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        s3.upload_fileobj(file,
                          settings.AWS_STORAGE_BUCKET_NAME,
                          f'{team_folder}{filename}',
                          ExtraArgs={
                              'Metadata': metadata
                          })

        messages.success(request, 'File uploaded successfully!')
        return redirect('team_detail', pk=team_id)

    return render(request, 'sportify/upload_file.html')

def delete_team_file(request, team_id, file_name):
    if request.method == 'GET':
        team_folder = f'teams/{team_id}/'
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        try:
            s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=f'{team_folder}{file_name}')
            messages.success(request, f"File '{file_name}' deleted successfully.")
        except Exception as e:
            messages.error(request, f"Failed to delete file '{file_name}': {e}")

    return redirect('team_detail', pk=team_id)

def calendar(request):
    template = loader.get_template("sportify/calendar.html")
    context = {}
    return HttpResponse(template.render(context, request))

def login(request):
    return render(request, "sportify/login.html")

def logout_view(request):
    logout(request)
    return redirect("home")



@login_required
def accept_member(request, team_id, member_id):
    team = get_object_or_404(Team, pk=team_id)
    member = get_object_or_404(User, pk=member_id)
    user = User.objects.get(email=request.user.email)
    
    if user == team.get_owner():
        team.accept_member(member)
        messages.success(request, f'{member.get_full_name()} has been accepted to the team.')
    return redirect('team_detail', pk=team_id)

@login_required
def deny_member(request, team_id, member_id):
    team = get_object_or_404(Team, pk=team_id)
    member = get_object_or_404(User, pk=member_id)
    user = User.objects.get(email=request.user.email)
    if user == team.get_owner():
        team.deny_member(member)
        messages.success(request, f'{member.get_full_name()} has been denied from the team.')
    return redirect('team_detail', pk=team_id)
@login_required
def remove_member(request, team_id, member_id):
    team = get_object_or_404(Team, pk=team_id)
    member = get_object_or_404(User, pk=member_id)
    user = User.objects.get(email=request.user.email)
    if user == team.get_owner():
        team.remove_member(member)
        messages.success(request, f'{member.get_full_name()} has been removed from the team.')
        
    return redirect('team_detail', pk=team_id)

@login_required
def transfer_ownership(request, team_id, member_id):
    team = get_object_or_404(Team, pk=team_id)
    member = get_object_or_404(User, pk=member_id)
    user = User.objects.get(email=request.user.email)
    if user == team.get_owner():
        team.transfer_ownership(member)
        messages.success(request, f'{member.get_full_name()} has been made the owner of this team.')
        team.save()
    return redirect('team_detail', pk=team_id)

def profile(request):
    template = loader.get_template("sportify/profile.html")
    user = User.objects.get(email=request.user.email)
    print(user.get_pfpURL())
    return HttpResponse(template.render({'userDjan': user}, request))

@login_required
def edit_profile(request):
    
    userDjan = User.objects.get(email=request.user.email)

    if request.method == 'POST':
        user = User.objects.get(email=request.user.email)
        bio = request.POST['bio']
        location = request.POST['location']
        phone_number = request.POST['phone_number']
        nickname = request.POST['nickname']
        user.change_bio(bio)
        user.change_location(location)
        user.change_phone_number(phone_number)
        user.change_nickname(nickname)
        user.save()


        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')  # Change 'profile' to the name of the profile page URL pattern

    return render(request, 'sportify/edit_profile.html', {'user': request.user, 'userDjan': userDjan})



def stage_file(request, pk):
    template = loader.get_template("sportify/stage_file.html")
    context = {}
    context['upload_url'] = reverse('upload_team_file', args=[pk])
    return HttpResponse(template.render(context, request))


def user_detail(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    context = {}
    context['userDjan'] = user
    if user.email == request.user.email:
        return redirect('profile')
    return render(request, 'sportify/user_detail.html', context)

@login_required
def dashboard(request):
    user = User.objects.get(email=request.user.email)
    teams_owned = user.owned_teams.all()
    teams_member = user.teams.exclude(owner=user)

    return render(request, 'sportify/dashboard.html', {
        'teams_owned': teams_owned,
        'teams_member': teams_member,
    })