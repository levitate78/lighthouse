import logging
from datetime import datetime, timezone
from threading import Thread
from flask import current_app
from concurrent.futures import ThreadPoolExecutor, as_completed
from extensions import db, scheduler
from gitlab_utils import get_gitlab_client
from models import Project, Pipeline, PipelineJob, UserSelectedGroup, SyncProgress

logger = logging.getLogger(__name__)


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
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
    pipeline.coverage = _to_float(pipe_data.get("coverage"))
    return pipeline


def _extract_test_summary(summary_data):
    total = summary_data.get("total") if isinstance(summary_data, dict) else None
    if not isinstance(total, dict):
        return {}

    return {
        "test_total": _to_int(total.get("count") or total.get("total")),
        "test_success": _to_int(total.get("success")),
        "test_failed": _to_int(total.get("failed")),
        "test_skipped": _to_int(total.get("skipped")),
        "test_error": _to_int(total.get("error")),
        "test_duration": _to_float(total.get("time")),
    }


def _fetch_pipeline_test_summary(gl, project_id, pipeline_id):
    try:
        summary = gl.http_get(
            f"/projects/{project_id}/pipelines/{pipeline_id}/test_report_summary"
        )
        return _extract_test_summary(summary)
    except Exception as exc:
        logger.debug(
            "No test report summary for project %s pipeline %s: %s",
            project_id,
            pipeline_id,
            exc,
        )
        return {}


def _fetch_jobs_for_pipeline(gl,project_id,pipeline_id):
    try:
        project = gl.projects.get(project_id)
        pipeline = project.pipelines.get(pipeline_id)
        jobs = pipeline.jobs.list(per_page=100, get_all=True)
        pipeline_metrics = {
            "coverage": _to_float(pipeline.asdict().get("coverage")),
            **_fetch_pipeline_test_summary(gl, project_id, pipeline_id),
        }

        return pipeline_id, [job.asdict() for job in jobs], pipeline_metrics
    except Exception as e:
        logger.warning('Failed to fetch jobs for project %s pipeline %s: %s ',
                       project_id,
                       pipeline_id,
                       e)
        return pipeline_id, [], {}

def _sync_jobs_for_pipeline(pipeline_id, jobs_data, pipeline_metrics=None):
    if pipeline_metrics:
        pipeline = db.session.get(Pipeline, pipeline_id)
        if pipeline:
            for key, value in pipeline_metrics.items():
                if hasattr(pipeline, key):
                    setattr(pipeline, key, value)

    PipelineJob.query.filter_by(pipeline_id=pipeline_id).delete()
    for job_data in jobs_data:
        job_obj = PipelineJob(
            id=job_data["id"],
            pipeline_id=pipeline_id,
            name=job_data.get("name", ""),
            stage=job_data.get("stage", ""),
            status=job_data.get("status", "unknown"),
            web_url=job_data.get("web_url", ""),
            duration=job_data.get("duration"),
            coverage=_to_float(job_data.get("coverage")),
            started_at=_parse_dt(job_data.get("started_at")),
            finished_at=_parse_dt(job_data.get("finished_at")),
            runner_name=job_data.get("runner", {}).get("description", "")
            if job_data.get("runner")
            else "",
        )
        db.session.add(job_obj)


def _background_sync_older_pipelines(group_ids, user_token):
    app = _get_flask_app()
    if app is None:
        return

    with app.app_context():
        gl = get_gitlab_client(private_token=user_token)

        for group_id in group_ids:
            try:
                group = gl.groups.get(group_id)
                projects = group.projects.list(get_all=True)

                progress = db.session.get(SyncProgress, group_id)
                if not progress:
                    progress = SyncProgress(group_id=group_id)
                    db.session.add(progress)
                progress.group_name = group.name
                progress.status = "syncing_history"
                progress.message = "Starting history sync..."
                db.session.commit()

                synced_pipelines_count = 0

                for proj_idx, proj in enumerate(projects):
                    proj_data = proj.asdict()
                    project = db.session.get(Project, proj_data["id"])
                    if not project:
                        continue

                    page = 1
                    while True:
                        pipelines = gl.projects.get(proj_data["id"]).pipelines.list(
                            per_page=10, page=page, get_all=False
                        )
                        if not pipelines:
                            break

                        target_pids = []
                        for pipe in pipelines:
                            pipe_data = pipe.asdict()
                            _upsert_pipeline(pipe_data, proj_data["id"])

                            # Fetch jobs only if not already cached
                            jobs_exist = db.session.query(PipelineJob.id).filter_by(pipeline_id=pipe.id).first() is not None
                            if not jobs_exist:
                                target_pids.append(pipe.id)

                        if target_pids:
                            MAX_WORKERS = 5
                            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                                futures = [
                                    executor.submit(
                                        _fetch_jobs_for_pipeline,
                                        gl,
                                        proj_data["id"],
                                        pid,
                                    )
                                    for pid in target_pids
                                ]

                                for future in as_completed(futures):
                                    try:
                                        pipeline_id, jobs_data, metrics = future.result(timeout=15)
                                        _sync_jobs_for_pipeline(pipeline_id, jobs_data, metrics)
                                    except Exception as e:
                                        logger.warning('Parallel job fetch failed for project %s:%s', proj_data["id"], e)

                        synced_pipelines_count += len(pipelines)

                        progress = db.session.get(SyncProgress, group_id)
                        if progress:
                            progress.current_project = proj_idx + 1
                            progress.current_pipeline = min(synced_pipelines_count, progress.total_pipelines)
                            total_p = max(progress.total_pipelines, synced_pipelines_count)
                            progress.message = f"Syncing pipeline {progress.current_pipeline} of {total_p} for group {group.name}"
                            db.session.commit()

                        db.session.commit()
                        page += 1

                progress = db.session.get(SyncProgress, group_id)
                if progress:
                    progress.status = "completed"
                    progress.message = "Sync complete"
                    db.session.commit()

            except Exception as exc:
                logger.warning(
                    "Background sync failed for group %s: %s",
                    group_id,
                    exc,
                )
                progress = db.session.get(SyncProgress, group_id)
                if progress:
                    progress.status = "failed"
                    progress.message = f"Background sync failed: {exc}"
                    db.session.commit()
        db.session.remove()


