import logging
from datetime import datetime, timezone
from flask import current_app

from extensions import db
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


def sync_pipelines():
    with current_app.app_context():
        gl = get_gitlab_client()

        selected_groups = db.session.query(UserSelectedGroup.group_id).distinct().all()
        group_ids = [group_id for (group_id,) in selected_groups]

        if not group_ids:
            logger.info("No groups selected, skipping sync.")
            return

        try:
            for group_id in group_ids:
                try:
                    group = gl.groups.get(group_id)
                    projects = group.projects.list(all=True)

                    for proj in projects:
                        proj_data = proj.asdict()
                        project = Project.query.get(proj_data["id"])
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
                            per_page=10
                        )
                        recent_pipeline_id = pipelines[0].id if pipelines else None

                        for pipe in pipelines:
                            pipe_data = pipe.asdict()
                            pipeline = Pipeline.query.get(pipe_data["id"])
                            if not pipeline:
                                pipeline = Pipeline(id=pipe_data["id"])
                                db.session.add(pipeline)
                            pipeline.project_id = proj_data["id"]
                            pipeline.ref = pipe_data.get("ref", "")
                            pipeline.sha = pipe_data.get("sha", "")
                            pipeline.status = pipe_data.get("status", "unknown")
                            pipeline.source = pipe_data.get("source", "")
                            pipeline.web_url = pipe_data.get("web_url", "")
                            pipeline.created_at = _parse_dt(pipe_data.get("created_at"))
                            pipeline.updated_at = _parse_dt(pipe_data.get("updated_at"))
                            pipeline.started_at = _parse_dt(pipe_data.get("started_at"))
                            pipeline.finished_at = _parse_dt(
                                pipe_data.get("finished_at")
                            )
                            pipeline.duration = pipe_data.get("duration")
                            pipeline.queued_duration = pipe_data.get("queued_duration")
                            db.session.flush()

                            if recent_pipeline_id and pipe.id == recent_pipeline_id:
                                jobs = (
                                    gl.projects.get(proj_data["id"])
                                    .pipelines.get(pipe_data["id"])
                                    .jobs.list()
                                )
                                PipelineJob.query.filter_by(
                                    pipeline_id=pipe_data["id"]
                                ).delete()
                                for job in jobs:
                                    job_data = job.asdict()
                                    job_obj = PipelineJob(
                                        id=job_data["id"],
                                        pipeline_id=pipe_data["id"],
                                        name=job_data.get("name", ""),
                                        stage=job_data.get("stage", ""),
                                        status=job_data.get("status", "unknown"),
                                        web_url=job_data.get("web_url", ""),
                                        duration=job_data.get("duration"),
                                        started_at=_parse_dt(
                                            job_data.get("started_at")
                                        ),
                                        finished_at=_parse_dt(
                                            job_data.get("finished_at")
                                        ),
                                        runner_name=job_data.get("runner", {}).get(
                                            "description", ""
                                        )
                                        if job_data.get("runner")
                                        else "",
                                    )
                                    db.session.add(job_obj)
                except Exception as exc:
                    logger.warning("Failed to sync group %s: %s", group_id, exc)

            db.session.commit()
            logger.info("Pipeline sync complete.")
        except Exception as exc:
            db.session.rollback()
            logger.error("Sync failed: %s", exc)
