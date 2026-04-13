from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

# Declarative base para SQLAlchemy
Base = declarative_base()

class Subject(Base):
    __tablename__ = 'subjects'
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)

    # Relación con contactos
    contacts = relationship("Contact", back_populates="subject")

class Contact(Base):
    __tablename__ = 'contacts'
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'))

    # Relación inversa con subject
    subject = relationship("Subject", back_populates="contacts")