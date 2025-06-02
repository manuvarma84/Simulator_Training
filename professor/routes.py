from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from models import db, User, Simulation, College, StudentSimulation, SimulationPackage, SimulationVersion
from .decorators import role_required
from flask_login import current_user
from datetime import datetime

prof_bp = Blueprint('prof', __name__, url_prefix='/professor')

@prof_bp.route('/dashboard')
@role_required('professor')
def dashboard():
    simulations = Simulation.query.filter_by(college_id=current_user.college_id).all()
    return render_template('professor/dashboard.html', simulations=simulations)

@prof_bp.route('/create-simulation', methods=['GET', 'POST'])
@role_required('professor')
def create_simulation():
    # Common for both GET and POST (if needed later)
    college_id = current_user.college_id

    if request.method == 'GET':
        # Get all packages for the college that have at least one active version
        packages = SimulationPackage.query.filter_by(
            college_id=college_id
        ).join(SimulationVersion).filter(
            SimulationVersion.is_active == True
        ).distinct().all()

        return render_template('professor/create_simulation.html',
                            packages=packages)

    # POST handling
    if request.method == 'POST':
        package_id = request.form.get('package_id')
        instance_name = request.form.get('instance_name')
        
        if not package_id or not instance_name:
            flash('Missing required fields', 'danger')
            return redirect(url_for('prof.create_simulation'))
            
        package = SimulationPackage.query.filter_by(
            id=package_id,
            college_id=college_id
        ).first()

        if not package or not package.active_version:
            flash('Invalid simulation package or no active version', 'danger')
            return redirect(url_for('prof.create_simulation'))

        try:
            new_sim = Simulation(
                name=instance_name,
                college_id=college_id,
                package_id=package.id,
                config={
                    'max_rounds': int(request.form.get('max_rounds', 20)),
                    'initial_cash': float(request.form.get('initial_cash', 50))
                }
            )
            db.session.add(new_sim)
            db.session.commit()
            flash('Simulation instance created successfully!', 'success')
            return redirect(url_for('prof.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating simulation: {str(e)}', 'danger')
            return redirect(url_for('prof.create_simulation'))

    # This return is technically unreachable but kept for safety
    return redirect(url_for('prof.create_simulation'))

@prof_bp.route('/simulation/<int:sim_id>')
@role_required('professor')
def view_simulation(sim_id):
    sim = Simulation.query.get_or_404(sim_id)
    if sim.college_id != current_user.college_id:
        abort(403)
        
    # Get active version config
    active_version = SimulationVersion.query.filter_by(
        package_id=sim.package.id,
        is_active=True
    ).first()
    if not active_version:
        abort(404, description="No active version found for this simulation package")
        
    return render_template('professor/view_simulation.html',
                         sim=sim,
                         package=sim.package,
                         instance_config=sim.config,
                         package_config=active_version.config)

@prof_bp.route('/simulations/<int:sim_id>/assign', methods=['GET', 'POST'])
@role_required('professor')
def assign_simulation(sim_id):
    # Authorization and simulation setup
    sim = Simulation.query.get_or_404(sim_id)
    if sim.college_id != current_user.college_id:
        abort(403)
    
    if not sim.active_version:
        flash('Simulation has no active version', 'danger')
        return redirect(url_for('prof.dashboard'))

    # Filter setup
    program_types = [p[0] for p in User.query.with_entities(User.program_type).distinct() if p[0]]
    batch_years = [b[0] for b in User.query.with_entities(User.batch_info).distinct() if b[0]]
    detailed_batches = [d[0] for d in User.query.with_entities(User.detailed_batch).distinct() if d[0]]

    # Student query
    query = User.query.filter(
        User.college_id == current_user.college_id,
        User.role == 'student'
    )

    # Apply filters
    filter_params = {
        'program_type': request.args.get('program_type') if request.method == 'GET' else request.form.get('program_type'),
        'batch_info': request.args.get('batch_info') if request.method == 'GET' else request.form.get('batch_info'),
        'detailed_batch': request.args.get('detailed_batch') if request.method == 'GET' else request.form.get('detailed_batch')
    }

    for key, value in filter_params.items():
        if value:
            query = query.filter(getattr(User, key) == value)

    students = query.order_by(User.name).all()
    existing_assignments = {a.student_id for a in sim.assignments}  # Use set for faster lookups

    if request.method == 'POST':
        try:
            # Validate input
            student_ids = request.form.getlist('student_ids')
            if not student_ids:
                flash('No students selected', 'danger')
                return redirect(url_for('prof.assign_simulation', sim_id=sim_id))

            # Date handling
            start_date = datetime.fromisoformat(request.form['start_date'])
            end_date = datetime.fromisoformat(request.form['end_date'])
            if end_date <= start_date:
                flash("End date must be after start date", 'danger')
                return redirect(url_for('prof.assign_simulation', sim_id=sim_id))

            # Batch assignment
            new_assignments = [
                StudentSimulation(
                    student_id=student_id,
                    simulation_id=sim.id,
                    assigned_by=current_user.id,
                    start_date=start_date,
                    end_date=end_date
                )
                for student_id in student_ids
                if student_id not in existing_assignments
            ]

            if not new_assignments:
                flash('Selected students already have this assignment', 'warning')
                return redirect(url_for('prof.view_simulation', sim_id=sim.id))

            db.session.bulk_save_objects(new_assignments)
            db.session.commit()
            flash(f'Assigned to {len(new_assignments)} students', 'success')
            return redirect(url_for('prof.view_simulation', sim_id=sim.id))

        except KeyError:
            flash('Missing required date parameters', 'danger')
        except ValueError as e:
            flash(f'Invalid date format: {str(e)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Assignment failed: {str(e)}', 'danger')

    return render_template('professor/assign_simulation.html',
                         sim=sim,
                         students=students,
                         existing_assignments=existing_assignments,
                         program_types=program_types,
                         batch_years=batch_years,
                         detailed_batches=detailed_batches,
                         current_filters=filter_params)
                         
@prof_bp.route('/delete-simulation/<int:sim_id>')
@role_required('professor')
def delete_simulation(sim_id):
    sim = Simulation.query.get_or_404(sim_id)
    if sim.college_id != current_user.college_id:
        abort(403)
        
    try:
        db.session.delete(sim)
        db.session.commit()
        flash('Simulation deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting simulation: {str(e)}', 'danger')
        
    return redirect(url_for('prof.dashboard'))