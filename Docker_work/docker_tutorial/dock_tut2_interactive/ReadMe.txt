1) Create main.py file.

2) Now we build the image:
..\docker_tutorial\dock_tut2_interactive> docker build -t python-soup-interactive .

NOTE: Whenever we change main.py file, we have to rebuild the image.
TO remove image: docker rmi -f <image_id>

3) Run the image:
..\docker_tutorial\dock_tut2_interactive> docker run -t -i python-soup-interactive
