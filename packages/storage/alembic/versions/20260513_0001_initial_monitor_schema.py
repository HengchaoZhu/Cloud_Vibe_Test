"""initial monitor storage schema

Revision ID: 20260513_0001
Revises: 
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260513_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "targets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_name"),
    )
    op.create_table(
        "aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_id", "value", name="uq_alias_target_value"),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("source_domain", sa.String(length=255), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("url_fingerprint", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url_fingerprint", name="uq_documents_url_fingerprint"),
    )
    op.create_index("ix_documents_url_fingerprint", "documents", ["url_fingerprint"], unique=False)
    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("source_class", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_run_priority", "tasks", ["run_id", "priority"], unique=False)
    op.create_table(
        "claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_fingerprint", name="uq_document_versions_content_fingerprint"),
    )
    op.create_index("ix_document_versions_content_fingerprint", "document_versions", ["content_fingerprint"], unique=False)
    op.create_table(
        "claim_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("normalized_claim", sa.Text(), nullable=False),
        sa.Column("structured_fields", sa.JSON(), nullable=False),
        sa.Column("claim_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_fingerprint", name="uq_claim_versions_claim_fingerprint"),
    )
    op.create_index("ix_claim_versions_claim_fingerprint", "claim_versions", ["claim_fingerprint"], unique=False)
    op.create_table(
        "candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_candidates_task_score", "candidates", ["task_id", "score"], unique=False)
    op.create_table(
        "digests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_version_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("quote_or_span", sa.Text(), nullable=False),
        sa.Column("stance", sa.String(length=32), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["claim_version_id"], ["claim_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "digest_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("digest_id", sa.Uuid(), nullable=False),
        sa.Column("claim_version_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["claim_version_id"], ["claim_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["digest_id"], ["digests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("digest_id", "claim_version_id", name="uq_digest_item_claim"),
    )
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("digest_item_id", sa.Uuid(), nullable=False),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["digest_item_id"], ["digest_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_table("digest_items")
    op.drop_table("evidence")
    op.drop_table("digests")
    op.drop_index("ix_candidates_task_score", table_name="candidates")
    op.drop_table("candidates")
    op.drop_index("ix_claim_versions_claim_fingerprint", table_name="claim_versions")
    op.drop_table("claim_versions")
    op.drop_index("ix_document_versions_content_fingerprint", table_name="document_versions")
    op.drop_table("document_versions")
    op.drop_table("claims")
    op.drop_index("ix_tasks_run_priority", table_name="tasks")
    op.drop_table("tasks")
    op.drop_table("entities")
    op.drop_index("ix_documents_url_fingerprint", table_name="documents")
    op.drop_table("documents")
    op.drop_table("runs")
    op.drop_table("aliases")
    op.drop_table("targets")
