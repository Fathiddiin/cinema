from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app, cors_allowed_origins="*")

# rooms = { code: { users: [{sid, name}] } }
rooms = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('create_room')
def on_create(data):
    name = data.get('name', 'Anonim')[:20]
    code = data.get('code', '').upper()
    if not code:
        emit('error', {'msg': 'Xona kodi kerak'})
        return
    if code in rooms:
        emit('error', {'msg': 'Bu kod band, boshqa kod tanlang'})
        return
    rooms[code] = {'users': [{'sid': request.sid, 'name': name}]}
    join_room(code)
    emit('room_joined', {'code': code, 'name': name, 'is_host': True})

@socketio.on('join_room')
def on_join(data):
    name = data.get('name', 'Anonim')[:20]
    code = data.get('code', '').upper()
    if code not in rooms:
        emit('error', {'msg': 'Xona topilmadi. Kodni tekshiring'})
        return
    if len(rooms[code]['users']) >= 2:
        emit('error', {'msg': 'Xona to\'la (2/2 kishi)'})
        return
    rooms[code]['users'].append({'sid': request.sid, 'name': name})
    join_room(code)
    emit('room_joined', {'code': code, 'name': name, 'is_host': False})
    # Notify the host
    partner = rooms[code]['users'][0]
    emit('partner_joined', {'name': name}, to=partner['sid'])
    emit('partner_joined', {'name': partner['name']}, to=request.sid)

@socketio.on('chat_msg')
def on_chat(data):
    code = data.get('code')
    if code not in rooms:
        return
    emit('chat_msg', {'name': data['name'], 'text': data['text']}, to=code, include_self=False)

@socketio.on('video_action')
def on_video(data):
    code = data.get('code')
    if code not in rooms:
        return
    emit('video_action', data, to=code, include_self=False)

@socketio.on('disconnect')
def on_disconnect():
    for code, room in list(rooms.items()):
        users = room['users']
        user = next((u for u in users if u['sid'] == request.sid), None)
        if user:
            users.remove(user)
            emit('partner_left', {'name': user['name']}, to=code)
            if not users:
                del rooms[code]
            break

if __name__ == '__main__':
    socketio.run(app, debug=True)
