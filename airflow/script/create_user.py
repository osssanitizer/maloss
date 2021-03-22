# Password
# https://github.com/mikeghen/airflow-tutorial/blob/master/README.md
import os
import airflow
from airflow import models, settings
from airflow.contrib.auth.backends.password_auth import PasswordUser

# create the user
user = PasswordUser(models.User())
if os.environ['AIRFLOW__WEBSERVER__USERNAME']:
    user.username = os.environ['AIRFLOW__WEBSERVER__USERNAME']
else:
    user.username = 'airflow'
if os.environ['AIRFLOW__WEBSERVER__EMAIL']:
    user.email = os.environ['AIRFLOW__WEBSERVER__EMAIL']
else:
    user.email = 'airflow@example.com'
if os.environ['AIRFLOW__WEBSERVER__PASSWORD']:
    user.password = os.environ['AIRFLOW__WEBSERVER__PASSWORD']
else:
    user.password = 'AirflowPassword'
print("creating user %s, email %s, password %s" % (user.username, user.email, user.password))

# save the user information
session = settings.Session()
session.add(user)
session.commit()
session.close()
exit()

