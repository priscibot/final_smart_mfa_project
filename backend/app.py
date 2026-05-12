"""
Smart Multi-Factor Authentication System - Flask Backend
Provides password and keystroke-based authentication.
"""

from datetime import datetime, timedelta
import json
import os
import secrets
import smtplib
import sys
from email.message import EmailMessage

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

from feature_extraction import BehavioralFeatureExtractor

app = Flask(
    __name__,
    template_folder='../frontend/templates',
    static_folder='../frontend/static'
)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if os.environ.get('VERCEL'):
    DATA_DIR = '/tmp/smart_mfa_data'
else:
    DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'users.db').replace('\\', '/')


app.config['SECRET_KEY'] = 'smart-mfa-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
feature_extractor = BehavioralFeatureExtractor()

MIN_ENROLLMENT_SAMPLES = 3
MIN_KEYSTROKE_EVENTS = 5
VECTOR_TOLERANCE_FLOOR_MS = 18.0
RESET_TOKEN_EXPIRY_MINUTES = 15

ROLE_PAGE_CONTENT = {
    'student': {
        'label': 'Student',
        'accent': '#1f936a',
        'subtitle': 'Academic records, enrollment progress, and semester activity',
        'signin_help': 'Sign in to access the student portal',
        'signup_help': 'Create a student account to access courses and academic services',
        'profile': {
            'name': 'Adaeze Nwosu',
            'identifier_label': 'Student ID',
            'identifier': '2023124567',
            'summary': 'Computer Science | 200 Level',
            'note': 'Review your academic summary, current courses, and enrollment details for Spring 2026.',
            'badge': "Dean's List · Good Standing",
            'avatar': 'AN',
        },
        'stats': [
            {'label': 'Role', 'value': 'Student', 'subtext': 'active account'},
            {'label': 'Enrollment', 'value': '91/120', 'subtext': 'credits completed'},
            {'label': 'GPA', 'value': '3.84', 'subtext': 'out of 4.00'},
            {'label': 'Attendance', 'value': '96%', 'subtext': 'overall rate'},
        ],
        'actions': [
            {'title': 'View Transcript', 'description': 'See your academic records'},
            {'title': 'Meet Advisor', 'description': 'Schedule time with your advisor'},
            {'title': 'Grade Result', 'description': 'Check your grades and results'},
            {'title': 'Current Courses', 'description': 'View your enrolled courses'},
        ],
        'details': [
            ('Email', 'adaeze.nwosu@university.edu'),
            ('Department', 'Faculty of Computing'),
            ('Advisor', 'Dr. Sarah Okonkwo'),
            ('Expected Graduation', 'May 2027'),
        ],
    },
    'staff': {
        'label': 'Staff',
        'accent': '#1f936a',
        'subtitle': 'Teaching schedule, class oversight, and academic operations',
        'signin_help': 'Sign in to access the staff portal',
        'signup_help': 'Register a staff account for teaching and administrative services',
        'profile': {
            'name': 'Dr. Chinedu Eze',
            'identifier_label': 'Staff ID',
            'identifier': 'STF-2026-114',
            'summary': 'Department of Computer Science | Senior Lecturer',
            'note': 'Monitor course delivery, student performance, and faculty activities from one place.',
            'badge': 'Active Faculty · Semester Ready',
            'avatar': 'CE',
        },
        'stats': [
            {'label': 'Role', 'value': 'Staff', 'subtext': 'academic portal'},
            {'label': 'Courses', 'value': '4', 'subtext': 'assigned this term'},
            {'label': 'Advisees', 'value': '38', 'subtext': 'students assigned'},
            {'label': 'Attendance', 'value': '98%', 'subtext': 'lecture coverage'},
        ],
        'actions': [
            {'title': 'Course Manager', 'description': 'Update lecture materials and assessments'},
            {'title': 'Student Advising', 'description': 'View advisees and meeting requests'},
            {'title': 'Results Upload', 'description': 'Manage grading and publication'},
            {'title': 'Department Files', 'description': 'Access faculty resources quickly'},
        ],
        'details': [
            ('Email', 'chinedu.eze@university.edu'),
            ('Department', 'School of Engineering'),
            ('Office', 'Block C, Room 204'),
            ('Specialization', 'Cybersecurity and Data Privacy'),
        ],
    },
    'admin': {
        'label': 'Admin',
        'accent': '#5b7be3',
        'subtitle': 'Identity oversight, security analytics, and institution-wide controls',
        'signin_help': 'Sign in to access the admin security portal',
        'signup_help': 'Register an administrator account for security and system management',
        'profile': {
            'name': 'Maya Johnson',
            'identifier_label': 'Admin ID',
            'identifier': 'ADM-SEC-011',
            'summary': 'ICT | Security Operations Lead',
            'note': 'Manage authentication activity, security alerts, and behavioral biometric oversight across the platform.',
            'badge': 'Privileged Access · Security Team',
            'avatar': 'MJ',
        },
        'stats': [
            {'label': 'Role', 'value': 'Admin', 'subtext': 'security portal'},
            {'label': 'Users', 'value': '2,314', 'subtext': 'active accounts'},
            {'label': 'Alerts', 'value': '12', 'subtext': 'open today'},
            {'label': 'System Uptime', 'value': '99.9%', 'subtext': 'availability'},
        ],
        'actions': [
            {'title': 'Threat Review', 'description': 'Inspect flagged biometric mismatches'},
            {'title': 'User Access', 'description': 'Approve, suspend, or restore accounts'},
            {'title': 'Audit Trail', 'description': 'Review recent sign-in activity'},
            {'title': 'Policy Settings', 'description': 'Adjust verification requirements'},
        ],
        'details': [
            ('Email', 'maya.johnson@university.edu'),
            ('Office', 'ICT Security Operations'),
            ('Access Level', 'Full Administrative Control'),
            ('Incident Queue', '4 critical · 8 medium'),
        ],
    },
}


