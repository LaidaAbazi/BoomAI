from app import create_app, db
from app.models import CaseStudy

app = create_app()
with app.app_context():
    # Get the 10 most recent case studies
    cases = CaseStudy.query.order_by(CaseStudy.id.desc()).limit(10).all()
    print('Most recent database titles:')
    for c in cases:
        print(f'ID {c.id}: "{c.title}"')
    
    print(f'\nTotal case studies: {CaseStudy.query.count()}') 