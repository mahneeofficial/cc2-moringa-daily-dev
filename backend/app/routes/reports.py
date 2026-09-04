from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Content, ContentReport
from app.utils import role_required

reports_bp = Blueprint("reports", __name__)


def safe_get_user_id():
    """Extract integer user ID safely from JWT identity."""
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return int(identity.get("id"))
    return int(identity)


# -------------------------------------------------------------------
# 1. USER ENDPOINTS
# -------------------------------------------------------------------

@reports_bp.post("/content/<int:content_id>")
@jwt_required()
def report_content(content_id):
    """Submit a report for specific content.
    ---
    tags:
      - Content Reports
    security:
      - BearerAuth: []
    parameters:
      - name: content_id
        in: path
        type: integer
        required: true
        description: ID of the content being reported
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - reason
          properties:
            reason:
              type: string
              description: Reason for reporting the content
              example: Inappropriate or offensive material
    responses:
      201:
        description: Report submitted successfully.
      400:
        description: Reason is missing/invalid or user identity is invalid.
      401:
        description: Unauthorized.
      404:
        description: Content not found.
      500:
        description: Failed to submit report.
    """
    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found."}), 404

    data = request.get_json(silent=True) or {}
    reason = data.get("reason")

    if not reason or not str(reason).strip():
        return jsonify({"error": "Reason is required."}), 400

    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity."}), 400

    report = ContentReport(
        ReportedBy=user_id,
        ContentID=content_id,
        Reason=str(reason).strip(),
        Status="Pending",
    )

    try:
        db.session.add(report)
        db.session.commit()
        return jsonify({"message": "Report submitted successfully."}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to submit report", "details": str(e)}), 500


# -------------------------------------------------------------------
# 2. ADMIN ENDPOINTS
# -------------------------------------------------------------------

@reports_bp.get("")
@jwt_required()
@role_required("Admin")
def list_reports():
    """Retrieve all content reports (Admin only).
    ---
    tags:
      - Content Reports (Admin)
    security:
      - BearerAuth: []
    parameters:
      - name: status
        in: query
        type: string
        required: false
        description: Filter reports by status (e.g., Pending, Resolved)
        example: Pending
    responses:
      200:
        description: List of content reports retrieved successfully.
      401:
        description: Unauthorized.
      403:
        description: Forbidden (Requires Admin role).
    """
    status = request.args.get("status")

    query = ContentReport.query
    if status:
        query = query.filter_by(Status=status)

    reports = query.order_by(ContentReport.CreatedAt.desc()).all()

    return (
        jsonify([
            {
                "id": report.ReportID,
                "report_id": report.ReportID,
                "content_id": report.ContentID,
                "user_id": report.ReportedBy,
                "reason": report.Reason,
                "status": report.Status,
                "created_at": (
                    report.CreatedAt.isoformat()
                    if hasattr(report, "CreatedAt") and report.CreatedAt
                    else None
                ),
            }
            for report in reports
        ]),
        200,
    )


@reports_bp.patch("/<int:report_id>")
@jwt_required()
@role_required("Admin")
def resolve_report(report_id):
    """Mark a content report as Resolved (Admin only).
    ---
    tags:
      - Content Reports (Admin)
    security:
      - BearerAuth: []
    parameters:
      - name: report_id
        in: path
        type: integer
        required: true
        description: ID of the report to resolve
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            status:
              type: string
              example: Resolved
              description: Optional custom status (defaults to Resolved)
    responses:
      200:
        description: Report resolved successfully.
      401:
        description: Unauthorized.
      403:
        description: Forbidden (Requires Admin role).
      404:
        description: Report not found.
      500:
        description: Failed to update report status.
    """
    report = db.session.get(ContentReport, report_id)
    if not report:
        return jsonify({"error": "Report not found."}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "Resolved")

    try:
        report.Status = new_status
        db.session.commit()
        return jsonify({"message": f"Report marked as {new_status} successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update report status", "details": str(e)}), 500