from datetime import datetime
from extensions import db, socketio

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))

    @staticmethod
    def create_notification(user_id, message, link=None):
        notification = Notification(
            user_id=user_id,
            message=message,
            link=link
        )
        db.session.add(notification)
        db.session.commit()

        # Emit WebSocket event
        socketio.emit('notification', {
            'unreadCount': Notification.query.filter_by(user_id=user_id, is_read=False).count()
        }, room=f'user_{user_id}')
        return notification

    def mark_as_read(self):
        self.is_read = True
        db.session.commit()

        # Emit WebSocket event with updated unread count
        socketio.emit('notification', {
            'unreadCount': Notification.query.filter_by(user_id=self.user_id, is_read=False).count()
        }, room=f'user_{self.user_id}')