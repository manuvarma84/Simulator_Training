# admin/routes.py (corrected)
from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from models import db, College, SimulationPackage, SimulationVersion, User
from .decorators import role_required  # Important security decorator
from flask_login import current_user
from sqlalchemy import or_
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
from flask import current_app
import os
import uuid
import zipfile
import json
import shutil
import pandas as pd

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Configuration constants
UPLOAD_FOLDER = 'simulation_packages'
ALLOWED_EXTENSIONS = {'zip'}
# Add after ALLOWED_EXTENSIONS definition
ALLOWED_SIMULATION_TYPES = {
    'business_sim': {
        'required_files': ['logic.py', 'routes.py', 'templates/'],
        'allowed_extensions': ['.py', '.html', '.json']
    }
}

def validate_sim_package(temp_dir, manifest):
    # 1. Verify simulation type
    sim_type = manifest.get('type')
    if sim_type not in ALLOWED_SIMULATION_TYPES:
        raise ValueError(f"Unsupported simulation type: {sim_type}")
    
    # 2. Check required files
    config = ALLOWED_SIMULATION_TYPES[sim_type]
    for file in config['required_files']:
        if not os.path.exists(os.path.join(temp_dir, file)):
            raise ValueError(f"Missing required file: {file}")
    
    # 3. Check for disallowed files
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext not in config['allowed_extensions']:
                raise ValueError(f"Disallowed file type: {ext}")

def validate_manifest(manifest):
    # Validate simulation type
    allowed_types = ['business_sim', 'financial_sim']  # Add your allowed types
    if 'type' not in manifest or manifest['type'] not in allowed_types:
        raise ValueError("Invalid or missing simulation type")
    
    # Validate entry points
    required_entry_points = ['student_view', 'professor_config']
    for ep in required_entry_points:
        if ep not in manifest['entry_points']:
            raise ValueError(f"Missing required entry point: {ep}")
            
                
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/add-college', methods=['GET', 'POST'])
@role_required('admin')
def add_college():
    if request.method == 'POST':
        code = request.form['code'].strip().upper()
        name = request.form['name'].strip()
        
        if College.query.filter_by(code=code).first():
            flash('College code already exists!', 'danger')
            return redirect(url_for('admin.add_college'))
            
        new_college = College(code=code, name=name)
        db.session.add(new_college)
        db.session.commit()
        flash('College added successfully!', 'success')
        return redirect(url_for('admin.add_college'))
    
    return render_template('admin/add_college.html')
    
@admin_bp.route('/upload-simulation', methods=['GET', 'POST'])
@role_required('admin')
def upload_simulation():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'sim_package' not in request.files:
            flash('No simulation package selected', 'danger')
            return redirect(request.url)

        file = request.files['sim_package']
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            try:
                # Create temporary directory
                sim_id = str(uuid.uuid4())
                temp_dir = os.path.join(UPLOAD_FOLDER, sim_id)
                os.makedirs(temp_dir, exist_ok=True)

                # Save and extract zip
                filename = secure_filename(file.filename)
                zip_path = os.path.join(temp_dir, filename)
                file.save(zip_path)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Verify manifest
                manifest_path = os.path.join(temp_dir, 'manifest.json')
                if not os.path.exists(manifest_path):
                    raise ValueError("Missing manifest.json file")

                with open(manifest_path) as f:
                    manifest = json.load(f)

                # Validate required manifest fields
                required_fields = ['name', 'version', 'entry_points']
                for field in required_fields:
                    if field not in manifest:
                        raise ValueError(f"Missing required field in manifest: {field}")

                validate_manifest(manifest)  # Add this line after loading the manifest

                if not current_user.college_id:
                    flash('Admin must belong to a college', 'danger')
                    return redirect(url_for('admin.upload_simulation'))
                
                # Create parent package if it doesn't exist
                package = SimulationPackage.query.filter_by(
                    name=manifest['name'],
                    college_id=current_user.college_id
                ).first()
                
                if not package:
                    package = SimulationPackage(
                        name=manifest['name'],
                        college_id=current_user.college_id
                    )
                    db.session.add(package)
                    db.session.commit()
                
                # Create new version
                version = SimulationVersion(
                    version=manifest['version'],
                    storage_path=temp_dir,
                    config=manifest,
                    package_id=package.id,
                    is_active='activate_now' in request.form
                )
                
                db.session.add(version)
                db.session.commit()
                
                # Deactivate other versions if activating this one
                if version.is_active:
                    SimulationVersion.query.filter(
                        SimulationVersion.package_id == package.id,
                        SimulationVersion.id != version.id
                    ).update({'is_active': False})
                    db.session.commit()
                
                flash('Simulation package uploaded successfully!', 'success')
                return redirect(url_for('admin.manage_simulations'))

            except Exception as e:
                # Cleanup on error
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                flash(f'Error processing package: {str(e)}', 'danger')
                return redirect(url_for('admin.upload_simulation'))

    return render_template('admin/upload_simulation.html')

