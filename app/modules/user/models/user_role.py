from app import db
from sqlalchemy.dialects.postgresql import JSONB


class UserRole(db.Model):
    __versioned__ = {}
    __tablename__ = "user_role"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(60), unique=True)
    label = db.Column(db.String(150), unique=True, nullable=False)
    permissions = db.Column(JSONB)

    def __repr__(self):
        return "<UserRole '{}'>".format(self.code)

