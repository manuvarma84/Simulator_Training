from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Simulation, User, StudentSimulation, SimulationVersion
from analysis import calculate_analytics
from .decorators import role_required
from collections import defaultdict
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload
from datetime import datetime

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard')
@role_required('student')
def dashboard():
    assignments = StudentSimulation.query.filter_by(
        student_id=current_user.id
    ).options(
        joinedload(StudentSimulation.simulation),
        joinedload(StudentSimulation.assigner)
    ).all()
    
    return render_template('student/dashboard.html', 
                         assignments=assignments,
                         now=datetime.utcnow())

@student_bp.route('/simulation/<int:assignment_id>')
@role_required('student')
def view_simulation(assignment_id):
    assignment = StudentSimulation.query.options(
        joinedload(StudentSimulation.simulation)
    ).get_or_404(assignment_id)

    if assignment.student_id != current_user.id:
        abort(403)

    # Get simulation state with default values
    state = assignment.simulation_state or {
        'current_round': 1,
        'decisions': {}
    }

    active_version = SimulationVersion.query.filter_by(
        package_id=assignment.simulation.package_id,
        is_active=True
    ).first()

    return render_template('student/simulation.html',
                         assignment=assignment,
                         simulation=assignment.simulation,
                         active_version=active_version,
                         state=state,  # Add this line
                         now=datetime.utcnow())

@student_bp.route('/submit-decisions/<int:sim_id>', methods=['POST'])
@role_required('student')  # Add this decorator
def submit_decisions(sim_id):
    # Get the student's assignment
    assignment = StudentSimulation.query.filter_by(
        student_id=current_user.id,
        simulation_id=sim_id
    ).first_or_404()
    
    # Get the simulation
    sim = assignment.simulation
    
    # Process decisions
    inputs = {key: request.form[key] for key in request.form if key != 'csrf_token'}
    results = calculate_analytics(sim.config['analytics'], inputs)
    
    # Mark as completed
    assignment.is_completed = True
    db.session.commit()
    
    return render_template('student/results.html',
                         sim=sim,
                         assignment=assignment,
                         student_decisions=inputs,
                         analytics_results=results)