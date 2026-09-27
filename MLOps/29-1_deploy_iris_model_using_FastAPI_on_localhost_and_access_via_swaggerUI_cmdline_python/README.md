
# Here I show how to deploy a ML model on localhost and access its API endpoint via POST request using browser or command line or a python program

### Requirements:
Install following packages:

- fastapi==0.116.1
- numpy==2.0.2
- scikit-learn==1.6.1

(OPTIONAL) Note: By the way, in my case I have a virtual env. So I activate my environment ( .venv\Scripts\Activate.ps1 ) 

Install above packages using following command:

```
(.venv) PS C:\Users\hi\gemini> python -m pip install fastapi==0.116.1 numpy==2.0.2 scikit-learn==1.6.1
```

## step1: Train and Save a Simple ML Model

See the code in file **step1_train_and_save_model.py**. Run this file and it creates file **iris_model.pkl**

## step2: Create FastAPI App

See the code in file **step2_app.py**. Do not run this file.

## step3: Run the FastAPI Server

In the directory where you created above **step2_app.py** file, on the command line type:

```
uvicorn step2_app:app --reload
```
This would actually run **step2_app.py**

## step4: Goto auto generated swagger UI
On your browser open **http://127.0.0.1:8000/docs**

-> click on "POST"    (Look at screenshot1.png)<br>
-> click "Try it Out" (Look at screenshot2.png)<br>
-> Enter following in request body (Look at screenshot3.png) <br>

a) In the request body enter following:
```

{
  "sepal_length": 5.1,
  "sepal_width": 3.5,
  "petal_length": 1.4,
  "petal_width": 0.2
}

```

Then click **Execute** . This should give prediction:0 (Look at screenshot4.png)

Now try following values in request:

Try 1 ) In the request body enter following:
```

{
  "sepal_length": 7.0,
  "sepal_width": 3.2,
  "petal_length": 4.7,
  "petal_width": 1.4
}

```

Then click **Execute**. This should give **prediction:1**

Try 2) In the request body enter following:
```

{
  "sepal_length": 6.3,
  "sepal_width": 3.3,
  "petal_length": 6.0,
  "petal_width": 2.5
}

```

Then click **Execute**. This should give **prediction:2**

## step5: Or Use PowerShell’s Invoke-RestMethod
You can also use command line. 
Goto **Start -> cmd -> open/change to Powershell** and type

```
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/predict" `
  -Body '{"sepal_length":5.1,"sepal_width":3.5,"petal_length":1.4,"petal_width":0.2}' `
  -ContentType "application/json"
```

## step6: Or use python program to access API endpoint

See the code in **step999_access_API_endpoint.py** . Run this file in  dedicated terminal.

