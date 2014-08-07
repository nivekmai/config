WhatsApp Configurator
======

###Install

1. Instal virtualenv  
  ```sudo easy_install venv```
2. cd to src dir  
  ```cd confing/src```
3. Activate virtualenv  
  ```. venv/bin/activate```
4. Install Flask  
  ```pip install flask```
5. Install Flask Restful  
  ```pip install flask-restful```
6. Install GitPython
  ```pip install gitpython```

###Use

1. Start server (in venv)
  ```cd src```
  ```python config.py```

#### PUT
```curl http://localhost:5000/config/test.json -d '{"key":"value"}' -X PUT```

#### GET
```curl http://localhost:5000/config/test.json -X GET```

#### DELETE
```curl http://localhost:5000/config/test.json -X DELETE```