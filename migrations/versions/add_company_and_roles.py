"""Add companies, company_invites, and user role/company fields

Revision ID: add_company_and_roles
Revises: add_language_to_case_studies
Create Date: 2025-11-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy import inspect
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'add_company_and_roles'
down_revision = 'add_language_to_case_studies'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    existing_columns_users = [col['name'] for col in inspector.get_columns('users')] if 'users' in existing_tables else []
    existing_columns_case_studies = [col['name'] for col in inspector.get_columns('case_studies')] if 'case_studies' in existing_tables else []
    
    # Create companies table if it doesn't exist
    if 'companies' not in existing_tables:
        op.create_table(
            'companies',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('owner_user_id', sa.Integer(), nullable=False, unique=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=True),
        )
    else:
        print("Companies table already exists, skipping creation")

    # Create company_invites table if it doesn't exist
    if 'company_invites' not in existing_tables:
        op.create_table(
            'company_invites',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('email', sa.String(length=255), nullable=False, index=True),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('role', sa.String(length=50), nullable=False, server_default='employee'),
            sa.Column('token', sa.String(length=255), nullable=False, unique=True, index=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=True),
            sa.Column('used', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        )
    else:
        print("Company_invites table already exists, skipping creation")

    # Add foreign keys after table creation (only if tables were just created or keys don't exist)
    # Check if foreign key exists by querying constraints
    if 'companies' in existing_tables:
        try:
            # Try to create foreign key - will fail silently if it exists
            op.create_foreign_key(
                'fk_companies_owner_user_id_users',
                'companies',
                'users',
                ['owner_user_id'],
                ['id'],
                ondelete='CASCADE',
            )
        except Exception:
            pass  # Foreign key might already exist
    
    if 'company_invites' in existing_tables:
        try:
            op.create_foreign_key(
                'fk_company_invites_company_id_companies',
                'company_invites',
                'companies',
                ['company_id'],
                ['id'],
                ondelete='CASCADE',
            )
        except Exception:
            pass  # Foreign key might already exist

    # Add role and company_id to users if they don't exist
    if 'role' not in existing_columns_users:
        op.add_column(
            'users',
            sa.Column('role', sa.String(length=50), nullable=True, server_default='owner'),
        )
    else:
        print("Users.role column already exists, skipping")
    
    if 'company_id' not in existing_columns_users:
        op.add_column(
            'users',
            sa.Column('company_id', sa.Integer(), nullable=True),
        )
        try:
            op.create_foreign_key(
                'fk_users_company_id_companies',
                'users',
                'companies',
                ['company_id'],
                ['id'],
                ondelete='SET NULL',
            )
        except Exception:
            pass  # Foreign key might already exist
    else:
        print("Users.company_id column already exists, skipping")

    # Add company_id to case_studies for company scoping if it doesn't exist
    if 'company_id' not in existing_columns_case_studies:
        op.add_column(
            'case_studies',
            sa.Column('company_id', sa.Integer(), nullable=True),
        )
        try:
            op.create_foreign_key(
                'fk_case_studies_company_id_companies',
                'case_studies',
                'companies',
                ['company_id'],
                ['id'],
                ondelete='CASCADE',
            )
        except Exception:
            pass  # Foreign key might already exist
    else:
        print("Case_studies.company_id column already exists, skipping")

    # Backfill: create one company per existing user and link
    bind = op.get_bind()
    metadata = sa.MetaData()

    users = sa.Table(
        'users',
        metadata,
        sa.Column('id', sa.Integer),
        sa.Column('email', sa.String(length=255)),
        sa.Column('company_name', sa.String(length=255)),
        sa.Column('role', sa.String(length=50)),
        sa.Column('company_id', sa.Integer),
    )

    companies = sa.Table(
        'companies',
        metadata,
        sa.Column('id', sa.Integer),
        sa.Column('name', sa.String(length=255)),
        sa.Column('owner_user_id', sa.Integer),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )

    case_studies = sa.Table(
        'case_studies',
        metadata,
        sa.Column('id', sa.Integer),
        sa.Column('user_id', sa.Integer),
        sa.Column('company_id', sa.Integer),
    )

    conn = bind

    # Create a company for each user and link their existing stories
    result = conn.execute(sa.select(users.c.id, users.c.email, users.c.company_name, users.c.company_id))
    user_rows = list(result)

    for row in user_rows:
        # Check if user already has a company_id set
        if row.company_id:
            company_id = row.company_id
            # Just update role if not set
            conn.execute(
                users.update()
                .where(users.c.id == row.id)
                .where(users.c.role.is_(None))
                .values(role='owner')
            )
        else:
            # Check if a company already exists for this user (by owner_user_id)
            existing_company = conn.execute(
                sa.select(companies.c.id)
                .where(companies.c.owner_user_id == row.id)
            ).first()
            
            if existing_company:
                company_id = existing_company.id
            else:
                # Derive a company name from existing company_name or email
                base_name = (row.company_name or '').strip()
                if not base_name:
                    base_name = f"{row.email}'s company"

                ins = companies.insert().values(
                    name=base_name,
                    owner_user_id=row.id,
                    created_at=datetime.utcnow(),
                )
                result = conn.execute(ins)
                # Get the inserted ID - handle different return types
                if hasattr(result, 'inserted_primary_key') and result.inserted_primary_key:
                    company_id = result.inserted_primary_key[0]
                else:
                    # Fallback: query for the company we just created
                    company_id = conn.execute(
                        sa.select(companies.c.id)
                        .where(companies.c.owner_user_id == row.id)
                    ).scalar()

            # Update user with role and company_id
            conn.execute(
                users.update()
                .where(users.c.id == row.id)
                .values(role='owner', company_id=company_id)
            )

        # Assign existing case studies to this company (only if they don't have company_id)
        conn.execute(
            case_studies.update()
            .where(case_studies.c.user_id == row.id)
            .where(case_studies.c.company_id.is_(None))
            .values(company_id=company_id)
        )

    # Make role non-nullable after backfill
    op.alter_column(
        'users',
        'role',
        existing_type=sa.String(length=50),
        nullable=False,
        server_default=None,
    )


def downgrade():
    # Drop foreign keys and columns in reverse order
    op.drop_constraint('fk_case_studies_company_id_companies', 'case_studies', type_='foreignkey')
    op.drop_column('case_studies', 'company_id')

    op.drop_constraint('fk_users_company_id_companies', 'users', type_='foreignkey')
    op.drop_column('users', 'company_id')
    op.drop_column('users', 'role')

    op.drop_constraint('fk_company_invites_company_id_companies', 'company_invites', type_='foreignkey')
    op.drop_constraint('fk_companies_owner_user_id_users', 'companies', type_='foreignkey')

    op.drop_table('company_invites')
    op.drop_table('companies')


