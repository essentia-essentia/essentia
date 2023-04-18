from flask import render_template,Flask,session,request,redirect
from uuid import getnode as get_mac
from datetime import datetime,timedelta
import pymysql
from flask_session import Session




app=Flask(__name__)
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route('/Login')
def login_page():
    return render_template('login.html')

@app.route("/Login_processing", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        #if credentials check out include the person in the session to authomatically login
        session["group"] = request.form.get("group")
        print(session["group"]+" has entered")
        return redirect("/")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session["group"] = None
    return redirect("/")

@app.route('/')
def index_page():
    connection = pymysql.connect(host='127.0.0.1',
                             user='root',
                             password='',
                             database='essentia_db',
                             cursorclass=pymysql.cursors.DictCursor)
    cursor=connection.cursor()
    #Check if the user is logged in and redirect appropriately
    if not session.get("group"):
        return redirect("/Login")

    #print('User is requesting for the timetable '+session['group'])
    #~~~~~~~~~~~~~~~~~~~~~~~Lessons~~~~~~~~~~~~~~~~~~~~~~~~~~``
    now=datetime.now()+timedelta(hours=3)
    week_day=now.weekday()+1

    #Data preperation
    #Get the current lesson
    #If the time the person is checking the timetable is tonight give tomorrows lessons and current lesson will be set to the first lesson tommorrow
    #if the time the person is checking the timetable is during a brake do something to indicate this either here in data preperation or using jinja if condition
    #If the time is a weekend show mondays sessions starting with the first session

    #check if its a weekend
    if week_day<=5:# if its a week day...
        #check if the time is within tonight between last lesson to midnight or between midnight to last lesson
        print('Today is a week day:'+"{}-{} {}:{}".format(now.day,now.month,now.hour,now.minute))
        midnight=datetime(now.year,now.month,now.day,23,59,00)
        last_lesson=datetime(now.year,now.month,now.day,17,20,00)
        if(last_lesson>now): # if 17:15 has not reached
            print("Showing todays lessons...")
            cursor.execute("SELECT * FROM `units` where `session_day`="+str(week_day)+" and `session_group`='"+session['group']+"' ORDER BY `session_start_time`;")
            data=cursor.fetchall()
            data=days_session_prep(data,now)
            #print(data)
        else: #if 17:15 has reached get tommorrows lessons
            print('Showing tommorrows lessons('+str(week_day+1)+')...')
            if(week_day==5):#if today is on friday show mondays lessons
                week_day=0
            cursor.execute("SELECT * FROM `units` where `session_day`="+str(week_day+1)+" and `session_group`='"+session['group']+"' ORDER BY `session_start_time`;")
            data=cursor.fetchall()
            data=days_session_prep(data,now+timedelta(days=1))
            #print(data)
    else: #if its a week end
        cursor.execute("SELECT * FROM `units` where `session_day`="+str(1)+" and `session_group`='"+session['group']+"' ORDER BY `session_start_time`;")
        data=cursor.fetchall()
        #print(data)

    return render_template('index.html',sessions=data)



@app.route('/time_table')
def time_table():
    #Check what group the person is FROM
    #~~~~~~~~~~~~~Group login~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    if not session.get("group"):
        return redirect("/Login")

    group=session['group']

    if(group=='BICS2B'):
        return render_template('timetables/ICS2B.html')
    elif(group=='BBIT3C'):
        return render_template('timetables/Sheet1.html')
    else:
        return "It seems your timetable is not available";



#function that prepears the data and determines the next or current lessons
def days_session_prep(data,day):
    now=datetime.now()+timedelta(hours=3)
    for session in data:
        start_time_data=str(session['session_start_time']).split(':')
        start_time=datetime(day.year,day.month,day.day,int(start_time_data[0]),int(start_time_data[1]),int(start_time_data[2]))
        end_time_data=str(session['session_end_time']).split(':')
        end_time=datetime(day.year,day.month,day.day,int(end_time_data[0]),int(end_time_data[1]),int(end_time_data[2]))

        if start_time>now:# the lesson has not started
            session['time_type']='future'
        else:# the lesson has started
            if end_time>now:# the lesson has not ended
                session['time_type']='current'
            else:# the lesson ended
                session['time_type']='past'

    return data


#Editing the timetable, links time...
@app.route('/Controls')
def table_database_controls():

    #~~~~~~~~~~~~~~Reconnecting to the database just in case connection was cutt off ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    connection = pymysql.connect(host='localhost',
                             user='root',
                             password='',
                             database='essentia_db',
                             cursorclass=pymysql.cursors.DictCursor)
    cursor=connection.cursor()
    #Check if the user is logged in and redirect appropriately
    if not session.get("group"):
        return redirect("/Login")

    #~~~~~~~~~~~~~~Check if the person is logged and redirecting appropriately if not logged in~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #Check if the user is logged in and redirect appropriately
    if not session.get("group"):
        return redirect("/Login")

    #~~~~~~~~~~~~~Giving controls to the user ~~~~~~~~~~~~
    group=session['group']
    cursor.execute("SELECT * FROM `units` WHERE `session_group`='"+group+"' ORDER BY `session_day`, `session_start_time`;")
    data=cursor.fetchall()

    #processing the session days; converting numerical days into English week days
    days={1:'Monday',2:'Teusday',3:'Wednesday',4:'Thursday',5:'Friday'}
    new_data=[]
    for individial_session in data:
        individial_session['day']=days[individial_session['session_day']]
        new_data.append(individial_session)
    data=new_data

    #renderring the data together with the sessions data for display edit or deleting
    return render_template('edit_table.html',data=data,session_group=group)


