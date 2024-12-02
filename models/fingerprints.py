from datetime import datetime
from database.database import db

class Fingerprint(db.Model):
    __tablename__ = 'fingerprints'

    fingerprint_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recording_id = db.Column(db.String(), unique=True, nullable=False)
    file_path = db.Column(db.String(), nullable=False)
    num_partitions = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now())
    
    def __init__(self, recording_id, file_path, num_partitions, duration, created_at):
        self.recording_id = recording_id
        self.file_path = file_path
        self.num_partitions = num_partitions
        self.duration = duration
        self.created_at = created_at
       
    def to_dict(self):
        return {
            'fingerprint_id': self.fingerprint_id,
            'recording_id': self.recording_id,
            'file_path': self.file_path,
            'num_partitions': self.num_partitions,
            'duration': self.duration,
            'created_at': self.created_at.strftime('%Y-%m-%dT%H:%M:%S')
        }

    @classmethod
    def create(cls, recording_id, file_path, num_partitions, duration, created_at):
        fingerprint = cls(recording_id=recording_id, file_path=file_path, num_partitions=num_partitions, duration=duration, created_at=created_at)
        db.session.add(fingerprint)
        db.session.commit()
        return fingerprint

    @classmethod
    def get_by_recording_id(cls, recording_id):
        return cls.query.filter_by(recording_id=recording_id).first()

    @classmethod
    def get_all(cls):
        return cls.query.all()

    def update(self, file_path=None, num_partitions=None, duration=None):
        if file_path:
            self.file_path = file_path
        if num_partitions:
            self.num_partitions = num_partitions
        if duration:
            self.duration = duration
        
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
