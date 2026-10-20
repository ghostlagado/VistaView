from app import socketio, app, HOST, PORT

if __name__ == "__main__":
    socketio.run(app, host=HOST, port=PORT)