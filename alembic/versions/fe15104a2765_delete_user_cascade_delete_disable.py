"""delete user  cascade delete disable

Revision ID: fe15104a2765
Revises: bf7b85a8e262
Create Date: 2023-12-17 13:58:35.967497

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fe15104a2765'
down_revision = 'bf7b85a8e262'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('posts_user_id_fkey', 'posts', type_='foreignkey')
    op.create_foreign_key(None, 'posts', 'users', ['user_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'posts', type_='foreignkey')
    op.create_foreign_key('posts_user_id_fkey', 'posts', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###