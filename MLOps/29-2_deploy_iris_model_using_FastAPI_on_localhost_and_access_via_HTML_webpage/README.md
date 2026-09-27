
# Here I show how to deploy a ML model on localhost and access its API endpoint using Web UI written in HTML + Javascript

Here I show how to build web UI using HTML + JavaScript. **The HTML + JavaScript approach is how you would build a production web app**

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

## step2: Create web UI

Create **index.html** and put the HTML + javascript code in there. This file is our web UI that we would use to access the model API endpoint.

## step3: Create FastAPI App

See the code in file **step2_app.py**. Do not run this file.

## step4: Run the FastAPI Server

In the directory where you created above **step2_app.py** file, on the command line type:

```
uvicorn step2_app:app --reload
```
This would actually run **step2_app.py**

## step5: Open web UI
On your browser go to URL: http://127.0.0.1:8000/ui

Enter the following
- Sepal Length: 5.1
- Sepal Width:  3.5
- Petal Length: 1.4
- Petal Width:  0.2
  
Press **Predict**. You would see output **setosa**.
