"""update_token_columns_to_text

Revision ID: 5480a30d0bae
Revises: 
Create Date: 2025-11-07 09:30:32.188133

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5480a30d0bae'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Update password_resets token column
    op.alter_column('password_resets', 'token',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.Text(),
               existing_nullable=False)
    
    # Update pending_users verification_token column
    op.alter_column('pending_users', 'verification_token',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.Text(),
               existing_nullable=False)

def downgrade():
    # Revert changes if needed
    op.alter_column('password_resets', 'token',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)
    
    op.alter_column('pending_users', 'verification_token',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)
