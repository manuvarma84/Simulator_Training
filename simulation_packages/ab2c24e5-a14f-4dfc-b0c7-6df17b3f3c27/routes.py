from flask import Blueprint, render_template, current_app
from .logic import BusinessSimEngine
from .decorators import professor_required

bp = Blueprint('business_sim', __name__,
              url_prefix='/business_sim',
              template_folder='templates')

@bp.route('/<int:assignment_id>')
def student_view(assignment_id):
    # Get student's simulation state from database
    assignment = StudentSimulation.query.get_or_404(assignment_id)
    sim_engine = BusinessSimEngine(assignment.simulation.config)
    
    return render_template('business_sim/student_view.html',
                         state=assignment.simulation_state,
                         config=assignment.simulation.config)

@bp.route('/configure/<int:sim_id>')
@professor_required
def configure(sim_id):
    # Professor configuration interface
    sim = Simulation.query.get_or_404(sim_id)
    return render_template('business_sim/professor_config.html',
                          sim=sim)

@bp.route('/report/<int:assignment_id>')
@professor_required
def generate_report(assignment_id):
    # Reporting functionality
    assignment = StudentSimulation.query.get_or_404(assignment_id)
    return render_template('business_sim/report.html',
                         data=assignment.simulation_state)