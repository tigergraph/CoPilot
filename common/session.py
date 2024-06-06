import uuid


class Session:
    def __init__(self, session_id, user_id, db_conn):
        self.session_id = session_id
        self.user_id = user_id
        self.db_conn = db_conn
        self.graphname = db_conn.state.conn.graphname


class SessionHandler:
    def __init__(self):
        self.sessions = {}

    def create_session(self, user_id, db_conn):
        session_id = str(uuid.uuid4())
        session = Session(session_id, user_id, db_conn)
        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def delete_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]