@admin_bp.route('/manage-simulations')
@role_required('admin')
def manage_simulations():
    packages = SimulationPackage.query.filter_by(
        college_id=current_user.college_id
    ).options(
        db.joinedload(SimulationPackage.versions)
    ).all()
    
    return render_template('admin/manage_simulations.html', packages=packages)

@admin_bp.route('/edit-simulation/<int:version_id>', methods=['GET', 'POST'])
@role_required('admin')
def edit_simulation(version_id):
    version = SimulationVersion.query.get_or_404(version_id)
    package = version.package
    
    # Verify admin owns the simulation
    if package.college_id != current_user.college_id:
        abort(403)

    if request.method == 'POST':
        try:
            if 'sim_package' not in request.files:
                flash('No file selected', 'danger')
                return redirect(url_for('admin.edit_simulation', version_id=version_id))

            file = request.files['sim_package']
            if not file or file.filename == '':
                flash('No file selected', 'danger')
                return redirect(url_for('admin.edit_simulation', version_id=version_id))

            # Create new temp directory
            new_temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(uuid.uuid4()))
            os.makedirs(new_temp_dir, exist_ok=True)

            # Save and extract new zip
            filename = secure_filename(file.filename)
            zip_path = os.path.join(new_temp_dir, filename)
            file.save(zip_path)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(new_temp_dir)

            # Validate new package
            manifest_path = os.path.join(new_temp_dir, 'manifest.json')
            if not os.path.exists(manifest_path):
                raise ValueError("Missing manifest.json file")

            with open(manifest_path) as f:
                manifest = json.load(f)

            validate_manifest(manifest)
            validate_sim_package(new_temp_dir, manifest)

            # Create new version
            new_version = SimulationVersion(
                version=manifest['version'],
                storage_path=new_temp_dir,
                config=manifest,
                package_id=package.id,
                is_active=version.is_active
            )

            # Cleanup old version
            if os.path.exists(version.storage_path):
                shutil.rmtree(version.storage_path)

            db.session.delete(version)
            db.session.add(new_version)
            db.session.commit()

            flash('Simulation version updated successfully!', 'success')
            return redirect(url_for('admin.manage_simulations'))

        except Exception as e:
            if os.path.exists(new_temp_dir):
                shutil.rmtree(new_temp_dir)
            flash(f'Error updating simulation: {str(e)}', 'danger')
            return redirect(url_for('admin.edit_simulation', version_id=version_id))

    # GET request - show edit form
    college = College.query.get(current_user.college_id)
    return render_template('admin/edit_simulation.html', 
                         version=version,
                         package=package,
                         college=college)
                         
@admin_bp.route('/manage-staff')
@role_required('admin')
def manage_staff():
    staff = User.query.filter_by(
        college_id=current_user.college_id,
        role='professor'
    ).all()
    college = College.query.get(current_user.college_id)
    return render_template('admin/manage_staff.html', staff=staff, college=college)

