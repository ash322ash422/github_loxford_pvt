First we create a simple django app:
1) Create a dir 'django_simple' on your local machine. 
2) Open visual-studio-code and open the above folder. Creat virtual env and install django package.
3) At the prompt, type " django-admin startproject mysite". This creates a django project called 'mysite'. At the prompt, type "cd mysite". This would take you inside 'mysite' directory.
4) At the prompt, type "python manage.py migrate". This would create some predefined admin apps that are very helpful.
5) At the prompt(in dir mysite), type "django-admin startapp notes". Make appropriate changes to notes/{urls.py,views.py} 
6) At the prompt(in dir mysite), type "django-admin startapp blog". Make appropriate changes to blog/{urls.py, views.py}
7) Go to mysite/settings.py and make appropriate changes
8) Go to mysite/urls.py and make appropriate changes
9) At the prompt, type "python manage.py runserver 0.0.0.0:8000". This would start development server on local machine port number 8000.
10) Go to web browser and type '127.0.0.1:8000/notes'. You will see ''notes' welcome page. Congratulations!!!!!
#####################################

0) create requirements.txt file:
..\dock_tut_django1\django_simple\mysite> pip freeze > .\requirements.txt

1) Now run  docker engine by open "Docker desktop" app.
2) Now create Dockerfile and docker-compose.yml file. In the same dir., enter cmd:

..\dock_tut_django1\django_simple\mysite> docker-compose build --no-cache
3) Now close and reopen "Docker desktop" app.
4) Now run  command:
..\dock_tut_django1\django_simple\mysite> docker-compose up

5) Goto URL 127.0.0.1:8000 ad you would see familiar django web page.

NOTE: Anytime code is changed then have to "docker-compose build" again and then "docker-compose up". (Also see docker-compose.yml)