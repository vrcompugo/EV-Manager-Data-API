from app import db


class TaskPersistentUsers(db.Model):
    __versioned__ = {}
    __tablename__ = "task_persistent_users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bitrix_task_id = db.Column(db.Integer)
    data = db.Column(db.JSON)
