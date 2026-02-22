import pandas as pd
import numpy as np
import joblib

import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report

# Load dataset
df = pd.read_csv("Training.csv")

# Remove unnamed column if exists
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

# Features & Target
X = df.drop("prognosis", axis=1)
y = df["prognosis"]

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Model
model = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    random_state=42
)

# Train
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print("Model Accuracy:", accuracy)

joblib.dump(accuracy, "accuracy.pkl")

# Cross validation
cv_scores = cross_val_score(model, X, y, cv=5)
print("Cross Validation Accuracy:", np.mean(cv_scores))

# Save model & feature names
joblib.dump(model, "model.pkl")
joblib.dump(X.columns.tolist(), "symptom_list.pkl")

importances = model.feature_importances_
indices = np.argsort(importances)[-10:]

plt.figure(figsize=(8,6))
plt.barh(range(len(indices)), importances[indices])
plt.yticks(range(len(indices)), [X.columns[i] for i in indices])
plt.title("Top 10 Important Symptoms")
plt.xlabel("Importance Score")
plt.show()
