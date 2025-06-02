from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from extensions import db
from sqlalchemy import UniqueConstraint

class StudentSimulation(db.Model):
    __tablename__ = 'student_simulation'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    simulation_id = db.Column(db.Integer, db.ForeignKey('simulation.id'))
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_completed = db.Column(db.Boolean, default=False)
    simulation_state = db.Column(db.JSON)  # Stores simulation progress
    results = db.Column(db.JSON)           # Final results storage
    start_date = db.Column(db.DateTime)  # Add these
    end_date = db.Column(db.DateTime)     # Add these
    
    # CORRECTED RELATIONSHIPS
    student = db.relationship('User', foreign_keys=[student_id], back_populates='received_assignments')
    simulation = db.relationship('Simulation', back_populates='assignments')
    assigner = db.relationship('User', foreign_keys=[assigned_by], back_populates='given_assignments')

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))  # Add this line    
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20))  # student, professor, admin
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    program_type = db.Column(db.String(50))
    batch_info = db.Column(db.String(50))
    detailed_batch = db.Column(db.String(100))
    
    # Relationships
    college = db.relationship('College', back_populates='users')
    
    # Student-related relationships
    received_assignments = db.relationship(
        'StudentSimulation',
        foreign_keys='StudentSimulation.student_id',
        back_populates='student',
        lazy=True
    )
    
    # Professor-related relationships
    given_assignments = db.relationship(
        'StudentSimulation',
        foreign_keys='StudentSimulation.assigned_by',
        back_populates='assigner',  # ✅ Match StudentSimulation relationship
        lazy=True
    )

    # Remove the simulations relationship and access through assignments instead

class College(db.Model):
    __tablename__ = 'college'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    code = db.Column(db.String(20), unique=True)
    subscription_expiry = db.Column(db.DateTime)
    
    users = db.relationship('User', back_populates='college', lazy=True)
    simulations = db.relationship('Simulation', back_populates='college', lazy=True)
    
    __table_args__ = (
        UniqueConstraint('code', name='uq_college_code'),
    )

# Add this to your models.py
class SimulationPackage(db.Model):
    __tablename__ = 'simulation_package'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))  # Remove unique=True as versions will handle uniqueness
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    instances = db.relationship('Simulation', back_populates='package')
    
    # Relationships
    college = db.relationship('College', backref='packages')
    versions = db.relationship('SimulationVersion', backref='package', lazy=True)   
    @property
    def active_version(self):
        return SimulationVersion.query.filter_by(
            package_id=self.id,
            is_active=True
        ).first()
        
class SimulationVersion(db.Model):
    __tablename__ = 'simulation_version'
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    storage_path = db.Column(db.String(200), nullable=False)
    config = db.Column(db.JSON, nullable=False)  # Fixed syntax here
    is_active = db.Column(db.Boolean, default=False)
    package_id = db.Column(db.Integer, db.ForeignKey('simulation_package.id'), nullable=False)
    
class Simulation(db.Model):
    __tablename__ = 'simulation'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'))
    config = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    package_id = db.Column(db.Integer, db.ForeignKey('simulation_package.id'))
    package = db.relationship('SimulationPackage', back_populates='instances')
    
    # Relationships
    college = db.relationship('College', back_populates='simulations')
    assignments = db.relationship('StudentSimulation', back_populates='simulation', lazy=True)  # Add this line

    @property
    def assigned_count(self):
        return len(self.assignments)  # Changed from student_assignments to assignments

    @property
    def completed_count(self):
        return len([a for a in self.assignments if a.is_completed])  # Changed here too

    @property
    def active_version(self):
        return SimulationVersion.query.filter_by(
            package_id=self.package_id,
            is_active=True
        ).first()