def _start_background_sync(group_ids,user_token):
    thread = Thread(
        target=_background_sync_older_pipelines,
        args=(group_ids,user_token),
        daemon=True,
    )
    thread.start()


def sync_pipelines(group_ids=None, background=False, user_token=None):
    results = {"success": True, "failures": []}
    app = _get_flask_app()
    if app is None:
        raise RuntimeError(
            "Unable to establish Flask application context for sync_pipelines"
        )

    with app.app_context():
        gl = get_gitlab_client(private_token=user_token)

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

                    # Fetch total pipeline counts in parallel
                    def _fetch_pipeline_count(gl_client, project_id):
                        try:
                            pipelines_list = gl_client.projects.get(project_id).pipelines.list(per_page=1, get_all=False)
                            return getattr(pipelines_list, 'total', 0)
                        except Exception:
                            return 0

                    total_pipelines = 0
                    with ThreadPoolExecutor(max_workers=5) as count_executor:
                        count_futures = [
                            count_executor.submit(_fetch_pipeline_count, gl, proj.asdict()["id"])
                            for proj in projects
                        ]
                        for f in as_completed(count_futures):
                            try:
                                total_pipelines += f.result()
                            except Exception:
                                pass

                    progress = db.session.get(SyncProgress, group_id)
                    if not progress:
                        progress = SyncProgress(group_id=group_id)
                        db.session.add(progress)
                    progress.group_name = group.name
                    progress.status = "syncing"
                    progress.total_projects = len(projects)
                    progress.current_project = 0
                    progress.total_pipelines = total_pipelines
                    progress.current_pipeline = 0
                    progress.message = f"Starting sync for group {group.name}..."
                    db.session.commit()

                    for idx, proj in enumerate(projects):
                        proj_data = proj.asdict()

                        progress = db.session.get(SyncProgress, group_id)
                        if progress:
                            progress.current_project = idx + 1
                            progress.message = f"Syncing project {proj_data['name']} ({idx+1} of {len(projects)})"
                            db.session.commit()

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
                        MAX_WORKERS = 5

                        pipeline_ids = []
                        for pipe in pipelines:
                            pipe_data = pipe.asdict()
                            _upsert_pipeline(pipe_data, proj_data["id"])
                            pipeline_ids.append(pipe.id)
                            
                        target_pipeline_ids = (
                            [recent_pipeline_id] if recent_pipeline_id else []
                        )

                        if target_pipeline_ids:
                            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                                futures = [
                                    executor.submit(
                                        _fetch_jobs_for_pipeline,
                                        gl,
                                        proj_data["id"],
                                        pid,
                                    )
                                    for pid in target_pipeline_ids
                                ]

                                for future in as_completed(futures):
                                    try:
                                        pipeline_id, jobs_data, metrics = future.result(timeout=15)
                                        _sync_jobs_for_pipeline(pipeline_id,jobs_data,metrics)
                                    except Exception as e:
                                        logger.warning('Parallel job fetch failed for project %s:%s', proj_data["id"],e)

                    db.session.commit()
                    logger.info("Sync complete for group %s.", group_id)

                    progress = db.session.get(SyncProgress, group_id)
                    if progress:
                        if background:
                            progress.status = "syncing_history"
                            progress.message = "Starting history sync..."
                        else:
                            progress.status = "completed"
                            progress.message = "Sync complete"
                        db.session.commit()

                except Exception as exc:
                    db.session.rollback()
                    logger.warning("Failed to sync group %s: %s", group_id, exc)

                    progress = db.session.get(SyncProgress, group_id)
                    if progress:
                        progress.status = "failed"
                        progress.message = f"Failed to sync group: {exc}"
                        db.session.commit()

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
        _start_background_sync(group_ids,user_token)

    return results


def sync_pipelines_background(group_ids=None):
    return sync_pipelines(group_ids=group_ids, background=True)