#adding a new session to the timetable table_database
@app.route("/new_session",methods=['POST','GET'])
def adding_new_session():
    #~~~~~~~~~~~~~~~~~~~~~~~Reconnecting to the database~~~~~~~~~~~~~~~~~~~~~~~~
    connection = pymysql.connect(host='localhost',
                             user='root',
                             password='',
                             database='essentia_db',
                             cursorclass=pymysql.cursors.DictCursor)
    cursor=connection.cursor()
    #Check if the user is logged in and redirect appropriately
    if not session.get("group"):
        return redirect("/Login")


    #~~~~~~~~~~~~~~~~~~~~~~~Data collection and addintion~~~~~~~~~~~~~~~~~~~~~~~~
    data={}
    if request.method == "POST":
        data['session_day']=request.form.get('session_day')
        data['session_name']=request.form.get('session_name')
        data['session_group']=request.form.get('session_group')
        data['session_start_time']=request.form.get('session_start_time')
        data['session_end_time']=request.form.get('session_end_time')
        data['session_venue_type']=request.form.get('session_venue_type')
        data['session_venue']=request.form.get('session_venue')

        #Check if the data is in the correct format and not empty

        #Executing an sqL statement that will add the rendered data into the table_database
        cursor.execute("INSERT INTO `units`( `session_day`,`session_group`, `session_name`, `session_start_time`, `session_end_time`, `session_venue_type`, `session_venue`) VALUES ('"+data['session_day']+"','"+data['session_group']+"','"+data['session_name']+"','"+data['session_start_time']+"','"+data['session_end_time']+"','"+data['session_venue_type']+"','"+data['session_venue']+"')")
        connection.commit()

    #We are done with the processing now return to the editing table
    #print(data)
    return redirect('/Controls')



@app.route('/delete_session',methods=['POST','GET'])
def delete_session():
    #~~~~~~~~~~~~~~~~~~~~~~~Reconnecting to the database~~~~~~~~~~~~~~~~~~~~~~~~
    connection = pymysql.connect(host='localhost',
                             user='root',
                             password='',
                             database='essentia_db',
                             cursorclass=pymysql.cursors.DictCursor)
    cursor=connection.cursor()
    #Check if the user is logged in and redirect appropriately
    if not session.get("group"):
        return redirect("/Login")


    #~~~~~~~~~~~~~~~~~~~~~~~Data collection and deletion process~~~~~~~~~~~~~~~~~~~~~~~~


    if(request.method=='POST'):
        #Delete the recived id
        id=request.form.get('session_id')
        cursor.execute("DELETE FROM `units` WHERE `unit_session_id`="+str(id))
        connection.commit()

    return redirect('/Controls')


#adding a new session to the timetable table_database
@app.route("/update_session",methods=['POST','GET'])
def updating_session():
    #~~~~~~~~~~~~~~~~~~~~~~~Reconnecting to the database~~~~~~~~~~~~~~~~~~~~~~~~
    connection = pymysql.connect(host='localhost',
                             user='root',
                             password='',
                             database='essentia_db',
                             cursorclass=pymysql.cursors.DictCursor)
    cursor=connection.cursor()
    #Check if the user is logged in and redirect appropriately
    if not session.get("group"):
        return redirect("/Login")


    #~~~~~~~~~~~~~~~~~~~~~~~Data collection and update process~~~~~~~~~~~~~~~~~~~~~~~~


    data={}
    if request.method == "POST":
        data['session_id']=request.form.get('session_id')
        data['session_day']=request.form.get('session_day')
        data['session_name']=request.form.get('session_name')
        data['session_group']=request.form.get('session_group')
        data['session_start_time']=request.form.get('session_start_time')
        data['session_end_time']=request.form.get('session_end_time')
        data['session_venue_type']=request.form.get('session_venue_type')
        data['session_venue']=request.form.get('session_venue')

        #Check if the data is in the correct format and not empty

        #Executing an sqL statement that will add the rendered data into the table_database
        cursor.execute("UPDATE `units` SET `session_day`='"+data['session_day']+"',`session_name`='"+data['session_name']+"',`session_start_time`='"+data['session_start_time']+"',`session_end_time`='"+data['session_end_time']+"',`session_venue_type`='"+data['session_venue_type']+"',`session_venue`='"+data['session_venue']+"' WHERE `unit_session_id`="+data['session_id']+"")
        connection.commit()

    #We are done with the processing now return to the editing table
    #print(data)
    return redirect('/Controls')

#@app.route('/')
#def hello_world():
#    return 'Hello from Flask!'

app.run(host='0.0.0.0', port=5000, debug=True)

