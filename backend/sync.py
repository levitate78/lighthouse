import logging
from datetime import datetime, timezone
from threading import Thread
from flask import current_app

from extensions import db, scheduler
from gitlab_utils import get_gitlab_client
from models import Project, Pipeline, PipelineJob, UserSelectedGroup

logger = logging.getLogger(__name__)


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _get_flask_app():
    try:
        return current_app._get_current_object()
    except RuntimeError:
        return scheduler.app


def _upsert_pipeline(pipe_data, project_id):
    pipeline = db.session.get(Pipeline, pipe_data["id"])
    if not pipeline:
        pipeline = Pipeline(id=pipe_data["id"])
        db.session.add(pipeline)
    pipeline.project_id = project_id
    pipeline.ref = pipe_data.get("ref", "")
    pipeline.sha = pipe_data.get("sha", "")
    pipeline.status = pipe_data.get("status", "unknown")
    pipeline.source = pipe_data.get("source", "")
    pipeline.web_url = pipe_data.get("web_url", "")
    pipeline.created_at = _parse_dt(pipe_data.get("created_at"))
    pipeline.updated_at = _parse_dt(pipe_data.get("updated_at"))
    pipeline.started_at = _parse_dt(pipe_data.get("started_at"))
    pipeline.finished_at = _parse_dt(pipe_data.get("finished_at"))
    pipeline.duration = pipe_data.get("duration")
    pipeline.queued_duration = pipe_data.get("queued_duration")
    return pipeline


def _sync_jobs_for_pipeline(project_id, pipeline_id, gl):
    jobs = (
        gl.projects.get(project_id).pipelines.get(pipeline_id).jobs.list(get_all=True)
    )
    PipelineJob.query.filter_by(pipeline_id=pipeline_id).delete()
    for job in jobs:
        job_data = job.asdict()
        job_obj = PipelineJob(
            id=job_data["id"],
            pipeline_id=pipeline_id,
            name=job_data.get("name", ""),
            stage=job_data.get("stage", ""),
            status=job_data.get("status", "unknown"),
            web_url=job_data.get("web_url", ""),
            duration=job_data.get("duration"),
            started_at=_parse_dt(job_data.get("started_at")),
            finished_at=_parse_dt(job_data.get("finished_at")),
            runner_name=job_data.get("runner", {}).get("description", "")
            if job_data.get("runner")
            else "",
        )
        db.session.add(job_obj)


def _background_sync_older_pipelines(group_ids):
    app = _get_flask_app()
    if app is None:
        return

    with app.app_context():
        gl = get_gitlab_client()

        for group_id in group_ids:
            try:
                group = gl.groups.get(group_id)
                projects = group.projects.list(get_all=True)

                for proj in projects:
                    proj_data = proj.asdict()
                    project = db.session.get(Project, proj_data["id"])
                    if not project:
                        continue

                    page = 2
                    while True:
                        pipelines = gl.projects.get(proj_data["id"]).pipelines.list(
                            per_page=10, page=page, get_all=False
                        )
                        if not pipelines:
                            break

                        for pipe in pipelines:
                            pipe_data = pipe.asdict()
                            _upsert_pipeline(pipe_data, proj_data["id"])
                        db.session.commit()
                        page += 1
            except Exception as exc:
                logger.warning(
                    "Background sync failed for group %s: %s",
                    group_id,
                    exc,
                )
        db.session.remove()


def _start_background_sync(group_ids):
    thread = Thread(
        target=_background_sync_older_pipelines,
        args=(group_ids,),
        daemon=True,
    )
    thread.start()


def sync_pipelines(group_ids=None, background=False):
    results = {"success": True, "failures": []}
    app = _get_flask_app()
    if app is None:
        raise RuntimeError(
            "Unable to establish Flask application context for sync_pipelines"
        )

    with app.app_context():
        gl = get_gitlab_client()

        if group_ids is None:
            selected_groups = (
                db.session.query(UserSelectedGroup.group_id).distinct().all()
            )
            group_ids = [group_id for (group_id,) in selected_groups]

        if not group_ids:
            logger.info("No groups selected, skipping sync.")
            return results

        try:
            for group_id in group_ids:
                try:
                    group = gl.groups.get(group_id)
                    projects = group.projects.list(get_all=True)

                    for proj in projects:
                        proj_data = proj.asdict()
                        project = db.session.get(Project, proj_data["id"])
                        if not project:
                            project = Project(id=proj_data["id"])
                            db.session.add(project)
                        project.group_id = group_id
                        project.name = proj_data["name"]
                        project.namespace = proj_data.get("namespace", {}).get(
                            "full_path", ""
                        )
                        project.web_url = proj_data.get("web_url", "")
                        project.default_branch = proj_data.get("default_branch", "main")
                        project.last_synced_at = datetime.now(timezone.utc)
                        db.session.flush()

                        pipelines = gl.projects.get(proj_data["id"]).pipelines.list(
                            per_page=10, get_all=False
                        )
                        recent_pipeline_id = pipelines[0].id if pipelines else None

                        for pipe in pipelines:
                            pipe_data = pipe.asdict()
                            _upsert_pipeline(pipe_data, proj_data["id"])

                            if recent_pipeline_id and pipe.id == recent_pipeline_id:
                                _sync_jobs_for_pipeline(
                                    proj_data["id"], pipe_data["id"], gl
                                )
                    db.session.commit()
                    logger.info("Sync complete for group %s.", group_id)
                except Exception as exc:
                    db.session.rollback()
                    logger.warning("Failed to sync group %s: %s", group_id, exc)
                    results["failures"].append(
                        {
                            "group_id": group_id,
                            "error": f"Failed to sync group: {group_id}",
                        }
                    )
            if results["failures"]:
                results["success"] = False
        except Exception as exc:
            db.session.rollback()
            logger.error("Sync failed: %s", exc)
            results["success"] = False
            results["failures"].append({"error": "Sync operation failed."})

    if background and results["success"]:
        _start_background_sync(group_ids)

    return results


def sync_pipelines_background(group_ids=None):
    return sync_pipelines(group_ids=group_ids, background=True)
