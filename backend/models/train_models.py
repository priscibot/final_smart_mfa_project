"""
Machine Learning Model Training Module
Trains Isolation Forest and SVM models for behavioral biometric authentication.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
from pathlib import Path
import json


class BehavioralAuthenticator:
    """Train and use ML models for behavioral authentication."""
    
    def __init__(self, model_type='isolation_forest'):
        """
        Initialize authenticator.
        
        Args:
            model_type: 'isolation_forest' or 'ocsvm'
        """
        self.model_type = model_type
        self.scaler = StandardScaler()
        self.models = {}  # One model per user
        self.feature_columns = None
        
    def load_data(self, data_path='data/raw/behavioral_data.csv'):
        """Load behavioral dataset."""
        df = pd.read_csv(data_path)
        print(f"Loaded {len(df)} sessions for {df['user_id'].nunique()} users")
        
        # Store feature columns (exclude metadata)
        self.feature_columns = [col for col in df.columns 
                               if col not in ['user_id', 'session_id', 'is_legitimate']]
        
        return df
    
    def train_user_model(self, user_data, contamination=0.1):
        """
        Train a model for a single user using only their legitimate sessions.
        
        Args:
            user_data: DataFrame of sessions for one user
            contamination: Expected proportion of outliers (impostors)
            
        Returns:
            Trained model
        """
        # Use only legitimate sessions for training
        legitimate_data = user_data[user_data['is_legitimate'] == 1]
        
        if len(legitimate_data) < 10:
            print(f"Warning: Only {len(legitimate_data)} legitimate sessions for training")
            return None
        
        # Extract features
        X = legitimate_data[self.feature_columns].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        if self.model_type == 'isolation_forest':
            model = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100,
                max_samples='auto',
                bootstrap=True
            )
        else:  # One-Class SVM
            model = OneClassSVM(
                kernel='rbf',
                gamma='auto',
                nu=contamination
            )
        
        model.fit(X_scaled)
        return model
    
    def train_all_users(self, df, contamination=0.1):
        """Train individual models for all users."""
        print(f"\nTraining {self.model_type} models for each user...")
        
        for user_id in df['user_id'].unique():
            user_data = df[df['user_id'] == user_id]
            
            # Train model for this user
            model = self.train_user_model(user_data, contamination)
            
            if model is not None:
                self.models[user_id] = {
                    'model': model,
                    'scaler': StandardScaler().fit(
                        user_data[user_data['is_legitimate'] == 1][self.feature_columns].values
                    )
                }
        
        print(f"Trained {len(self.models)} user models")
    
    def predict(self, user_id, features):
        """
        Predict if a session is legitimate for a given user.
        
        Args:
            user_id: User identifier
            features: Feature dictionary or array
            
        Returns:
            (is_legitimate: bool, confidence_score: float)
        """
        if user_id not in self.models:
            return False, 0.0
        
        user_model = self.models[user_id]
        
        # Convert features to array if dict
        if isinstance(features, dict):
            X = np.array([features.get(f, 0.0) for f in self.feature_columns])
        else:
            X = np.array(features)
        
        X = X.reshape(1, -1)
        
        # Scale using user-specific scaler
        X_scaled = user_model['scaler'].transform(X)
        
        # Predict
        prediction = user_model['model'].predict(X_scaled)[0]
        
        # Get anomaly score (higher = more normal)
        if hasattr(user_model['model'], 'score_samples'):
            score = user_model['model'].score_samples(X_scaled)[0]
            # Normalize score to 0-1 range (approximate)
            confidence = 1 / (1 + np.exp(-score))
        else:
            # For models without score_samples
            confidence = 0.8 if prediction == 1 else 0.2
        
        is_legitimate = prediction == 1
        
        return is_legitimate, float(confidence)
    
    def save_models(self, output_dir='data/models'):
        """Save trained models to disk."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save each user model
        for user_id, user_model in self.models.items():
            user_dir = output_path / user_id
            user_dir.mkdir(exist_ok=True)
            
            joblib.dump(user_model['model'], user_dir / 'model.pkl')
            joblib.dump(user_model['scaler'], user_dir / 'scaler.pkl')
        
        # Save metadata
        metadata = {
            'model_type': self.model_type,
            'num_users': len(self.models),
            'feature_columns': self.feature_columns,
        }
        
        with open(output_path / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Saved {len(self.models)} models to {output_path}")
    
    def load_models(self, model_dir='data/models'):
        """Load trained models from disk."""
        model_path = Path(model_dir)
        
        # Load metadata
        with open(model_path / 'metadata.json', 'r') as f:
            metadata = json.load(f)
        
        self.model_type = metadata['model_type']
        self.feature_columns = metadata['feature_columns']
        
        # Load each user model
        for user_dir in model_path.iterdir():
            if user_dir.is_dir():
                user_id = user_dir.name
                
                model = joblib.load(user_dir / 'model.pkl')
                scaler = joblib.load(user_dir / 'scaler.pkl')
                
                self.models[user_id] = {
                    'model': model,
                    'scaler': scaler
                }
        
        print(f"Loaded {len(self.models)} models from {model_path}")


if __name__ == '__main__':
    # Train Isolation Forest models
    print("Training Isolation Forest models...")
    if_auth = BehavioralAuthenticator(model_type='isolation_forest')
    df = if_auth.load_data('../data/raw/behavioral_data.csv')
    if_auth.train_all_users(df, contamination=0.15)
    if_auth.save_models('../data/models/isolation_forest')
    
    print("\n" + "="*50)
    
    # Train One-Class SVM models for comparison
    print("Training One-Class SVM models...")
    svm_auth = BehavioralAuthenticator(model_type='ocsvm')
    svm_auth.feature_columns = if_auth.feature_columns  # Use same features
    svm_auth.train_all_users(df, contamination=0.15)
    svm_auth.save_models('../data/models/ocsvm')
    
    print("\nModel training complete!")
