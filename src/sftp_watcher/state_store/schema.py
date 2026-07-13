import sqlalchemy as sa

metadata = sa.MetaData()


downloaded_files = sa.Table(
    "downloaded_files",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("remote_path", sa.Text, nullable=False),
    sa.Column("local_path", sa.Text, nullable=False),
    sa.Column("size", sa.Integer, nullable=False),
    sa.Column("mtime", sa.Integer, nullable=False),
    sa.Column("process_state", sa.Text, nullable=False),
    sa.Column(
        "created_at",
        sa.Text,
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    ),
    sa.Column(
        "updated_at",
        sa.Text,
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    ),
    sa.CheckConstraint(
        "process_state IN ('pending', 'success', 'failed')",
        name="ck_downloaded_files_process_state",
    ),
    sa.UniqueConstraint(
        "remote_path",
        "size",
        "mtime",
        name="uq_downloaded_files_identity",
    ),
)


sa.Index(
    "idx_downloaded_files_process_state",
    downloaded_files.c.process_state,
)
