from flask import request
from flask_login import current_user
from flask_socketio import join_room
from extensions import socketio

@socketio.on('connect')
def handle_connect():
    """Handle client connection and join them to their user-specific room"""
    if not current_user.is_authenticated:
        return False
    
    # Join user to their own room for private notifications
    join_room(f'user_{current_user.id}')
    return True