@admin_bp.route('/add-staff', methods=['GET', 'POST'])
@role_required('admin')
def add_staff():
    college = College.query.get(current_user.college_id)
    
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            
            new_staff = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role='professor',
                college_id=current_user.college_id
            )
            
            db.session.add(new_staff)
            db.session.commit()
            flash('Staff member added successfully', 'success')
            return redirect(url_for('admin.manage_staff'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding staff: {str(e)}', 'danger')
    
    return render_template('admin/add_staff.html', college=college)

@admin_bp.route('/manage-students')
@role_required('admin')
def manage_students():
    college = College.query.get(current_user.college_id)
    
    # Base query
    query = User.query.filter_by(
        role='student',
        college_id=current_user.college_id
    )

    # Apply filters
    program = request.args.get('program')
    if program:
        query = query.filter_by(program_type=program)

    batch_year = request.args.get('batch_year')
    if batch_year:
        query = query.filter_by(batch_info=batch_year)

    detailed_batch = request.args.get('detailed_batch')
    if detailed_batch:
        query = query.filter(User.detailed_batch.ilike(f"%{detailed_batch}%"))

    search = request.args.get('search')
    if search:
        query = query.filter(or_(
            User.name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%")
        ))

    students = query.order_by(User.name).all()

    return render_template('admin/manage_students.html', 
                         students=students,
                         college=college)

@admin_bp.route('/upload-students', methods=['POST'])
@role_required('admin')
def upload_students():
    if 'student_file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('admin.manage_students'))
    
    file = request.files['student_file']
    if file.filename.endswith(('.csv', '.xlsx')):
        try:
            df = pd.read_excel(file) if file.filename.endswith('.xlsx') else pd.read_csv(file)
            required_columns = ['name', 'email', 'program_type', 'batch_year', 'detailed_batch']
            
            if not all(col in df.columns for col in required_columns):
                flash('Missing required columns in file', 'danger')
                return redirect(url_for('admin.manage_students'))
            
            for _, row in df.iterrows():
                user = User(
                    email=row['email'],
                    name=row['name'],
                    program_type=row['program_type'],
                    batch_info=row['batch_year'],
                    detailed_batch=row['detailed_batch'],
                    role='student',
                    college_id=current_user.college_id,
                    password_hash=generate_password_hash(str(uuid.uuid4()))
                )
                db.session.add(user)
            
            db.session.commit()
            flash(f'{len(df)} students added successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing file: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_students'))

@admin_bp.route('/admin-dashboard')
@role_required('admin')
def admin_dashboard():
    college = College.query.get(current_user.college_id)
    stats = {
        'staff_count': User.query.filter_by(college_id=current_user.college_id, role='professor').count(),
        'student_count': User.query.filter_by(college_id=current_user.college_id, role='student').count(),
        'simulation_count': SimulationPackage.query.filter_by(college_id=current_user.college_id).count()
    }
    return render_template('admin/dashboard.html', stats=stats, college=college)
    
    
@admin_bp.route('/delete-simulation/<int:sim_id>', methods=['POST'])
@role_required('admin')
def delete_simulation(sim_id):
    sim = SimulationPackage.query.filter_by(
        id=sim_id,
        college_id=current_user.college_id
    ).first_or_404()
    
    try:
        if os.path.exists(sim.storage_path):
            shutil.rmtree(sim.storage_path)
        db.session.delete(sim)
        db.session.commit()
        flash('Simulation deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting simulation: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_simulations'))

