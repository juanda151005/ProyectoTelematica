from sqlalchemy.orm import Session

from app.modules.files.models import FileAttachment


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, file_attachment: FileAttachment) -> FileAttachment:
        self.db.add(file_attachment)
        self.db.commit()
        self.db.refresh(file_attachment)
        return file_attachment
