from flask import Flask, render_template, jsonify, request
import requests
import pandas as pd
import numpy as np

app = Flask(__name__)

# Sheet2API
api_url = "https://sheet2api.com/v1/4rN3UV6RQwat/attendance-data"

def fetch_data():
    # fetch data
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json() 
        df = pd.DataFrame(data)
        # Ensure all week columns are numeric
        weeks = [f'Week {i}' for i in range(1, 15)]
        for week in weeks:
            df[week] = pd.to_numeric(df[week], errors='coerce')
        return df
    else:
        raise Exception(f"Failed to fetch data from Sheet2API. Status code: {response.status_code}")

# Get data and weeks columns
df = fetch_data()
weeks = [f'Week {i}' for i in range(1, 15)]

# Home page
@app.route('/') 
def home():
    return render_template('dashboard.html') 

# Data endpoints for Chart.js
@app.route('/api/individual_attendance')
def individual_attendance_data():
    campus = request.args.get('campus', 'all')
    filtered_df = df.copy()
    
    if campus != 'all':
        filtered_df = filtered_df[filtered_df['Campus'].str.lower() == campus.lower()]
    
    data = []
    for _, row in filtered_df.iterrows():
        student_data = {
            'name': f"{row['Student Name']} ({row['Campus']})",
            'data': row[weeks].tolist(),
            'at_risk': row['Week 14'] >= 10
        }
        data.append(student_data)
    
    return jsonify({
        'weeks': weeks,
        'students': data
    })

@app.route('/api/average_attendance')
def average_attendance_data():
    campus = request.args.get('campus', 'all')
    filtered_df = df.copy()
    
    if campus != 'all':
        filtered_df = filtered_df[filtered_df['Campus'].str.lower() == campus.lower()]
    
    avg_data = filtered_df.groupby('Course ID')[weeks].mean().reset_index()
    courses = avg_data['Course ID'].tolist()
    data = avg_data[weeks].values.tolist()
    
    avg_by_course = avg_data[weeks].mean(axis=1)
    highest_absence_course = avg_data.loc[avg_by_course.idxmin(), 'Course ID']
    
    return jsonify({
        'weeks': weeks,
        'courses': courses,
        'data': data,
        'highest_absence_course': highest_absence_course
    })

@app.route('/api/average_absence')
def average_absence_data():
    campus = request.args.get('campus', 'all')
    filtered_df = df.copy()
    
    if campus != 'all':
        filtered_df = filtered_df[filtered_df['Campus'].str.lower() == campus.lower()]
    
    melted = filtered_df.groupby('Course ID')[weeks].mean().reset_index().melt(
        id_vars=['Course ID'],
        value_vars=weeks,
        var_name='Week',
        value_name='Absence'
    )
    
    courses = melted['Course ID'].unique().tolist()
    data = {}
    for course in courses:
        data[course] = melted[melted['Course ID'] == course]['Absence'].tolist()
    
    highest_absence_course = melted.groupby('Course ID')['Absence'].mean().idxmax()
    
    return jsonify({
        'weeks': weeks,
        'courses': courses,
        'data': data,
        'highest_absence_course': highest_absence_course
    })

@app.route('/api/final_absence')
def final_absence_data():
    campus = request.args.get('campus', 'all')
    filtered_df = df.copy()
    
    if campus != 'all':
        filtered_df = filtered_df[filtered_df['Campus'].str.lower() == campus.lower()]
    
    final_avg = filtered_df.groupby('Course ID')[weeks].mean().mean(axis=1).reset_index()
    final_avg.columns = ['course', 'absence']
    
    highest_absence_course = final_avg.loc[final_avg['absence'].idxmax(), 'course']
    
    return jsonify({
        'data': final_avg.to_dict('records'),
        'highest_absence_course': highest_absence_course
    })

@app.route('/api/table_data')
def table_data():
    campus = request.args.get('campus', 'all')
    filtered_df = df.copy()
    
    if campus != 'all':
        filtered_df = filtered_df[filtered_df['Campus'].str.lower() == campus.lower()]
    
    table_data = filtered_df[['Student ID', 'Student Name', 'Course ID', 'CRN', 'Campus'] + weeks]
    return jsonify(table_data.to_dict('records'))

# Dashboard route
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/studentdata')
def student_data():
    # Get all student data
    students = df.to_dict('records')
    return render_template('studentdata.html', students=students, weeks=weeks)

if __name__ == '__main__':
    app.run(debug=True)

