"""Authentication routes for GitHub OAuth."""
from flask import redirect, url_for, session, request, current_app, jsonify
from flask_login import login_user, logout_user, current_user
from . import auth_bp
from services.database import UserService
import requests


@auth_bp.route('/login')
def login():
    """Redirect to GitHub OAuth login."""
    github_client_id = current_app.config['GITHUB_CLIENT_ID']
    redirect_uri = url_for('auth.callback', _external=True)

    # Store the next URL in session to redirect after login
    session['next_url'] = request.args.get('next', '/')

    # GitHub OAuth authorization URL
    github_auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={github_client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope=user:email"
    )

    return redirect(github_auth_url)


@auth_bp.route('/callback')
def callback():
    """Handle GitHub OAuth callback."""
    code = request.args.get('code')

    if not code:
        return jsonify({'error': 'No authorization code received'}), 400

    # Exchange code for access token
    token_url = 'https://github.com/login/oauth/access_token'
    token_data = {
        'client_id': current_app.config['GITHUB_CLIENT_ID'],
        'client_secret': current_app.config['GITHUB_CLIENT_SECRET'],
        'code': code,
        'redirect_uri': url_for('auth.callback', _external=True)
    }
    token_headers = {'Accept': 'application/json'}

    token_response = requests.post(token_url, data=token_data, headers=token_headers)
    token_json = token_response.json()

    access_token = token_json.get('access_token')

    if not access_token:
        return jsonify({'error': 'Failed to get access token'}), 400

    # Get user info from GitHub
    user_url = 'https://api.github.com/user'
    user_headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }

    user_response = requests.get(user_url, headers=user_headers)
    user_data = user_response.json()

    # Get user email if not public
    email = user_data.get('email')
    if not email:
        email_url = 'https://api.github.com/user/emails'
        email_response = requests.get(email_url, headers=user_headers)
        emails = email_response.json()
        # Get primary email
        for email_obj in emails:
            if email_obj.get('primary'):
                email = email_obj.get('email')
                break

    # Create or update user in database
    user = UserService.get_or_create_user(
        github_id=str(user_data['id']),
        username=user_data['login'],
        email=email,
        avatar_url=user_data.get('avatar_url'),
        name=user_data.get('name'),
        github_token=access_token
    )

    # Log in the user
    login_user(user)

    # Redirect to the original page or home
    next_url = session.pop('next_url', '/')
    return redirect(next_url)


@auth_bp.route('/logout')
def logout():
    """Log out the current user."""
    logout_user()
    return redirect(url_for('index'))


@auth_bp.route('/user')
def user_info():
    """Get current user info (API endpoint)."""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'username': current_user.username,
            'email': current_user.email,
            'avatar_url': current_user.avatar_url,
            'name': current_user.name
        })
    return jsonify({'authenticated': False})