@admin_bp.route('/toggle-simulation/<int:version_id>', methods=['POST'])
@role_required('admin')
def toggle_simulation(version_id):
    version = SimulationVersion.query.filter_by(id=version_id).first_or_404()
    
    # Ensure admin owns the package
    if version.package.college_id != current_user.college_id:
        abort(403)
    
    try:
        # Deactivate all versions
        SimulationVersion.query.filter_by(package_id=version.package_id).update({'is_active': False})
        # Activate selected version
        version.is_active = True
        db.session.commit()
        flash('Active version updated', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating version: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_simulations'))
    
@admin_bp.route('/toggle-version/<int:version_id>', methods=['POST'])
@role_required('admin')
def toggle_version(version_id):
    version = SimulationVersion.query.get_or_404(version_id)
    if version.package.college_id != current_user.college_id:
        abort(403)

    try:
        # Deactivate all versions in the package
        SimulationVersion.query.filter_by(package_id=version.package_id).update({'is_active': False})
        
        # Toggle the selected version
        version.is_active = not version.is_active
        db.session.commit()
        flash('Version activation status updated', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating version: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_simulations'))

@admin_bp.route('/delete-version/<int:version_id>', methods=['GET', 'POST'])
@role_required('admin')
def delete_version(version_id):
    version = SimulationVersion.query.get_or_404(version_id)
    if version.package.college_id != current_user.college_id:
        abort(403)

    if request.method == 'POST':
        try:
            if os.path.exists(version.storage_path):
                shutil.rmtree(version.storage_path)
            db.session.delete(version)
            db.session.commit()
            flash('Version deleted successfully', 'success')
            return redirect(url_for('admin.manage_simulations'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting version: {str(e)}', 'danger')
    
    # GET request shows confirmation page
    return render_template('admin/delete_simulation.html', version=version)
    
@admin_bp.route('/edit-staff/<int:staff_id>', methods=['GET', 'POST'])
@role_required('admin')
def edit_staff(staff_id):
    college = College.query.get(current_user.college_id)
    staff = User.query.filter_by(
        id=staff_id,
        role='professor',
        college_id=current_user.college_id
    ).first_or_404()

    if request.method == 'POST':
        try:
            staff.name = request.form['name']
            staff.email = request.form['email']
            
            if request.form['password']:
                staff.password_hash = generate_password_hash(request.form['password'])
            
            db.session.commit()
            flash('Staff member updated successfully', 'success')
            return redirect(url_for('admin.manage_staff'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating staff: {str(e)}', 'danger')

    return render_template('admin/edit_staff.html', 
                         staff=staff,
                         college=college)

@admin_bp.route('/delete-staff/<int:staff_id>', methods=['POST'])
@role_required('admin')
def delete_staff(staff_id):
    staff_member = User.query.filter_by(
        id=staff_id,
        role='professor',
        college_id=current_user.college_id
    ).first_or_404()

    try:
        db.session.delete(staff_member)
        db.session.commit()
        flash('Staff member deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting staff: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_staff'))
    
@admin_bp.route('/add-student', methods=['GET', 'POST'])
@role_required('admin')
def add_student():
    college = College.query.get(current_user.college_id)
    
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            password = str(uuid.uuid4())[:8]  # Generate random password
            
            new_student = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role='student',
                college_id=current_user.college_id,
                program_type=request.form['program_type'],
                batch_info=request.form['batch_info'],
                detailed_batch=request.form['detailed_batch']                
            )
            
            db.session.add(new_student)
            db.session.commit()
            
            flash(f'Student added successfully. Temporary password: {password}', 'success')
            return redirect(url_for('admin.manage_students'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'danger')
    
    return render_template('admin/add_student.html', college=college)

@admin_bp.route('/delete-student/<int:student_id>', methods=['POST'])
@role_required('admin')
def delete_student(student_id):
    student = User.query.filter_by(
        id=student_id,
        role='student',
        college_id=current_user.college_id
    ).first_or_404()

    try:
        db.session.delete(student)
        db.session.commit()
        flash('Student deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting student: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_students'))
    
# Add to routes.py
@admin_bp.route('/edit-student/<int:student_id>', methods=['GET', 'POST'])
@role_required('admin')
def edit_student(student_id):
    college = College.query.get(current_user.college_id)
    student = User.query.filter_by(
        id=student_id,
        role='student',
        college_id=current_user.college_id
    ).first_or_404()

    if request.method == 'POST':
        try:
            student.name = request.form['name']
            student.email = request.form['email']
            student.program_type = request.form['program_type']
            student.batch_info = request.form['batch_info']
            student.detailed_batch = request.form['detailed_batch']    
            
            if request.form.get('password'):
                student.password_hash = generate_password_hash(request.form['password'])
            
            db.session.commit()
            flash('Student updated successfully', 'success')
            return redirect(url_for('admin.manage_students'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating student: {str(e)}', 'danger')

    return render_template('admin/edit_student.html', 
                         student=student,
                         college=college)

@admin_bp.route('/bulk-edit-students', methods=['POST'])
@role_required('admin')
def bulk_edit_students():
    student_ids = request.form.getlist('student_ids')
    
    # Get students from same college
    students = User.query.filter(
        User.id.in_(student_ids),
        User.role == 'student',
        User.college_id == current_user.college_id
    ).all()
    
    # Add your bulk edit logic here
    flash(f'{len(students)} students selected for editing', 'info')
    return redirect(url_for('admin.manage_students'))

@admin_bp.route('/bulk-delete-students', methods=['POST'])
@role_required('admin')
def bulk_delete_students():
    student_ids = request.form.getlist('student_ids')
    
    try:
        if not student_ids:
            flash('No students selected', 'warning')
            return redirect(url_for('admin.manage_students'))
            
        delete_count = User.query.filter(
            User.id.in_(student_ids),
            User.role == 'student',
            User.college_id == current_user.college_id
        ).delete(synchronize_session=False)
        
        db.session.commit()
        flash(f'Successfully deleted {delete_count} students', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting students: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_students'))