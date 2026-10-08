from flask import Flask, current_app, jsonify, request
import sqlite3
import os


DATABASE = os.environ.get("DATABASE", "aceest_fitness.db")


PROGRAMS = {
    "Fat Loss": {
        "factor": 22,
        "description": "Fat loss focused fitness program",
    },
    "Muscle Gain": {
        "factor": 35,
        "description": "Muscle gain and strength focused program",
    },
    "Beginner": {
        "factor": 26,
        "description": "Beginner-friendly full-body fitness program",
    },
}


def get_db():
    connection = sqlite3.connect(current_app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    return connection


def init_db(database):
    connection = sqlite3.connect(database)

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            age INTEGER NOT NULL,
            height REAL NOT NULL,
            weight REAL NOT NULL,
            program TEXT NOT NULL,
            calories INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            week TEXT NOT NULL,
            adherence REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            workout_type TEXT NOT NULL,
            duration_min INTEGER NOT NULL,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );
        """
    )

    connection.commit()
    connection.close()


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        DATABASE=os.environ.get(
            "DATABASE",
            "aceest_fitness.db",
        )
    )

    if test_config is not None:
        app.config.update(test_config)

    init_db(app.config["DATABASE"])

    @app.route("/")
    def home():
        return jsonify(
            {
                "application": "ACEest Fitness & Gym",
                "status": "running",
                "version": "1.0",
            }
        )

    @app.route("/health")
    def health():
        return jsonify({"status": "healthy"})

    @app.route("/programs")
    def programs():
        return jsonify(PROGRAMS)

    @app.route("/clients", methods=["GET"])
    def get_clients():
        connection = get_db()
        clients = connection.execute(
            "SELECT * FROM clients ORDER BY id"
        ).fetchall()
        connection.close()

        return jsonify([dict(client) for client in clients])

    @app.route("/clients", methods=["POST"])
    def create_client():
        data = request.get_json(silent=True) or {}

        name = data.get("name")
        age = data.get("age")
        height = data.get("height")
        weight = data.get("weight")
        program = data.get("program")

        if not name:
            return jsonify({"error": "Name is required"}), 400

        if program not in PROGRAMS:
            return jsonify({"error": "Invalid program"}), 400

        try:
            age = int(age)
            height = float(height)
            weight = float(weight)
        except (TypeError, ValueError):
            return jsonify(
                {"error": "Age, height and weight must be numeric"}
            ), 400

        if weight <= 0:
            return jsonify(
                {"error": "Weight must be greater than zero"}
            ), 400

        calories = round(weight * PROGRAMS[program]["factor"])

        connection = get_db()

        try:
            cursor = connection.execute(
                """
                INSERT INTO clients
                (name, age, height, weight, program, calories)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    age,
                    height,
                    weight,
                    program,
                    calories,
                ),
            )

            connection.commit()

            client = connection.execute(
                "SELECT * FROM clients WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()

        except sqlite3.IntegrityError:
            connection.close()
            return jsonify(
                {"error": "Client already exists"}
            ), 409

        connection.close()

        return jsonify(
            {
                "message": "Client created successfully",
                "client": dict(client),
            }
        ), 201

    @app.route("/clients/<int:client_id>")
    def get_client(client_id):
        connection = get_db()

        client = connection.execute(
            "SELECT * FROM clients WHERE id = ?",
            (client_id,),
        ).fetchone()

        connection.close()

        if client is None:
            return jsonify({"error": "Client not found"}), 404

        return jsonify(dict(client))

    @app.route(
        "/clients/<int:client_id>/progress",
        methods=["GET"],
    )
    def get_progress(client_id):
        connection = get_db()

        client = connection.execute(
            "SELECT id FROM clients WHERE id = ?",
            (client_id,),
        ).fetchone()

        if client is None:
            connection.close()
            return jsonify({"error": "Client not found"}), 404

        progress = connection.execute(
            """
            SELECT * FROM progress
            WHERE client_id = ?
            ORDER BY id
            """,
            (client_id,),
        ).fetchall()

        connection.close()

        return jsonify([dict(item) for item in progress])

    @app.route(
        "/clients/<int:client_id>/progress",
        methods=["POST"],
    )
    def add_progress(client_id):
        data = request.get_json(silent=True) or {}

        week = data.get("week")
        adherence = data.get("adherence")

        if not week:
            return jsonify({"error": "Week is required"}), 400

        if adherence is None:
            return jsonify(
                {"error": "Adherence is required"}
            ), 400

        try:
            adherence = float(adherence)
        except (TypeError, ValueError):
            return jsonify(
                {"error": "Adherence must be numeric"}
            ), 400

        if not 0 <= adherence <= 100:
            return (
                jsonify(
                    {
                        "error":
                        "Adherence must be between 0 and 100"
                    }
                ),
                400,
            )

        connection = get_db()

        client = connection.execute(
            "SELECT id FROM clients WHERE id = ?",
            (client_id,),
        ).fetchone()

        if client is None:
            connection.close()
            return jsonify({"error": "Client not found"}), 404

        cursor = connection.execute(
            """
            INSERT INTO progress
            (client_id, week, adherence)
            VALUES (?, ?, ?)
            """,
            (
                client_id,
                week,
                adherence,
            ),
        )

        connection.commit()

        progress = connection.execute(
            "SELECT * FROM progress WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        connection.close()

        return jsonify(
            {
                "message": "Progress saved successfully",
                "progress": dict(progress),
            }
        ), 201

    @app.route(
        "/clients/<int:client_id>/workouts",
        methods=["GET"],
    )
    def get_workouts(client_id):
        connection = get_db()

        client = connection.execute(
            "SELECT id FROM clients WHERE id = ?",
            (client_id,),
        ).fetchone()

        if client is None:
            connection.close()
            return jsonify({"error": "Client not found"}), 404

        workouts = connection.execute(
            """
            SELECT * FROM workouts
            WHERE client_id = ?
            ORDER BY id
            """,
            (client_id,),
        ).fetchall()

        connection.close()

        return jsonify([dict(workout) for workout in workouts])

    @app.route(
        "/clients/<int:client_id>/workouts",
        methods=["POST"],
    )
    def add_workout(client_id):
        data = request.get_json(silent=True) or {}

        date = data.get("date")
        workout_type = data.get("workout_type")
        duration_min = data.get("duration_min")
        notes = data.get("notes", "")

        if not date:
            return jsonify({"error": "Date is required"}), 400

        if not workout_type:
            return jsonify(
                {"error": "Workout type is required"}
            ), 400

        try:
            duration_min = int(duration_min)
        except (TypeError, ValueError):
            return jsonify(
                {"error": "Duration must be numeric"}
            ), 400

        if duration_min <= 0:
            return jsonify(
                {"error": "Duration must be greater than zero"}
            ), 400

        connection = get_db()

        client = connection.execute(
            "SELECT id FROM clients WHERE id = ?",
            (client_id,),
        ).fetchone()

        if client is None:
            connection.close()
            return jsonify({"error": "Client not found"}), 404

        cursor = connection.execute(
            """
            INSERT INTO workouts
            (client_id, date, workout_type, duration_min, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                client_id,
                date,
                workout_type,
                duration_min,
                notes,
            ),
        )

        connection.commit()

        workout = connection.execute(
            "SELECT * FROM workouts WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        connection.close()

        return jsonify(
            {
                "message": "Workout saved successfully",
                "workout": dict(workout),
            }
        ), 201

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
