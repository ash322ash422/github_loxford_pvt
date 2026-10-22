
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
import joblib
import numpy as np

# Load data
iris = load_iris()
X, y = iris.data, iris.target

# Train model
model = LogisticRegression(max_iter=200)
model.fit(X, y)

# Test to see if prediction works
X_test = [5.1, 3.5, 1.4, 0.2]
X_test = np.array([X_test])  # reshape for sklearn

prediction = model.predict(X_test)
predicted_class_name = load_iris().target_names[prediction[0]]
print("Predicted class:", predicted_class_name )

# Save model
joblib.dump(model, "iris_model.pkl")
print("Model saved as iris_model.pkl")
