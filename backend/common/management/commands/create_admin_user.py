from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from getpass import getpass


class Command(BaseCommand):
    help = 'Create a new admin user for the Echo Chamber Analyst system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username for the admin user (default: admin)'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email for the admin user (default: admin@example.com)'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for the admin user (will prompt if not provided)'
        )
        parser.add_argument(
            '--superuser',
            action='store_true',
            help='Create as superuser (default: True)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if user exists (will update password)'
        )

    def handle(self, *args, **options):
        username = options.get('username') or 'admin'
        email = options.get('email') or 'admin@example.com'
        password = options.get('password')
        is_superuser = options.get('superuser', True)
        force = options.get('force', False)

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            if not force:
                self.stdout.write(
                    self.style.ERROR(f'User "{username}" already exists. Use --force to update.')
                )
                return
            else:
                user = User.objects.get(username=username)
                self.stdout.write(f'Updating existing user: {username}')
        else:
            user = None

        # Get password if not provided
        if not password:
            password = getpass(f'Enter password for {username}: ')
            if not password:
                self.stdout.write(self.style.ERROR('Password is required'))
                return

        # Create or update user
        if user:
            # Update existing user
            user.email = email
            user.is_staff = True
            user.is_superuser = is_superuser
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Updated user: {username}')
            )
        else:
            # Create new user
            if is_superuser:
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created superuser: {username}')
                )
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                user.is_staff = True
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created staff user: {username}')
                )

        # Display login information
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Login Credentials:'))
        self.stdout.write(f'Username: {username}')
        self.stdout.write(f'Password: {password}')
        self.stdout.write(f'Email: {email}')
        self.stdout.write(f'Superuser: {user.is_superuser}')
        self.stdout.write(f'Staff: {user.is_staff}')
        self.stdout.write('')
        self.stdout.write('You can now login to:')
        self.stdout.write('- Django Admin: http://localhost:8000/admin/')
        self.stdout.write('- Your application frontend')