def get_role_content(role):
    """Return UI content for a role page."""
    return ROLE_PAGE_CONTENT[role]


def generate_user_identifier(role):
    """Generate a role-specific identifier for new users."""
    prefixes = {
        'student': 'STD',
        'staff': 'STF',
        'admin': 'ADM',
    }
    prefix = prefixes[role]
    year = datetime.utcnow().year
    next_index = 1

    while True:
        candidate = f'{prefix}-{year}-{next_index:04d}'
        if not User.query.filter_by(user_id=candidate).first():
            return candidate
        next_index += 1


def get_post_login_redirect(user):
    """Send authenticated users to the homepage for their role."""
    return url_for('role_homepage', role=user.role)


def set_authenticated_session(user):
    """Persist a successful login in the session."""
    session['user_id'] = user.user_id
    session['username'] = user.username
    session['role'] = user.role
    session['authenticated'] = True


def user_matches_role(user, role):
    """Ensure users only use the matching role portal."""
    return user is not None and user.role == role


def build_role_home_context(user):
    """Create homepage content from a real user record."""
    role_content = get_role_content(user.role)
    full_name = user.full_name or user.username
    avatar = ''.join(part[0] for part in full_name.split()[:2]).upper() or user.username[:2].upper()

    profile = dict(role_content['profile'])
    profile['name'] = full_name
    profile['identifier'] = user.user_id
    profile['summary'] = user.department or role_content['profile']['summary']
    profile['note'] = user.profile_note or role_content['profile']['note']
    profile['avatar'] = avatar

    fallback_department = next((value for label, value in role_content['details'] if label == 'Department'), role_content['profile']['summary'])
    details = [
        (profile['identifier_label'], user.user_id),
        ('Email', user.email),
        ('Department', user.department or fallback_department),
        ('Username', user.username),
        ('Created', user.created_at.strftime('%d %b %Y'))
    ]

    return {
        **role_content,
        'profile': profile,
        'details': details
    }


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='student')
    profile_note = db.Column(db.String(255), nullable=True)
    department = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class AuthenticationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    auth_type = db.Column(db.String(32))
    success = db.Column(db.Boolean, nullable=False)
    confidence_score = db.Column(db.Float, nullable=True)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    breach_suspected = db.Column(db.Boolean, default=False)
    details = db.Column(db.Text, nullable=True)


class KeystrokeProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), unique=True, nullable=False)
    sample_count = db.Column(db.Integer, default=0, nullable=False)
    profile_data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    token = db.Column(db.String(12), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def ensure_database_schema():
    """Add missing columns when an older SQLite database already exists."""
    inspector = inspect(db.engine)
    user_columns = {column['name'] for column in inspector.get_columns('user')}
    log_columns = {column['name'] for column in inspector.get_columns('authentication_log')}

    if 'full_name' not in user_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN full_name VARCHAR(120)"))
    if 'profile_note' not in user_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN profile_note VARCHAR(255)"))
    if 'department' not in user_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN department VARCHAR(120)"))
    if 'breach_suspected' not in log_columns:
        db.session.execute(
            text("ALTER TABLE authentication_log ADD COLUMN breach_suspected BOOLEAN DEFAULT 0")
        )
    if 'details' not in log_columns:
        db.session.execute(
            text("ALTER TABLE authentication_log ADD COLUMN details TEXT")
        )
    db.session.commit()


def load_profile_samples(profile):
    """Read stored enrollment samples."""
    if not profile or not profile.profile_data:
        return []

    try:
        payload = json.loads(profile.profile_data)
    except json.JSONDecodeError:
        return []

    samples = payload.get('samples', [])
    return samples if isinstance(samples, list) else []


def save_profile_samples(profile, samples):
    """Persist normalized enrollment samples."""
    profile.profile_data = json.dumps({'samples': samples})
    profile.sample_count = len(samples)
    profile.updated_at = datetime.utcnow()


def upsert_keystroke_profile(user_id, features):
    """Save the newest keystroke sample for a user."""
    profile = KeystrokeProfile.query.filter_by(user_id=user_id).first()
    if profile is None:
        profile = KeystrokeProfile(user_id=user_id, profile_data=json.dumps({'samples': []}))
        db.session.add(profile)

    samples = load_profile_samples(profile)
    samples.append(features)
    samples = samples[-8:]
    save_profile_samples(profile, samples)
    return profile


def delete_keystroke_profile(user_id):
    """Remove a user's enrolled typing profile."""
    profile = KeystrokeProfile.query.filter_by(user_id=user_id).first()
    if profile is not None:
        db.session.delete(profile)
    return profile is not None


def generate_reset_token():
    """Create a short numeric token for email delivery."""
    return f"{secrets.randbelow(1_000_000):06d}"


def send_reset_email(user, token):
    """Attempt to send a reset token email using configured SMTP settings."""
    smtp_host = os.getenv('SMART_MFA_SMTP_HOST')
    smtp_port = int(os.getenv('SMART_MFA_SMTP_PORT', '587'))
    smtp_user = os.getenv('SMART_MFA_SMTP_USER')
    smtp_password = os.getenv('SMART_MFA_SMTP_PASSWORD')
    sender = os.getenv('SMART_MFA_EMAIL_FROM', smtp_user or 'no-reply@smartmfa.local')

    message = EmailMessage()
    message['Subject'] = 'Smart MFA keystroke reset token'
    message['From'] = sender
    message['To'] = user.email
    message.set_content(
        f"Hello {user.full_name or user.username},\n\n"
        f"Use this token to reset your keystroke profile and password: {token}\n"
        f"This token expires in {RESET_TOKEN_EXPIRY_MINUTES} minutes.\n\n"
        "If you did not request this action, please contact your administrator."
    )

    if not smtp_host or not smtp_user or not smtp_password:
        print(
            f"[smart-mfa] SMTP is not configured. Reset token for {user.email}: {token}",
            file=sys.stderr
        )
        return False

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)
    return True


