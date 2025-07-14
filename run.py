import os
from app import create_app, db
from app.models import User, CaseStudy, SolutionProviderInterview, ClientInterview, InviteToken, Label, Feedback

app = create_app()

@app.cli.command("init-db")
def init_db():
    """Initialize the database."""
    db.create_all()
    print("Database initialized!")

@app.cli.command("create-tables")
def create_tables():
    """Create all database tables."""
    db.create_all()
    print("All tables created!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=True, host="0.0.0.0", port=port) 