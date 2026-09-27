1) Create Docker file in each python  and mysql dir. Also create docker-compose.yml file in necessary dir.

2) Run following: 
..\docker_tutorial\dock_tut_python_mysql1> docker-compose build

3)..\docker_tutorial\dock_tut_python_mysql1> docker-compose up
NOTE: You will see following error: pythonapp-1  | mysql.connector.errors.DatabaseError: 2003 (HY000): Can't connect to MySQL server on 'mysql:3306' (111)
Ignore it.

4) Kill the container (Ctrl+c) and then restart it: 
..\docker_tutorial\dock_tut_python_mysql1> docker-compose up

You would see O/P:
...
mysql-1      | 2024-06-30T09:01:23.410763Z 0 [System] [MY-011323] [Server] X Plugin ready for connections. Bind-address: '::' port: 33060, socket: /var/run/mysqld/mysqlx.sock
pythonapp-1  | DB connected
pythonapp-1  | [(1, 'John', 'Andersen'), (2, 'Emma', 'Smith')]
...