def create_password_reset_token(user):
    """Create and persist a reset token for a user."""
    PasswordResetToken.query.filter_by(user_id=user.user_id, used=False).update({'used': True})
    token_value = generate_reset_token()
    token = PasswordResetToken(
        user_id=user.user_id,
        token=token_value,
        role=user.role,
        expires_at=datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)
    )
    db.session.add(token)
    return token


def get_valid_password_reset_token(role, token_value):
    """Return a valid reset token record when present."""
    if not token_value:
        return None

    return PasswordResetToken.query.filter_by(
        role=role,
        token=token_value,
        used=False
    ).filter(PasswordResetToken.expires_at >= datetime.utcnow()).first()


def summarize_vector(values):
    """Return summary stats for an enrolled vector position."""
    mean_value = sum(values) / len(values)
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return mean_value, variance ** 0.5


def is_biometric_character_key(key_value):
    """Keep only printable single-character keys for keystroke biometrics."""
    return isinstance(key_value, str) and len(key_value) == 1


def compare_sequence_vectors(samples, features, vector_key):
    """Compare current dwell/flight sequences against enrolled sequences."""
    sample_vector = features.get(vector_key, [])
    enrolled_vectors = [sample.get(vector_key, []) for sample in samples]
    matching_vectors = [vector for vector in enrolled_vectors if len(vector) == len(sample_vector)]

    if not sample_vector or not matching_vectors:
        return 0.0

    per_sample_distances = []

    for index in range(len(sample_vector)):
        enrolled_position_values = [vector[index] for vector in matching_vectors]
        mean_value, std_value = summarize_vector(enrolled_position_values)
        tolerance = max(std_value * 2.8, abs(mean_value) * 0.24, VECTOR_TOLERANCE_FLOOR_MS * 1.35)
        position_distance = abs(sample_vector[index] - mean_value) / tolerance
        per_sample_distances.append(position_distance)

    return sum(per_sample_distances) / len(per_sample_distances)


def calculate_profile_scores(samples, features):
    """Compute aggregate, sequence, and total distances for one feature sample."""
    keys = [
        'dwell_mean',
        'dwell_std',
        'dwell_median',
        'flight_mean',
        'flight_std',
        'flight_median',
        'typing_speed_cpm',
        'total_duration_ms'
    ]
    normalized_distances = []

    for key in keys:
        values = [sample.get(key, 0.0) for sample in samples]
        mean_value = sum(values) / len(values)
        variance = sum((value - mean_value) ** 2 for value in values) / len(values)
        std_value = variance ** 0.5
        tolerance = max(std_value * 2.2, abs(mean_value) * 0.14, 1.0)
        distance = abs(features.get(key, 0.0) - mean_value) / tolerance
        normalized_distances.append(distance)

    aggregate_distance = sum(normalized_distances) / len(normalized_distances)
    dwell_sequence_distance = compare_sequence_vectors(samples, features, 'dwell_vector')
    flight_sequence_distance = compare_sequence_vectors(samples, features, 'flight_vector')
    sequence_distance = (dwell_sequence_distance * 0.55) + (flight_sequence_distance * 0.45)
    total_distance = (aggregate_distance * 0.5) + (sequence_distance * 0.5)

    return {
        'aggregate_distance': aggregate_distance,
        'sequence_distance': sequence_distance,
        'total_distance': total_distance
    }


def compute_adaptive_thresholds(samples):
    """Derive per-user thresholds from enrolled sample variation."""
    fallback = {
        'aggregate_threshold': 1.2,
        'sequence_threshold': 1.15,
        'total_threshold': 1.1,
        'duration_threshold': None
    }

    if len(samples) < 4:
        return fallback

    aggregate_scores = []
    sequence_scores = []
    total_scores = []
    duration_values = [sample.get('total_duration_ms', 0.0) for sample in samples]

    for index, sample in enumerate(samples):
        comparison_pool = samples[:index] + samples[index + 1:]
        if len(comparison_pool) < 2:
            continue

        scores = calculate_profile_scores(comparison_pool, sample)
        aggregate_scores.append(scores['aggregate_distance'])
        sequence_scores.append(scores['sequence_distance'])
        total_scores.append(scores['total_distance'])

    def adaptive_limit(values, floor):
        if not values:
            return floor
        mean_value, std_value = summarize_vector(values)
        return max(floor, mean_value + (std_value * 2.5))

    duration_mean, duration_std = summarize_vector(duration_values)
    return {
        'aggregate_threshold': adaptive_limit(aggregate_scores, fallback['aggregate_threshold']),
        'sequence_threshold': adaptive_limit(sequence_scores, fallback['sequence_threshold']),
        'total_threshold': adaptive_limit(total_scores, fallback['total_threshold']),
        'duration_threshold': max(350.0, duration_mean * 0.35, duration_std * 3.0)
    }


