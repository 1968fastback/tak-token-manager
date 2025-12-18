#!/bin/bash

echo "Starting Phase 2: Main application files..."

# The main.py file is large, so we'll create it in one go
cat > app/main.py << 'MAINPY_EOF'
from flask import Flask, request, jsonify, render_template, send_file, flash, redirect, url_for
from flask_cors import CORS
from app.database import db, EnrollmentToken, AuditLog
from app.token_service import TokenService
from app.tak_integration import TAKServerAPI
from app.email_service import EmailService
import os
from datetime import datetime
import qrcode
from io import BytesIO
import logging
import zipfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-me')

db.init_app(app)
email_service = EmailService()

TAK_SERVER_HOST = os.getenv('TAK_SERVER_HOST', '10.123.123.2')
TAK_SERVER_PORT = os.getenv('TAK_SERVER_PORT', '8089')
PUBLIC_URL = os.getenv('PUBLIC_URL', 'http://localhost:5000')
TOKEN_EXPIRY_MINUTES = int(os.getenv('TOKEN_EXPIRY_MINUTES', '120'))

tak_api = None
TAK_API_URL = os.getenv('TAK_API_URL')
if TAK_API_URL:
    tak_api = TAKServerAPI(TAK_API_URL, os.getenv('TAK_ADMIN_USER'), os.getenv('TAK_ADMIN_PASS'))

@app.route('/')
def index():
    stats = TokenService.get_statistics()
    return render_template('index.html', stats=stats)

@app.route('/create')
def create_user_page():
    return render_template('create_user.html')

@app.route('/user/<username>')
def user_detail(username):
    token = EnrollmentToken.query.filter_by(username=username).first()
    if not token:
        flash('User not found', 'error')
        return redirect(url_for('index'))
    return render_template('user_detail.html', token=token)

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'server': TAK_SERVER_HOST
    })

@app.route('/api/tokens', methods=['POST'])
def create_token():
    try:
        data = request.json
        username = data.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'Username required'}), 400
        
        result = TokenService.create_token(
            username=username,
            group_name=data.get('group_name', '__ANON__'),
            expiry_minutes=data.get('expiry_minutes', TOKEN_EXPIRY_MINUTES),
            email=data.get('email'),
            notes=data.get('notes')
        )
        
        if not result['success']:
            return jsonify(result), 400
        
        token_data = result['token_data']
        
        # Generate package
        try:
            package_path = generate_data_package(username, token_data['token'], token_data['group_name'])
            token_obj = EnrollmentToken.query.filter_by(username=username).first()
            token_obj.package_generated = True
            token_obj.package_path = package_path
            db.session.commit()
        except Exception as e:
            logger.error(f"Package generation failed: {e}")
        
        # Send email
        if data.get('send_email') and data.get('email') and email_service.enabled:
            qr_url = f"{PUBLIC_URL}/api/tokens/{username}/qr"
            package_url = f"{PUBLIC_URL}/api/tokens/{username}/package"
            
            email_result = email_service.send_enrollment_email(
                username=username,
                email=data.get('email'),
                token=token_data['token'],
                expires_at=datetime.fromisoformat(token_data['expires_at']),
                qr_url=qr_url,
                package_url=package_url
            )
            token_data['email_sent'] = email_result['success']
        
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tokens/<username>')
def get_token(username):
    result = TokenService.get_token(username)
    return jsonify(result), 200 if result['success'] else 404

@app.route('/api/tokens/<username>/revoke', methods=['POST'])
def revoke_token(username):
    result = TokenService.revoke_token(username)
    if tak_api:
        tak_api.revoke_certificate(username)
        tak_api.delete_user(username)
    return jsonify(result)

@app.route('/api/tokens', methods=['GET'])
def list_tokens():
    filter_type = request.args.get('filter', 'all')
    result = TokenService.list_tokens(filter_type)
    return jsonify(result)

@app.route('/api/stats')
def get_stats():
    return jsonify(TokenService.get_statistics())

@app.route('/api/tokens/<username>/qr')
def generate_qr_code(username):
    token_result = TokenService.get_token(username)
    if not token_result['success']:
        return jsonify(token_result), 404
    
    enrollment_url = f"{PUBLIC_URL}/api/tokens/{username}/package"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(enrollment_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@app.route('/api/tokens/<username>/package')
def download_package(username):
    token = EnrollmentToken.query.filter_by(username=username).first()
    if not token:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    
    if not token.package_path or not os.path.exists(token.package_path):
        token.package_path = generate_data_package(username, token.token, token.group_name)
        db.session.commit()
    
    return send_file(token.package_path, as_attachment=True, download_name=f"enroll-{username}.zip")

@app.route('/api/cleanup', methods=['POST'])
def manual_cleanup():
    result = TokenService.cleanup_expired_tokens()
    return jsonify(result)

def generate_data_package(username, token, group_name):
    """Generate enrollment package"""
    package_dir = '/app/packages'
    os.makedirs(package_dir, exist_ok=True)
    
    user_dir = f"{package_dir}/{username}"
    os.makedirs(f"{user_dir}/MANIFEST", exist_ok=True)
    
    # manifest.xml
    manifest = f"""<MissionPackageManifest version="2">
    <Configuration>
        <Parameter name="uid" value="{username}-{datetime.now().strftime('%Y%m%d%H%M%S')}"/>
        <Parameter name="name" value="enroll-{username}.zip"/>
        <Parameter name="onReceiveDelete" value="true"/>
    </Configuration>
    <Contents>
        <Content ignore="false" zipEntry="config.pref"/>
        <Content ignore="false" zipEntry="truststore-root.p12"/>
    </Contents>
</MissionPackageManifest>"""
    
    with open(f"{user_dir}/MANIFEST/manifest.xml", 'w') as f:
        f.write(manifest)
    
    # config.pref
    config = f"""<?xml version='1.0' standalone='yes'?>
<preferences>
    <preference version="1" name="cot_streams">
        <entry key="count" class="class java.lang.Integer">1</entry>
        <entry key="description0" class="class java.lang.String">ShadowMoses TAK</entry>
        <entry key="enabled0" class="class java.lang.Boolean">true</entry>
        <entry key="connectString0" class="class java.lang.String">{TAK_SERVER_HOST}:{TAK_SERVER_PORT}:ssl</entry>
        <entry key="caLocation0" class="class java.lang.String">cert/truststore-root.p12</entry>
        <entry key="caPassword0" class="class java.lang.String">atakatak</entry>
        <entry key="enrollForCertificateWithTrust0" class="class java.lang.Boolean">true</entry>
        <entry key="useAuth0" class="class java.lang.Boolean">true</entry>
        <entry key="username0" class="class java.lang.String">{username}</entry>
        <entry key="password0" class="class java.lang.String">{token}</entry>
        <entry key="cacheCreds0" class="class java.lang.String">Cache credentials</entry>
    </preference>
</preferences>"""
    
    with open(f"{user_dir}/config.pref", 'w') as f:
        f.write(config)
    
    # Copy truststore
    import shutil
    truststore_src = '/app/config/truststore-root.p12'
    if os.path.exists(truststore_src):
        shutil.copy2(truststore_src, f"{user_dir}/truststore-root.p12")
    
    # Create zip
    zip_path = f"{package_dir}/enroll-{username}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(user_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, user_dir)
                zipf.write(file_path, arcname)
    
    # Cleanup temp dir
    shutil.rmtree(user_dir)
    
    return zip_path

@app.before_first_request
def create_tables():
    db.create_all()
    logger.info("Database initialized")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
MAINPY_EOF

echo "
