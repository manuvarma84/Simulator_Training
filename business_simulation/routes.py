from flask import Blueprint, render_template, abort
from business_simulation.decorators import professor_required, student_required  # Add student_required
from models import StudentSimulation, Simulation
from flask_login import current_user

bp = Blueprint('business_sim', __name__,
              url_prefix='/business_sim',
              template_folder='templates')

@bp.route('/student/<int:assignment_id>', methods=['GET', 'POST'])
@student_required  # Add this decorator
def student_view(assignment_id):
    # Verify student owns the assignment
    assignment = StudentSimulation.query.get_or_404(assignment_id)
    if assignment.student_id != current_user.id:
        abort(403)
    
    # Rest of your code remains the same
    sim_engine = BusinessSimEngine(assignment.simulation.config)
    return render_template('business_sim/student_view.html',
                         state=assignment.simulation_state,
                         config=assignment.simulation.config)

@bp.route('/configure/<int:sim_id>')
@professor_required
def configure(sim_id):
    # Add college ownership check
    sim = Simulation.query.get_or_404(sim_id)
    if sim.college_id != current_user.college_id:
        abort(403)
    
    return render_template('business_sim/professor_config.html',
                          sim=sim)

@bp.route('/report/<int:assignment_id>')
@professor_required
def generate_report(assignment_id):
    # Add college ownership check
    assignment = StudentSimulation.query.get_or_404(assignment_id)
    if assignment.simulation.college_id != current_user.college_id:
        abort(403)
    
    return render_template('business_sim/report.html',
                         data=assignment.simulation_state)