def compare_against_profile(profile, features):
    """Compare live features against the enrolled keystroke profile."""
    samples = load_profile_samples(profile)
    if len(samples) < MIN_ENROLLMENT_SAMPLES:
        return {
            'is_match': True,
            'confidence': 0.55,
            'reason': 'Enrollment in progress'
        }

    scores = calculate_profile_scores(samples, features)
    aggregate_distance = scores['aggregate_distance']
    sequence_distance = scores['sequence_distance']
    total_distance = scores['total_distance']
    confidence = max(0.0, min(1.0, 1.0 - (total_distance / 2.2)))
    thresholds = compute_adaptive_thresholds(samples)

    is_match = (
        aggregate_distance <= thresholds['aggregate_threshold'] and
        sequence_distance <= thresholds['sequence_threshold'] and
        total_distance <= thresholds['total_threshold']
    )

    average_duration = sum(sample.get('total_duration_ms', 0.0) for sample in samples) / len(samples)
    if thresholds['duration_threshold'] is not None and abs(features.get('total_duration_ms', 0.0) - average_duration) > thresholds['duration_threshold']:
        is_match = False

    reason = 'Keystroke pattern matched enrolled profile'
    if not is_match:
        reason = (
            f'Keystroke mismatch detected (aggregate={aggregate_distance:.2f}, '
            f'sequence={sequence_distance:.2f}, total={total_distance:.2f})'
        )

    return {
        'is_match': is_match,
        'confidence': round(confidence, 4),
        'reason': reason,
        'aggregate_distance': round(aggregate_distance, 4),
        'sequence_distance': round(sequence_distance, 4),
        'total_distance': round(total_distance, 4),
        'thresholds': {
            'aggregate': round(thresholds['aggregate_threshold'], 4),
            'sequence': round(thresholds['sequence_threshold'], 4),
            'total': round(thresholds['total_threshold'], 4)
        }
    }


def filter_password_keystrokes(keystroke_events):
    """Keep only complete password-field key events."""
    filtered_events = []

    for event in keystroke_events:
        if event.get('field') != 'password':
            continue
        if event.get('press_time') is None or event.get('release_time') is None:
            continue
        if not is_biometric_character_key(event.get('key')):
            continue

        filtered_events.append({
            'key': event.get('key'),
            'press_time': event.get('press_time'),
            'release_time': event.get('release_time')
        })

    return filtered_events


def extract_login_keystroke_features(keystroke_events):
    """Extract normalized features from login typing events."""
    password_events = filter_password_keystrokes(keystroke_events)
    if len(password_events) < MIN_KEYSTROKE_EVENTS:
        return None
    features = feature_extractor.extract_keystroke_features(password_events)
    if features is None:
        return None

    dwell_vector = []
    flight_vector = []
    press_interval_vector = []

    for index, event in enumerate(password_events):
        dwell_vector.append(max(0, event['release_time'] - event['press_time']))

        if index < len(password_events) - 1:
            next_event = password_events[index + 1]
            flight_vector.append(max(0, next_event['press_time'] - event['release_time']))
            press_interval_vector.append(max(0, next_event['press_time'] - event['press_time']))

    total_duration = password_events[-1]['release_time'] - password_events[0]['press_time']
    features.update({
        'total_duration_ms': float(total_duration),
        'press_interval_mean': float(sum(press_interval_vector) / len(press_interval_vector)) if press_interval_vector else 0.0,
        'dwell_vector': dwell_vector,
        'flight_vector': flight_vector,
        'press_interval_vector': press_interval_vector
    })
    return features


def log_authentication_attempt(user_id, auth_type, success, confidence=None, breach_suspected=False, details=None):
    """Create a log entry that can also be surfaced in the admin portal."""
    db.session.add(AuthenticationLog(
        user_id=user_id,
        auth_type=auth_type,
        success=success,
        confidence_score=confidence,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:200],
        breach_suspected=breach_suspected,
        details=details
    ))


def build_admin_dashboard_context(search_term=''):
    """Create admin homepage metrics, login session view, and user table data."""
    successful_auths = AuthenticationLog.query.filter_by(
        auth_type='behavioral',
        success=True
    ).count()
    failed_auths = AuthenticationLog.query.filter(
        ((AuthenticationLog.auth_type == 'behavioral') & (AuthenticationLog.success.is_(False))) |
        ((AuthenticationLog.auth_type == 'password') & (AuthenticationLog.success.is_(False)))
    ).count()
    total_auth_attempts = successful_auths + failed_auths
    login_logs = AuthenticationLog.query.filter(
        AuthenticationLog.auth_type.in_(['password', 'behavioral'])
    ).order_by(
        AuthenticationLog.timestamp.desc()
    ).limit(12).all()
    usernames_by_user_id = {
        user.user_id: user.username
        for user in User.query.filter(
            User.user_id.in_([log.user_id for log in login_logs])
        ).all()
    }
    login_sessions = [
        {
            'user_id': log.user_id,
            'username': usernames_by_user_id.get(log.user_id, 'Unknown'),
            'timestamp': log.timestamp,
            'auth_type': log.auth_type,
            'success': log.success,
            'ip_address': log.ip_address
        }
        for log in login_logs
    ]

    user_query = User.query.order_by(User.created_at.desc())
    if search_term:
        like_term = f'%{search_term}%'
        user_query = user_query.filter(
            (User.user_id.ilike(like_term)) |
            (User.username.ilike(like_term)) |
            (User.email.ilike(like_term)) |
            (User.role.ilike(like_term))
        )

    users = user_query.all()
    return {
        'stats': {
            'total_users': User.query.count(),
            'total_attempts': total_auth_attempts,
            'successful': successful_auths,
            'failed': failed_auths,
            'success_rate': (successful_auths / total_auth_attempts * 100) if total_auth_attempts > 0 else 0
        },
        'login_sessions': login_sessions,
        'users': users,
        'search_term': search_term
    }


