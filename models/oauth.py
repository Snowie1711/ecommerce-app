from extensions import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from models.user import User

class OAuth(OAuthConsumerMixin, db.Model):
    __tablename__ = 'oauth'
    
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    user = db.relationship(User)