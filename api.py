import gitlab
from datetime import datetime, timezone
from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required, current_user
from flask_dance.contrib.gitlab import gitlab as gitlab_dance

from extensions import db
from gitlab_utils import get_gitlab_client
from models import Project, Pipeline, PipelineJob, UserSelectedGroup
from sync import sync_pipelines

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/user/current')
@login_required
def api_current_user():
    return jsonify(current_user.to_dict())


@api_bp.route('/api/user/gitlab-token', methods=['POST'])
@login_required
def api_update_gitlab_token():
    try:
        data = request.get_json()
    except Exception as exc:
        return jsonify({'error': f'Invalid JSON: {exc}'}), 400

    token = data.get('token', '').strip()
    if not token:
        return jsonify({'error': 'Token is required'}), 400

    # Validate the token
    from gitlab_utils import validate_gitlab_token
    is_valid, error_msg = validate_gitlab_token(token)
    if not is_valid:
        return jsonify({'error': f'Invalid GitLab token: {error_msg}'}), 400

    # Update the user's token
    current_user.gitlab_token = token
    try:
        db.session.commit()
        return jsonify({'status': 'ok', 'message': 'GitLab token updated successfully'})
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('Failed to update GitLab token for user %s: %s', current_user.id, exc)
        return jsonify({'error': 'Failed to update token'}), 500


@api_bp.route('/api/user/groups', methods=['GET'])
@login_required
def api_get_user_groups():
    groups = UserSelectedGroup.query.filter_by(user_id=current_user.id).all()
    return jsonify([group.to_dict() for group in groups])


@api_bp.route('/api/user/groups', methods=['POST'])
@login_required
def api_add_user_group():
    try:
        data = request.get_json()
    except Exception as exc:
        return jsonify({'error': f'Invalid JSON: {exc}'}), 400

    group_identifier = data.get('group_id') or data.get('group_path')
    if not group_identifier:
        return jsonify({'error': 'Missing group_id or group_path'}), 400

    # Validate group_id if provided
    if data.get('group_id'):
        try:
            group_id_int = int(group_identifier)
            if group_id_int <= 0:
                return jsonify({'error': 'group_id must be a positive integer'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'group_id must be a valid integer'}), 400

    # Validate group_path if provided
    if data.get('group_path') and not isinstance(group_identifier, str):
        return jsonify({'error': 'group_path must be a string'}), 400

    gitlab_token = None
    if current_user.provider == 'gitlab' and gitlab_dance.authorized:
        gitlab_token = gitlab_dance.token['access_token']
    elif current_user.gitlab_token:
        gitlab_token = current_user.gitlab_token
    else:
        return jsonify({'error': 'GitLab authentication required. Please provide a GitLab token or login via GitLab OAuth'}), 403

    try:
        gl = get_gitlab_client(private_token=gitlab_token)

        if data.get('group_id'):
            group = gl.groups.get(int(group_identifier))
        else:
            group = gl.groups.get(group_identifier)

        group_data = group.asdict()
        existing = UserSelectedGroup.query.filter_by(user_id=current_user.id, group_id=group_data['id']).first()
        if existing:
            return jsonify({'error': 'Group already selected'}), 400

        group_obj = UserSelectedGroup(
            user_id=current_user.id,
            group_id=group_data['id'],
            group_name=group_data['name'],
            group_full_path=group_data['full_path'],
        )
        db.session.add(group_obj)
        db.session.commit()
        return jsonify(group_obj.to_dict())
    except gitlab.exceptions.GitlabAuthenticationError:
        current_app.logger.warning(
            'GitLab authentication failed for user %s with token starting with %s...',
            current_user.id,
            gitlab_token[:10] if gitlab_token else 'none',
        )
        return jsonify({'error': 'Invalid GitLab token. Please check your token and try again'}), 401
    except gitlab.exceptions.GitlabGetError as exc:
        if exc.response_code == 404:
            return jsonify({'error': 'Group not found or access denied'}), 404
        current_app.logger.warning('GitLab API error for user %s: %s', current_user.id, exc)
        return jsonify({'error': f'GitLab API error: {exc}'}), 400
    except Exception as exc:
        current_app.logger.error('Failed to add group %s for user %s: %s', group_identifier, current_user.id, exc)
        return jsonify({'error': 'Failed to add group. Please try again later.'}), 500


@api_bp.route('/api/user/groups/<int:group_id>', methods=['DELETE'])
@login_required
def api_remove_user_group(group_id):
    if group_id <= 0:
        return jsonify({'error': 'Invalid group ID'}), 400

    group = UserSelectedGroup.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    db.session.delete(group)
    db.session.commit()
    return jsonify({'status': 'ok'})


@api_bp.route('/api/projects')
@login_required
def api_projects():
    projects = Project.query.order_by(Project.name).all()
    return jsonify([p.to_dict() for p in projects])


@api_bp.route('/api/projects/<int:project_id>/pipelines')
@login_required
def api_pipelines(project_id):
    if project_id <= 0:
        return jsonify({'error': 'Invalid project ID'}), 400

    limit = request.args.get('limit', 10, type=int)
    if limit < 1 or limit > 100:
        limit = 10  # Default to 10 if invalid

    pipelines = (
        Pipeline.query
        .filter_by(project_id=project_id)
        .order_by(Pipeline.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify([p.to_dict() for p in pipelines])


@api_bp.route('/api/pipelines/<int:pipeline_id>/jobs')
@login_required
def api_jobs(pipeline_id):
    if pipeline_id <= 0:
        return jsonify({'error': 'Invalid pipeline ID'}), 400

    jobs = PipelineJob.query.filter_by(pipeline_id=pipeline_id).all()
    return jsonify([j.to_dict() for j in jobs])


@api_bp.route('/api/summary')
@login_required
def api_summary():
    total_projects = Project.query.count()
    from sqlalchemy import func

    sub = (
        db.session.query(
            Pipeline.project_id,
            func.max(Pipeline.created_at).label('max_created'),
        ).group_by(Pipeline.project_id).subquery()
    )
    latest = (
        db.session.query(Pipeline)
        .join(sub, (Pipeline.project_id == sub.c.project_id) &
                   (Pipeline.created_at == sub.c.max_created))
        .all()
    )
    status_counts = {}
    for p in latest:
        status_counts[p.status] = status_counts.get(p.status, 0) + 1

    return jsonify({
        'total_projects': total_projects,
        'status_counts': status_counts,
        'total_latest_pipelines': len(latest),
    })


@api_bp.route('/api/sync', methods=['POST'])
@login_required
def api_sync():
    sync_pipelines()
    return jsonify({'status': 'ok', 'synced_at': datetime.now(timezone.utc).isoformat()})


# Admin endpoints for user approval
@api_bp.route('/api/admin/users')
@login_required
def api_admin_users():
    # Only allow admin user to access this
    if current_user.username != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([user.to_dict() for user in users])


@api_bp.route('/api/admin/users/<int:user_id>/approve', methods=['POST'])
@login_required
def api_admin_approve_user(user_id):
    # Only allow admin user to access this
    if current_user.username != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    user.approved = True
    db.session.commit()
    return jsonify({'status': 'ok', 'user': user.to_dict()})


@api_bp.route('/api/admin/users/<int:user_id>/reject', methods=['POST'])
@login_required
def api_admin_reject_user(user_id):
    # Only allow admin user to access this
    if current_user.username != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'status': 'ok'})
