from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from app.database import db, EnrollmentToken
from app.token_service import TokenService
from app.email_service import EmailService
import os
from datetime import datetime
import qrcode
from io import BytesIO
import logging
import zipfile
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')

db.init_app(app)
email_service = EmailService()

TAK_HOST = os.getenv('TAK_SERVER_HOST', '10.123.123.2')
TAK_PORT = os.getenv('TAK_SERVER_PORT', '8089')
PUBLIC_URL = os.getenv('PUBLIC_URL', 'http://localhost:5000')

@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/dashboard')
def index():
    stats = TokenService.get_statistics()
    return render_template('index.html', stats=stats)

@app.route('/create')
def create_page():
    return render_template('create_user.html')

@app.route('/user/<username>')
def user_detail(username):
    token = EnrollmentToken.query.filter_by(username=username).first()
    return render_template('user_detail.html', token=token) if token else ('Not found', 404)

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/api/tokens', methods=['POST'])
def create_token():
    data = request.json
    result = TokenService.create_token(
        username=data.get('username'),
        group_name=data.get('group_name', '__ANON__'),
        expiry_minutes=data.get('expiry_minutes', 120),
        email=data.get('email'),
        notes=data.get('notes')
    )
    if result['success']:
        username = data.get('username')
        token_data = result['token_data']
        pkg_path = generate_package(username, token_data['token'], token_data['group_name'])
        token_obj = EnrollmentToken.query.filter_by(username=username).first()
        token_obj.package_path = pkg_path
        db.session.commit()
        
        if data.get('send_email') and data.get('email'):
            email_service.send_enrollment_email(
                username, data['email'], token_data['token'],
                datetime.fromisoformat(token_data['expires_at']),
                f"{PUBLIC_URL}/api/tokens/{username}/qr",
                f"{PUBLIC_URL}/api/tokens/{username}/package"
            )
    return jsonify(result), 201 if result['success'] else 400

@app.route('/api/tokens/<username>')
def get_token(username):
    return jsonify(TokenService.get_token(username))

@app.route('/api/tokens/<username>/revoke', methods=['POST'])
def revoke(username):
    return jsonify(TokenService.revoke_token(username))

@app.route('/api/tokens')
def list_tokens():
    return jsonify(TokenService.list_tokens(request.args.get('filter', 'all')))

@app.route('/api/stats')
def stats():
    return jsonify(TokenService.get_statistics())

@app.route('/api/tokens/<username>/qr')
def qr_code(username):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f"{PUBLIC_URL}/api/tokens/{username}/package")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/api/tokens/<username>/package')
def package(username):
    token = EnrollmentToken.query.filter_by(username=username).first()
    if not token or not token.package_path:
        return jsonify({'error': 'Not found'}), 404
    return send_file(token.package_path, as_attachment=True)

def generate_package(username, token, group):
    pkg_dir = '/app/packages'
    os.makedirs(pkg_dir, exist_ok=True)
    tmp_dir = f"{pkg_dir}/{username}"
    os.makedirs(f"{tmp_dir}/MANIFEST", exist_ok=True)
    
    manifest = f"""<MissionPackageManifest version="2">
    <Configuration>
        <Parameter name="uid" value="{username}"/>
        <Parameter name="name" value="enroll-{username}.zip"/>
    </Configuration>
    <Contents>
        <Content zipEntry="config.pref"/>
        <Content zipEntry="truststore-root.p12"/>
    </Contents>
</MissionPackageManifest>"""
    
    with open(f"{tmp_dir}/MANIFEST/manifest.xml", 'w') as f:
        f.write(manifest)
    
    config = f"""<?xml version='1.0' standalone='yes'?>
<preferences>
    <preference version="1" name="cot_streams">
        <entry key="count" class="class java.lang.Integer">1</entry>
        <entry key="connectString0" class="class java.lang.String">{TAK_HOST}:{TAK_PORT}:ssl</entry>
        <entry key="caLocation0" class="class java.lang.String">cert/truststore-root.p12</entry>
        <entry key="caPassword0" class="class java.lang.String">atakatak</entry>
        <entry key="enrollForCertificateWithTrust0" class="class java.lang.Boolean">true</entry>
        <entry key="useAuth0" class="class java.lang.Boolean">true</entry>
        <entry key="username0" class="class java.lang.String">{username}</entry>
        <entry key="password0" class="class java.lang.String">{token}</entry>
    </preference>
</preferences>"""
    
    with open(f"{tmp_dir}/config.pref", 'w') as f:
        f.write(config)
    
    if os.path.exists('/app/config/truststore-root.p12'):
        shutil.copy2('/app/config/truststore-root.p12', f"{tmp_dir}/")
    
    zip_path = f"{pkg_dir}/enroll-{username}.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for root, _, files in os.walk(tmp_dir):
            for file in files:
                fp = os.path.join(root, file)
                zf.write(fp, os.path.relpath(fp, tmp_dir))
    
    shutil.rmtree(tmp_dir)
    return zip_path

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
