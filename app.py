from flask import Flask, app, render_template, request, redirect, url_for, flash, session, abort, send_from_directory, after_this_request
from werkzeug.utils import secure_filename
import pyAesCrypt
import os
from celery import Celery

app = Flask(__name__)
app.config['SECRET_KEY'] = 'c131454e-bb49-43e6-b1dd-7f993d45185f'
app.config['BUFFER_SIZE'] = 128 * 1024
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])


@celery.task
def remove_file(path):
    os.remove(path)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/encrypt', methods=['POST'])
def encrypt():
    file = request.files['file']
    pw = request.form.get('password')
    filename = secure_filename(file.filename)
    file.save(os.path.join('files', filename))
    pyAesCrypt.encryptFile(os.path.join('files', filename), os.path.join('files', filename)+'.aes',
                           pw, app.config['BUFFER_SIZE'])
    os.remove(os.path.join('files', filename))
    remove_file.apply_async(
        args=[os.path.join('files', filename+'.aes')], countdown=60)
    return send_from_directory('files', filename+'.aes', as_attachment=True)


@app.route('/decrypt', methods=['POST'])
def decrypt():
    file = request.files['defile']
    pw = request.form.get('depassword')
    filename = secure_filename(file.filename)
    if filename[-4:] != '.aes':
        flash('Encrypted file must end with .aes', 'warning')
        return redirect(url_for('home'))
    file.save(os.path.join('files', filename))
    try:
        pyAesCrypt.decryptFile(os.path.join('files', filename), os.path.join('files', filename)[:-4],
                               pw, app.config['BUFFER_SIZE'])
    except ValueError:
        flash('Error decrypting file', 'danger')
        os.remove(os.path.join('files', filename))
        return redirect(url_for('home'))
    os.remove(os.path.join('files', filename))
    remove_file.apply_async(
        args=[os.path.join('files', filename[:-4])], countdown=60)
    return send_from_directory('files', filename[:-4], as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