def authenticate_user_with_keystrokes(user, password, keystroke_events):
    """Run password plus keystroke verification for a single user."""
    if not user or not check_password_hash(user.password_hash, password):
        if user:
            log_authentication_attempt(
                user.user_id,
                'password',
                False,
                details='Password verification failed'
            )
            db.session.commit()
        return {
            'success': False,
            'status': 401,
            'payload': {'success': False, 'message': 'Invalid username or password'}
        }

    if not user.is_active:
        return {
            'success': False,
            'status': 403,
            'payload': {'success': False, 'message': 'Account is disabled'}
        }

    keystroke_features = extract_login_keystroke_features(keystroke_events)
    if keystroke_features is None:
        return {
            'success': False,
            'status': 400,
            'payload': {
                'success': False,
                'message': 'Keystroke sample was too short. Please type your password naturally so the system can verify your typing pattern.'
            }
        }

    log_authentication_attempt(
        user.user_id,
        'password',
        True,
        details='Password verified successfully'
    )

    existing_profile = KeystrokeProfile.query.filter_by(user_id=user.user_id).first()
    stored_samples = load_profile_samples(existing_profile)

    if len(stored_samples) < MIN_ENROLLMENT_SAMPLES:
        profile = upsert_keystroke_profile(user.user_id, keystroke_features)
        log_authentication_attempt(
            user.user_id,
            'behavioral',
            True,
            confidence=0.6,
            details=f'Enrollment sample {profile.sample_count}/{MIN_ENROLLMENT_SAMPLES} captured'
        )

        set_authenticated_session(user)
        db.session.commit()

        enrollment_complete = profile.sample_count >= MIN_ENROLLMENT_SAMPLES
        message = (
            'Password and keystroke profile verified successfully.'
            if enrollment_complete else
            f'Login successful. Keystroke enrollment sample {profile.sample_count} of {MIN_ENROLLMENT_SAMPLES} saved.'
        )

        return {
            'success': True,
            'status': 200,
            'payload': {
                'success': True,
                'message': message,
                'enrollment_in_progress': not enrollment_complete,
                'samples_collected': profile.sample_count,
                'samples_required': MIN_ENROLLMENT_SAMPLES,
                'redirect': get_post_login_redirect(user)
            }
        }

    comparison = compare_against_profile(existing_profile, keystroke_features)

    if comparison['is_match']:
        profile = existing_profile
        if comparison['confidence'] >= 0.72:
            profile = upsert_keystroke_profile(user.user_id, keystroke_features)
        log_authentication_attempt(
            user.user_id,
            'behavioral',
            True,
            confidence=comparison['confidence'],
            details=f"{comparison['reason']}. Stored samples: {profile.sample_count if profile else len(stored_samples)}"
        )

        set_authenticated_session(user)
        db.session.commit()

        return {
            'success': True,
            'status': 200,
            'payload': {
                'success': True,
                'message': 'Password and keystroke profile verified successfully.',
                'confidence': comparison['confidence'],
                'details': comparison['reason'],
                'redirect': get_post_login_redirect(user)
            }
        }

    log_authentication_attempt(
        user.user_id,
        'behavioral',
        False,
        confidence=comparison['confidence'],
        breach_suspected=True,
        details='Possible breach detected: correct password but keystroke profile mismatch'
    )
    db.session.commit()
    session.clear()

    return {
        'success': False,
        'status': 403,
        'payload': {
            'success': False,
            'message': 'Possible breach detected. The password was correct, but the typing pattern did not match the enrolled user.',
            'confidence': comparison['confidence'],
            'details': comparison['reason'],
            'possible_breach': True
        }
    }


@app.route('/api/reset_keystroke_profile', methods=['POST'])
def reset_keystroke_profile():
    """Reset a user's keystroke profile for demonstration or re-enrollment."""
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({
            'success': False,
            'message': 'Invalid username or password'
        }), 401

    deleted = delete_keystroke_profile(user.user_id)
    log_authentication_attempt(
        user.user_id,
        'profile_reset',
        True,
        details='Keystroke profile reset for re-enrollment'
    )
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Keystroke profile reset. Log in naturally three times to enroll a fresh typing profile.',
        'profile_cleared': deleted
    })


@app.route('/api/<role>/request-keystroke-reset', methods=['POST'])
def request_keystroke_reset(role):
    """Email a reset token when a user needs to rebuild their keystroke profile."""
    if role not in ROLE_PAGE_CONTENT:
        return jsonify({'success': False, 'message': 'Invalid role'}), 404

    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    user = User.query.filter_by(username=username, role=role).first()

    if not user:
        return jsonify({
            'success': True,
            'message': 'If the account exists, a reset token has been sent to the registered email address.',
            'redirect': url_for('reset_token_page', role=role)
        })

    token = create_password_reset_token(user)
    email_sent = False
    try:
        email_sent = send_reset_email(user, token.token)
    except Exception as error:
        print(f'[smart-mfa] Failed to send reset email: {error}', file=sys.stderr)

    log_authentication_attempt(
        user.user_id,
        'keystroke_reset_requested',
        True,
        details='Reset token issued for keystroke mismatch recovery'
    )
    db.session.commit()

    message = (
        'A reset token has been sent to the registered email address.'
        if email_sent else
        'A reset token was generated. SMTP is not configured, so the token was logged on the server console instead of being emailed.'
    )
    return jsonify({
        'success': True,
        'message': message,
        'redirect': url_for('reset_token_page', role=role)
    })


