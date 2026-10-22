import json
import requests

data = [ 
    [5.4, 3.4, 1.7, 0.2],
    [5.1, 3.7, 1.5, 0.4],
    [5, 2.3, 3.3, 1],
    [6.7, 3.3, 5.7, 2.1],
]

url = 'http://127.0.0.1:8000/predict/'
# url = 'http://13.235.69.71:8000/predict/'

predictions = []
for record in data:
    payload = {'features': record}
    payload = json.dumps(payload)
    response = requests.post(url, data=payload)
    predictions.append(response.json()['predicted_class'])

print("The prediction received from server:\n", predictions)


