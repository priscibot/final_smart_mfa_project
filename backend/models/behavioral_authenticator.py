"""
Behavioral Biometric Authentication Models
Implements Isolation Forest and SVM for continuous authentication
"""

import numpy as np
import pandas as pd
import pickle
import json
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                             f1_score, confusion_matrix, roc_auc_score, roc_curve)
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

class BehavioralAuthenticator:
    def __init__(self, model_type='isolation_forest'):
        """
        Initialize behavioral authenticator
        model_type: 'isolation_forest' or 'svm'
        """
        self.model_type = model_type
        self.scaler = StandardScaler()
        self.model = None
        self.feature_columns = None
        self.training_metrics = {}
        
        if model_type == 'isolation_forest':
            self.model = IsolationForest(
                contamination=0.2,  # Expected proportion of outliers
                random_state=42,
                n_estimators=100,
                max_samples='auto'
            )
        elif model_type == 'svm':
            self.model = OneClassSVM(
                kernel='rbf',
                gamma='auto',
                nu=0.2  # Upper bound on training errors
            )
        else:
            raise ValueError("model_type must be 'isolation_forest' or 'svm'")
    
    def prepare_features(self, df):
        """Extract and prepare feature columns"""
        # Exclude non-feature columns
        exclude_cols = ['user_id', 'timestamp', 'is_legitimate']
        self.feature_columns = [col for col in df.columns if col not in exclude_cols]
        
        X = df[self.feature_columns].values
        y = df['is_legitimate'].values if 'is_legitimate' in df.columns else None
        
        return X, y
    
    def train(self, train_df, validation_split=0.2):
        """Train the behavioral authentication model"""
        print(f"\n{'='*60}")
        print(f"Training {self.model_type.upper()} Model")
        print(f"{'='*60}")
        
        # Prepare features
        X, y = self.prepare_features(train_df)
        
        # Split for validation
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=42, stratify=y
        )
        
        print(f"Training samples: {len(X_train)}")
        print(f"Validation samples: {len(X_val)}")
        print(f"Features: {len(self.feature_columns)}")
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        # Train on legitimate users only (anomaly detection)
        X_train_legit = X_train_scaled[y_train == 1]
        print(f"Training on {len(X_train_legit)} legitimate user samples...")
        
        self.model.fit(X_train_legit)
        
        # Validation
        predictions_train = self.model.predict(X_train_scaled)
        predictions_val = self.model.predict(X_val_scaled)
        
        # Convert predictions: 1 = legitimate, -1 = anomaly/impostor
        predictions_train_binary = (predictions_train == 1).astype(int)
        predictions_val_binary = (predictions_val == 1).astype(int)
        
        # Calculate metrics
        train_acc = accuracy_score(y_train, predictions_train_binary)
        val_acc = accuracy_score(y_val, predictions_val_binary)
        val_precision = precision_score(y_val, predictions_val_binary)
        val_recall = recall_score(y_val, predictions_val_binary)
        val_f1 = f1_score(y_val, predictions_val_binary)
        
        # Calculate FAR and FRR
        cm = confusion_matrix(y_val, predictions_val_binary)
        tn, fp, fn, tp = cm.ravel()
        
        far = fp / (fp + tn) if (fp + tn) > 0 else 0  # False Acceptance Rate
        frr = fn / (fn + tp) if (fn + tp) > 0 else 0  # False Rejection Rate
        
        self.training_metrics = {
            'train_accuracy': train_acc,
            'val_accuracy': val_acc,
            'val_precision': val_precision,
            'val_recall': val_recall,
            'val_f1_score': val_f1,
            'far': far,
            'frr': frr,
            'confusion_matrix': cm.tolist(),
            'model_type': self.model_type,
            'training_date': datetime.now().isoformat()
        }
        
        print(f"\nTraining Results:")
        print(f"  Training Accuracy: {train_acc:.4f}")
        print(f"  Validation Accuracy: {val_acc:.4f}")
        print(f"  Precision: {val_precision:.4f}")
        print(f"  Recall: {val_recall:.4f}")
        print(f"  F1-Score: {val_f1:.4f}")
        print(f"  FAR (False Acceptance Rate): {far:.4f}")
        print(f"  FRR (False Rejection Rate): {frr:.4f}")
        
        return self.training_metrics
    
    def evaluate(self, test_df):
        """Evaluate model on test data"""
        print(f"\n{'='*60}")
        print(f"Evaluating {self.model_type.upper()} Model")
        print(f"{'='*60}")
        
        X_test, y_test = self.prepare_features(test_df)
        X_test_scaled = self.scaler.transform(X_test)
        
        predictions = self.model.predict(X_test_scaled)
        predictions_binary = (predictions == 1).astype(int)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, predictions_binary)
        precision = precision_score(y_test, predictions_binary)
        recall = recall_score(y_test, predictions_binary)
        f1 = f1_score(y_test, predictions_binary)
        
        # Confusion matrix
        cm = confusion_matrix(y_test, predictions_binary)
        tn, fp, fn, tp = cm.ravel()
        
        far = fp / (fp + tn) if (fp + tn) > 0 else 0
        frr = fn / (fn + tp) if (fn + tp) > 0 else 0
        
        test_metrics = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'far': far,
            'frr': frr,
            'confusion_matrix': cm.tolist(),
            'test_samples': len(X_test)
        }
        
        print(f"\nTest Results:")
        print(f"  Accuracy: {accuracy:.4f}")
        print(f"  Precision: {precision:.4f}")
        print(f"  Recall: {recall:.4f}")
        print(f"  F1-Score: {f1:.4f}")
        print(f"  FAR: {far:.4f}")
        print(f"  FRR: {frr:.4f}")
        print(f"\nConfusion Matrix:")
        print(f"  TN: {tn}  FP: {fp}")
        print(f"  FN: {fn}  TP: {tp}")
        
        return test_metrics, cm, predictions_binary, y_test
    
    def predict(self, features_dict):
        """Predict if behavior matches legitimate user"""
        # Convert dict to array in correct feature order
        features = np.array([[features_dict[col] for col in self.feature_columns]])
        features_scaled = self.scaler.transform(features)
        
        prediction = self.model.predict(features_scaled)[0]
        
        # Get anomaly score (distance from normal behavior)
        if self.model_type == 'isolation_forest':
            score = self.model.score_samples(features_scaled)[0]
        else:  # SVM
            score = self.model.decision_function(features_scaled)[0]
        
        is_legitimate = prediction == 1
        confidence = abs(score)
        
        return {
            'is_legitimate': bool(is_legitimate),
            'confidence': float(confidence),
            'prediction': int(prediction),
            'timestamp': datetime.now().isoformat()
        }
    
    def save_model(self, filepath):
        """Save trained model and scaler"""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns,
            'model_type': self.model_type,
            'training_metrics': self.training_metrics
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"\n✓ Model saved to {filepath}")
    
    @classmethod
    def load_model(cls, filepath):
        """Load trained model"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        authenticator = cls(model_type=model_data['model_type'])
        authenticator.model = model_data['model']
        authenticator.scaler = model_data['scaler']
        authenticator.feature_columns = model_data['feature_columns']
        authenticator.training_metrics = model_data['training_metrics']
        
        print(f"✓ Model loaded from {filepath}")
        return authenticator


def plot_confusion_matrix(cm, model_name, save_path):
    """Plot and save confusion matrix"""
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=['Impostor', 'Legitimate'],
                yticklabels=['Impostor', 'Legitimate'])
    plt.title(f'Confusion Matrix - {model_name}')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Confusion matrix saved to {save_path}")


def compare_models(results_if, results_svm):
    """Compare Isolation Forest and SVM results"""
    metrics = ['accuracy', 'precision', 'recall', 'f1_score', 'far', 'frr']
    
    comparison = pd.DataFrame({
        'Metric': metrics,
        'Isolation Forest': [results_if[m] for m in metrics],
        'SVM': [results_svm[m] for m in metrics]
    })
    
    print("\n" + "="*60)
    print("MODEL COMPARISON")
    print("="*60)
    print(comparison.to_string(index=False))
    
    return comparison


if __name__ == "__main__":
    # This will be called from train_models.py
    pass