@app.route('/reset/<role>/verify-token', methods=['GET'])
def reset_token_page(role):
    """Render the token verification page."""
    if role not in ROLE_PAGE_CONTENT:
        return redirect(url_for('login'))

    content = get_role_content(role)
    return render_template(
        'reset_token.html',
        role=role,
        accent=content['accent'],
        page_title=f'{content["label"]} Reset Verification'
    )


@app.route('/reset/<role>/new-password', methods=['GET'])
def reset_password_page(role):
    """Render the password and keystroke re-enrollment page."""
    if role not in ROLE_PAGE_CONTENT:
        return redirect(url_for('login'))

    token = request.args.get('token', '').strip()
    if not get_valid_password_reset_token(role, token):
        return redirect(url_for('reset_token_page', role=role))

    content = get_role_content(role)
    return render_template(
        'reset_password.html',
        role=role,
        accent=content['accent'],
        token=token,
        page_title=f'{content["label"]} New Password'
    )


@app.route('/api/<role>/verify-reset-token', methods=['POST'])
def verify_reset_token(role):
    """Verify a reset token before allowing password reset."""
    if role not in ROLE_PAGE_CONTENT:
        return jsonify({'success': False, 'message': 'Invalid role'}), 404

    data = request.get_json() or {}
    token_value = (data.get('token') or '').strip()
    token = get_valid_password_reset_token(role, token_value)

    if not token:
        return jsonify({'success': False, 'message': 'Invalid or expired token.'}), 400

    return jsonify({
        'success': True,
        'message': 'Token verified successfully.',
        'redirect': url_for('reset_password_page', role=role, token=token.token)
    })


@app.route('/api/<role>/complete-reset', methods=['POST'])
def complete_reset(role):
    """Save a new password and clear the keystroke profile for fresh login enrollment."""
    if role not in ROLE_PAGE_CONTENT:
        return jsonify({'success': False, 'message': 'Invalid role'}), 404

    data = request.get_json() or {}
    token_value = (data.get('token') or '').strip()
    password_one = data.get('password_one') or ''
    password_two = data.get('password_two') or ''

    token = get_valid_password_reset_token(role, token_value)
    if not token:
        return jsonify({'success': False, 'message': 'Invalid or expired token.'}), 400

    if not password_one or not password_two:
        return jsonify({'success': False, 'message': 'Enter the new password in both fields.'}), 400
    if len(password_one) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters long.'}), 400
    if password_one != password_two:
        return jsonify({'success': False, 'message': 'Both password entries must match.'}), 400

    user = User.query.filter_by(user_id=token.user_id, role=role).first()
    if not user:
        return jsonify({'success': False, 'message': 'User account not found.'}), 404

    user.password_hash = generate_password_hash(password_one)
    delete_keystroke_profile(user.user_id)
    token.used = True

    log_authentication_attempt(
        user.user_id,
        'password_reset',
        True,
        details='Password reset completed and keystroke enrollment cleared for fresh login enrollment'
    )
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Password updated successfully. Keystroke enrollment will restart and complete after {MIN_ENROLLMENT_SAMPLES} successful logins.',
        'redirect': url_for('role_signin', role=role)
    })


@app.route('/api/<role>/signup', methods=['POST'])
def api_role_signup(role):
    """Create a new user for a role-specific portal."""
    if role not in ROLE_PAGE_CONTENT:
        return jsonify({'success': False, 'message': 'Invalid role'}), 404

    data = request.get_json() or {}
    full_name = (data.get('full_name') or '').strip()
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    confirm_password = data.get('confirm_password') or ''

    if not full_name or not username or not email or not password:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400
    if password != confirm_password:
        return jsonify({'success': False, 'message': 'Passwords do not match.'}), 400
    if len(password) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters long.'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Username is already in use.'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email is already registered.'}), 409

    role_content = get_role_content(role)
    user = User(
        user_id=generate_user_identifier(role),
        username=username,
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
        department=role_content['profile']['summary'],
        profile_note=role_content['profile']['note']
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'This username, email, or generated user ID is already in use. Please try a different value.'
        }), 409

    return jsonify({
        'success': True,
        'message': f'{role_content["label"]} account created successfully. Sign in and complete keystroke enrollment.',
        'redirect': url_for('role_signin', role=role)
    })


@app.route('/api/<role>/signin', methods=['POST'])
def api_role_signin(role):
    """Authenticate a user against the selected role portal."""
    if role not in ROLE_PAGE_CONTENT:
        return jsonify({'success': False, 'message': 'Invalid role'}), 404

    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    keystroke_events = data.get('keystroke_events', [])

    user = User.query.filter_by(username=username).first()
    if user and user.role != role:
        return jsonify({
            'success': False,
            'message': f'This account belongs to the {user.role} portal. Please sign in through the correct page.'
        }), 403

    result = authenticate_user_with_keystrokes(user, password, keystroke_events)
    return jsonify(result['payload']), result['status']


