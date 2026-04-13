from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contact.models import Subject, Contact

# Conexión a tu base de datos PostgreSQL
engine = create_engine("postgresql+psycopg2://postgres:5432@localhost:5432/contact")

Session = sessionmaker(bind=engine)
session = Session()

# Insertar un Subject
new_subject = Subject(name="Matemáticas")
session.add(new_subject)
session.commit()

# Insertar un Contact relacionado con ese Subject
new_contact = Contact(name="Felipe", subject_id=new_subject.id)
session.add(new_contact)
session.commit()

# Consultar Subjects
print("Subjects:")
for s in session.query(Subject).all():
    print(s.id, s.name)

# Consultar Contacts
print("\nContacts:")
for c in session.query(Contact).all():
    print(c.id, c.name, c.subject_id)