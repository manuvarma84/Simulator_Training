from main import create_app
from extensions import db
from models import Simulation, User, College, StudentSimulation

app = create_app()

with app.app_context():
    print("Simulations:")
    for sim in Simulation.query.all():
        print(f"ID: {sim.id}, Name: {sim.name}, College: {sim.college.name if sim.college else 'None'}")

    print("\nUsers:")
    for user in User.query.all():
        print(f"ID: {user.id}, Email: {user.email}, Role: {user.role}")

    print("\nColleges:")
    for college in College.query.all():
        print(f"ID: {college.id}, Name: {college.name}, Code: {college.code}")

    print("\nStudent-Simulation Assignments:")
    for s in StudentSimulation.query.all():
        print(f"Student ID: {s.student_id}, Simulation ID: {s.simulation_id}, Assigned By: {s.assigned_by}, Completed: {s.is_completed}")