with app.app_context():
    db.create_all()
    ensure_database_schema()

    if os.environ.get('VERCEL') or User.query.count() == 0:
        demo_users = [
            {
                'user_id': 'user_000',
                'username': 'john.doe',
                'full_name': 'John Doe',
                'email': 'john@university.edu',
                'password': 'password123',
                'role': 'student',
                'department': 'Computer Science | 200 Level',
                'profile_note': 'Review your academic summary, current courses, and enrollment details for Spring 2026.'
            },
            {
                'user_id': 'user_001',
                'username': 'jane.smith',
                'full_name': 'Jane Smith',
                'email': 'jane@university.edu',
                'password': 'password123',
                'role': 'student',
                'department': 'Information Systems | 300 Level',
                'profile_note': 'Track your coursework, semester registration, and academic performance.'
            },
            {
                'user_id': 'user_002',
                'username': 'admin',
                'full_name': 'System Admin',
                'email': 'admin@university.edu',
                'password': 'admin123',
                'role': 'admin',
                'department': 'ICT | Security Operations',
                'profile_note': 'Manage authentication activity, security alerts, and behavioral biometric oversight across the platform.'
            },
            {
                'user_id': 'user_003',
                'username': 'staff',
                'full_name': 'Demo Staff',
                'email': 'staff@university.edu',
                'password': 'staff123',
                'role': 'staff',
                'department': 'Department of Computer Science | Lecturer',
                'profile_note': 'Manage courses, advise students, and review academic activity.'
            },
        ]

        for user_data in demo_users:
            db.session.add(User(
                user_id=user_data['user_id'],
                username=user_data['username'],
                full_name=user_data['full_name'],
                email=user_data['email'],
                password_hash=generate_password_hash(user_data['password']),
                role=user_data['role'],
                department=user_data['department'],
                profile_note=user_data['profile_note']
            ))

        db.session.commit()
        print('Created demo users')

    for user in User.query.all():
        updates_made = False
        if not user.full_name:
            user.full_name = user.username.replace('.', ' ').title()
            updates_made = True
        if not user.department:
            user.department = get_role_content(user.role)['profile']['summary']
            updates_made = True
        if not user.profile_note:
            user.profile_note = get_role_content(user.role)['profile']['note']
            updates_made = True
        if updates_made:
            db.session.add(user)
    db.session.commit()


@app.route('/')
def index():
    """Landing page with all login options."""
    return render_template('index.html')


@app.route('/login', methods=['GET'])
def login():
    """Legacy login route now points to the landing page."""
    return redirect(url_for('index'))


@app.route('/<role>/signin', methods=['GET'])
def role_signin(role):
    """Role-specific sign-in page."""
    if role not in ROLE_PAGE_CONTENT:
        return redirect(url_for('login'))

    content = get_role_content(role)
    return render_template(
        'role_auth.html',
        role=role,
        mode='signin',
        page_title=f"{content['label']} Sign In",
        eyebrow=f"{content['label'].upper()} LOGIN",
        headline=f"{content['label']} Login",
        subheadline=content['signin_help'],
        accent=content['accent'],
        links=[
            {'label': 'Create account', 'href': url_for('role_signup', role=role)},
            {'label': 'Back home', 'href': url_for('index')},
        ]
    )


@app.route('/<role>/signup', methods=['GET'])
def role_signup(role):
    """Role-specific sign-up page."""
    if role not in ROLE_PAGE_CONTENT:
        return redirect(url_for('login'))

    content = get_role_content(role)
    return render_template(
        'role_auth.html',
        role=role,
        mode='signup',
        page_title=f"{content['label']} Sign Up",
        eyebrow=f"{content['label'].upper()} REGISTRATION",
        headline=f"{content['label']} Sign Up",
        subheadline=content['signup_help'],
        accent=content['accent'],
        links=[
            {'label': 'Already have an account?', 'href': url_for('role_signin', role=role)},
            {'label': 'Back home', 'href': url_for('index')},
        ]
    )


@app.route('/<role>/homepage', methods=['GET'])
def role_homepage(role):
    """Role-specific homepage mockup."""
    if role not in ROLE_PAGE_CONTENT:
        return redirect(url_for('login'))
    if 'user_id' not in session or not session.get('authenticated'):
        return redirect(url_for('role_signin', role=role))

    user = User.query.filter_by(user_id=session['user_id']).first()
    if not user_matches_role(user, role):
        return redirect(get_post_login_redirect(user) if user else url_for('login'))

    content = build_role_home_context(user)
    admin_dashboard = None
    if role == 'admin':
        admin_dashboard = build_admin_dashboard_context(request.args.get('search', '').strip())
    return render_template(
        'role_home.html',
        role=role,
        accent=content['accent'],
        content=content,
        admin_dashboard=admin_dashboard
    )


@app.route('/api/login', methods=['POST'])
def api_login():
    """Handle password verification and keystroke biometrics during login."""
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    keystroke_events = data.get('keystroke_events', [])

    user = User.query.filter_by(username=username).first()
    result = authenticate_user_with_keystrokes(user, password, keystroke_events)
    return jsonify(result['payload']), result['status']


@app.route('/api/verify_behavioral', methods=['POST'])
def verify_behavioral():
    """Verify behavioral biometrics during an active session."""
    if 'user_id' not in session or not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json() or {}
    keystroke_events = data.get('keystroke_events', [])
    user_id = session['user_id']

    keystroke_features = extract_login_keystroke_features(keystroke_events)
    if keystroke_features is None:
        return jsonify({
            'success': False,
            'message': 'Insufficient keystroke data for verification.'
        }), 400

    profile = KeystrokeProfile.query.filter_by(user_id=user_id).first()
    comparison = compare_against_profile(profile, keystroke_features)

    log_authentication_attempt(
        user_id,
        'continuous_behavioral',
        comparison['is_match'],
        confidence=comparison['confidence'],
        breach_suspected=not comparison['is_match'],
        details=comparison['reason']
    )
    db.session.commit()

    if comparison['is_match']:
        return jsonify({
            'success': True,
            'behavioral_verified': True,
            'message': 'Behavior verified',
            'confidence': comparison['confidence']
        })

    session.clear()
    return jsonify({
        'success': False,
        'behavioral_verified': False,
        'message': 'Possible breach detected during continuous verification.',
        'confidence': comparison['confidence']
    }), 403


