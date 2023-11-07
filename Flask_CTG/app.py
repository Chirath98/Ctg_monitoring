from flask import Flask, render_template, request, url_for, flash,redirect,session
from flask_mysqldb import MySQL
import pandas as pd
import pickle
import numpy as np
import bcrypt  # For hashing passwords

app = Flask(__name__)
app.secret_key = 'many random bytes'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'D313ac71hb'
app.config['MYSQL_DB'] = 'smart_ctg'

mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

#----Model
def prediction(lst):
    filename = 'model/predictor.pickle'
    with open(filename, 'rb') as file:
        model = pickle.load(file)
    pred_value = model.predict(lst)  #pass the entire data, not a list of lists
    return pred_value

@app.route("/ctg_prediction", methods=['POST', 'GET'])
def ctg_prediction():
    pred = 0  # Initialize pred with a default value of 0
    if request.method == 'POST':
        if 'csv_file' in request.files:
            csv_file = request.files['csv_file']
            bed_no = request.form['bed_no']  # Get the bed number from the form
            if csv_file.filename != '':
                df = pd.read_csv(csv_file)
                data_arrays = df.values.tolist()

                flat_data = [item for sublist in data_arrays for item in sublist]

                pred = prediction(data_arrays)
                pred = np.round(pred[0])

                # Insert patient data, including the prediction result and bed number, into the database
                cur = mysql.connection.cursor()
                cur.execute("UPDATE patient SET status = %s WHERE bed_no = %s", (pred, bed_no))
                mysql.connection.commit()
                cur.close()

    return render_template('ctg_prediction.html', pred=pred)
#model end

# dashboard
@app.route('/dashboard')
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM patient")
    data = cur.fetchall()
    cur.close()

    return render_template('dashboard.html', patient=data)

@app.route('/insert', methods=['POST'])
def insert():
    if request.method == "POST":
        flash("Data Inserted Successfully")
        bed_no = request.form['bed_no']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        guardian = request.form['guardian']
        comments = request.form['comments']

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO patient (bed_no, name, email, phone, guardian, comments) VALUES (%s, %s, %s, %s, %s, %s)",
            (bed_no, name, email, phone, guardian, comments)
        )
        mysql.connection.commit()
        return redirect(url_for('dashboard'))


@app.route('/delete/<string:id_data>', methods = ['GET'])
def delete(id_data):
    flash("Record Has Been Deleted Successfully")
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM patient WHERE id=%s", (id_data,))
    mysql.connection.commit()
    return redirect(url_for('dashboard'))

@app.route('/update', methods=['POST', 'GET'])
def update():
    if request.method == 'POST':
        id_data = request.form['id']
        bed_no = request.form['bed_no']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        guardian = request.form['guardian']
        comments = request.form['comments']
        status = request.form['status']

        cur = mysql.connection.cursor()
        cur.execute("""
        UPDATE patient SET bed_no=%s, name=%s, email=%s, phone=%s, guardian=%s, comments=%s, status=%s
        WHERE id=%s
        """, (bed_no, name, email, phone, guardian, comments, status, id_data))
        
        mysql.connection.commit()
        flash("Data Updated Successfully")
        return redirect(url_for('dashboard'))



@app.route('/view/<int:id_data>', methods=['GET'])
def view_patient(id_data):
    cur = mysql.connection.cursor()
    cur.execute("SELECT name, email, bed_no, phone, guardian, comments, status FROM patient WHERE id = %s", (id_data,))
    patient_data = cur.fetchone()
    cur.close()

    if patient_data is None:
        return "Patient not found"  
    # Create a dictionary with the data you want to pass to the template.
    patient = {
        'name': patient_data[0],
        'email': patient_data[1],
        'bed_no': patient_data[2],
        'phone': patient_data[3],
        'guardian': patient_data[4],
        'comments': patient_data[5],
        'status': patient_data[6]
    }
    return render_template('view_patient.html', patient=patient)


@app.route('/find', methods=['POST', 'GET'])
def find():
    if request.method == 'POST':
        search_query = request.form['search_query']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM patient WHERE name LIKE %s", ("%" + search_query + "%",))
        search_results = cur.fetchall()
        cur.close()
        return render_template('dashboard.html', patient=search_results)
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the provided username and password match an entry in the admin table
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name, password FROM admin WHERE name = %s", (username,))
        admin_data = cur.fetchone()
        cur.close()

        if admin_data is not None and admin_data[2] == password:
            # If the username and password are correct, set a session variable to indicate the user is logged in
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))  # Redirect to the admin panel
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

# Define a route for logging out
@app.route('/logout')
def logout():
    session['admin_logged_in'] = False
    return redirect(url_for('index'))  # Redirect to the home page


if __name__=="__main__":
    app.run(debug=True)