@app.route('/dashboard')
def dashboard():
    """User dashboard."""
    if 'user_id' not in session or not session.get('authenticated'):
        return redirect(url_for('login'))

    user = User.query.filter_by(user_id=session['user_id']).first()
    if user:
        return redirect(get_post_login_redirect(user))
    return redirect(url_for('login'))


@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout user."""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@app.route('/admin/users/<user_id>/update', methods=['POST'])
def admin_update_user(user_id):
    """Allow admins to edit passwords and block or unblock accounts."""
    if 'user_id' not in session or not session.get('authenticated'):
        return redirect(url_for('role_signin', role='admin'))

    admin_user = User.query.filter_by(user_id=session['user_id']).first()
    if not admin_user or admin_user.role != 'admin':
        return 'Access denied', 403

    target_user = User.query.filter_by(user_id=user_id).first_or_404()
    if target_user.user_id == admin_user.user_id:
        return redirect(url_for('role_homepage', role='admin', search=request.args.get('search', '')))

    target_user.role = (request.form.get('role') or target_user.role).strip().lower()
    if target_user.role not in ROLE_PAGE_CONTENT:
        target_user.role = 'student'

    target_user.full_name = (request.form.get('full_name') or target_user.full_name).strip()
    target_user.email = (request.form.get('email') or target_user.email).strip().lower()
    target_user.is_active = request.form.get('status') == 'active'

    new_password = (request.form.get('new_password') or '').strip()
    if new_password:
        target_user.password_hash = generate_password_hash(new_password)
        delete_keystroke_profile(target_user.user_id)

    db.session.add(target_user)
    db.session.commit()
    return redirect(url_for('role_homepage', role='admin', search=request.args.get('search', '')))


@app.route('/admin/users/<user_id>/delete', methods=['POST'])
def admin_delete_user(user_id):
    """Allow admins to delete accounts."""
    if 'user_id' not in session or not session.get('authenticated'):
        return redirect(url_for('role_signin', role='admin'))

    admin_user = User.query.filter_by(user_id=session['user_id']).first()
    if not admin_user or admin_user.role != 'admin':
        return 'Access denied', 403

    target_user = User.query.filter_by(user_id=user_id).first_or_404()
    if target_user.user_id == admin_user.user_id:
        return redirect(url_for('role_homepage', role='admin', search=request.args.get('search', '')))

    KeystrokeProfile.query.filter_by(user_id=target_user.user_id).delete()
    PasswordResetToken.query.filter_by(user_id=target_user.user_id).delete()
    AuthenticationLog.query.filter_by(user_id=target_user.user_id).delete()
    db.session.delete(target_user)
    db.session.commit()
    return redirect(url_for('role_homepage', role='admin', search=request.args.get('search', '')))


@app.route('/admin/stats')
def admin_stats():
    """Admin statistics page."""
    if 'user_id' not in session or not session.get('authenticated'):
        return redirect(url_for('login'))

    user = User.query.filter_by(user_id=session['user_id']).first()
    if user.role != 'admin':
        return 'Access denied', 403

    successful_auths = AuthenticationLog.query.filter_by(
        auth_type='behavioral',
        success=True
    ).count()
    failed_auths = AuthenticationLog.query.filter(
        ((AuthenticationLog.auth_type == 'behavioral') & (AuthenticationLog.success.is_(False))) |
        ((AuthenticationLog.auth_type == 'password') & (AuthenticationLog.success.is_(False)))
    ).count()
    total_auth_attempts = successful_auths + failed_auths
    recent_logs = AuthenticationLog.query.order_by(
        AuthenticationLog.timestamp.desc()
    ).limit(20).all()
    suspected_breaches = AuthenticationLog.query.filter(
        AuthenticationLog.breach_suspected.is_(True)
    ).order_by(AuthenticationLog.timestamp.desc()).limit(20).all()

    stats = {
        'total_users': User.query.count(),
        'total_attempts': total_auth_attempts,
        'successful': successful_auths,
        'failed': failed_auths,
        'success_rate': (successful_auths / total_auth_attempts * 100) if total_auth_attempts > 0 else 0,
        'suspected_breaches': AuthenticationLog.query.filter(
            AuthenticationLog.breach_suspected.is_(True)
        ).count()
    }

    return render_template('admin_stats.html', stats=stats, logs=recent_logs, breaches=suspected_breaches)


if __name__ == '__main__':
    print('\n' + '=' * 70)
    print('SMART MULTI-FACTOR AUTHENTICATION SYSTEM')
    print('=' * 70)
    print('\nDemo Accounts:')
    print('  Student: john.doe / password123')
    print('  Student: jane.smith / password123')
    print('  Admin: admin / admin123')
    print('\nKeystroke enrollment note:')
    print(f'  The first {MIN_ENROLLMENT_SAMPLES} successful logins for a user build that user profile.')
    print('\nStarting server on http://127.0.0.1:5000')
    print('=' * 70 + '\n')

    app.run(debug=True, host='127.0.0.1', port=5000)
