"""
Synthetic Behavioral Biometric Data Generator
Generates realistic keystroke dynamics and mouse movement patterns for testing
"""

import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
import random

class SyntheticBehavioralDataGenerator:
    def __init__(self, seed=42):
        np.random.seed(seed)
        random.seed(seed)
        
    def generate_keystroke_profile(self, user_id, num_samples=100, is_legitimate=True):
        """
        Generate keystroke dynamics features
        Features: dwell_time, flight_time, typing_speed, error_rate
        """
        if is_legitimate:
            # Legitimate user - consistent patterns with small variance
            base_dwell = np.random.normal(80, 10)  # milliseconds
            base_flight = np.random.normal(120, 15)
            base_speed = np.random.normal(4.5, 0.5)  # keys per second
            base_error = np.random.normal(0.03, 0.01)  # 3% error rate
        else:
            # Impostor - different patterns
            base_dwell = np.random.normal(100, 20)
            base_flight = np.random.normal(150, 25)
            base_speed = np.random.normal(3.8, 0.8)
            base_error = np.random.normal(0.08, 0.03)
        
        samples = []
        for i in range(num_samples):
            # Add temporal variation (fatigue, time of day effects)
            time_factor = 1 + 0.1 * np.sin(i / num_samples * 2 * np.pi)
            
            sample = {
                'user_id': user_id,
                'timestamp': (datetime.now() + timedelta(minutes=i*5)).isoformat(),
                'dwell_time_mean': max(20, base_dwell * time_factor + np.random.normal(0, 5)),
                'dwell_time_std': abs(np.random.normal(10, 3)),
                'flight_time_mean': max(30, base_flight * time_factor + np.random.normal(0, 8)),
                'flight_time_std': abs(np.random.normal(15, 4)),
                'typing_speed': max(1, base_speed * time_factor + np.random.normal(0, 0.2)),
                'error_rate': max(0, min(0.2, base_error + np.random.normal(0, 0.01))),
                'backspace_frequency': abs(np.random.normal(0.05, 0.02)),
                'pause_count': int(abs(np.random.normal(3, 1))),
                'is_legitimate': 1 if is_legitimate else 0
            }
            samples.append(sample)
        
        return samples
    
    def generate_mouse_profile(self, user_id, num_samples=100, is_legitimate=True):
        """
        Generate mouse movement patterns
        Features: velocity, acceleration, curvature, idle_time
        """
        if is_legitimate:
            base_velocity = np.random.normal(300, 50)  # pixels/second
            base_acceleration = np.random.normal(150, 25)
            base_curvature = np.random.normal(0.3, 0.05)
            base_idle = np.random.normal(2.5, 0.5)  # seconds
        else:
            base_velocity = np.random.normal(400, 80)
            base_acceleration = np.random.normal(200, 40)
            base_curvature = np.random.normal(0.5, 0.1)
            base_idle = np.random.normal(3.5, 0.8)
        
        samples = []
        for i in range(num_samples):
            time_factor = 1 + 0.08 * np.sin(i / num_samples * 2 * np.pi)
            
            sample = {
                'user_id': user_id,
                'timestamp': (datetime.now() + timedelta(minutes=i*5)).isoformat(),
                'velocity_mean': max(50, base_velocity * time_factor + np.random.normal(0, 20)),
                'velocity_std': abs(np.random.normal(50, 10)),
                'acceleration_mean': max(20, base_acceleration * time_factor + np.random.normal(0, 15)),
                'acceleration_std': abs(np.random.normal(25, 8)),
                'curvature_mean': max(0.1, base_curvature + np.random.normal(0, 0.02)),
                'idle_time_mean': max(0.5, base_idle + np.random.normal(0, 0.3)),
                'click_frequency': abs(np.random.normal(0.8, 0.2)),
                'scroll_velocity': abs(np.random.normal(150, 30)),
                'is_legitimate': 1 if is_legitimate else 0
            }
            samples.append(sample)
        
        return samples
    
    def generate_combined_profile(self, user_id, num_samples=100, is_legitimate=True):
        """
        Generate combined keystroke + mouse behavioral profile
        """
        keystroke_samples = self.generate_keystroke_profile(user_id, num_samples, is_legitimate)
        mouse_samples = self.generate_mouse_profile(user_id, num_samples, is_legitimate)
        
        combined = []
        for k, m in zip(keystroke_samples, mouse_samples):
            sample = {**k, **{f'mouse_{key}': val for key, val in m.items() if key not in ['user_id', 'timestamp', 'is_legitimate']}}
            combined.append(sample)
        
        return combined
    
    def generate_dataset(self, num_users=20, samples_per_user=100, impostor_ratio=0.2):
        """
        Generate complete dataset with multiple users
        """
        all_data = []
        
        # Generate legitimate user data
        for user_id in range(1, num_users + 1):
            user_samples = self.generate_combined_profile(
                f"user_{user_id:03d}", 
                num_samples=samples_per_user,
                is_legitimate=True
            )
            all_data.extend(user_samples)
        
        # Generate impostor attempts (users trying to impersonate others)
        num_impostor_samples = int(len(all_data) * impostor_ratio)
        for _ in range(num_impostor_samples):
            target_user = f"user_{random.randint(1, num_users):03d}"
            impostor_samples = self.generate_combined_profile(
                target_user,
                num_samples=1,
                is_legitimate=False
            )
            all_data.extend(impostor_samples)
        
        return pd.DataFrame(all_data)
    
    def save_dataset(self, df, filepath):
        """Save dataset to CSV"""
        df.to_csv(filepath, index=False)
        print(f"Dataset saved to {filepath}")
        print(f"Total samples: {len(df)}")
        print(f"Legitimate samples: {df['is_legitimate'].sum()}")
        print(f"Impostor samples: {len(df) - df['is_legitimate'].sum()}")
        print(f"Features: {len(df.columns)}")


if __name__ == "__main__":
    generator = SyntheticBehavioralDataGenerator(seed=42)
    
    # Generate training dataset (larger)
    print("Generating training dataset...")
    train_df = generator.generate_dataset(num_users=30, samples_per_user=150, impostor_ratio=0.2)
    generator.save_dataset(train_df, "raw/behavioral_training_data.csv")
    
    print("\nGenerating test dataset...")
    test_df = generator.generate_dataset(num_users=10, samples_per_user=50, impostor_ratio=0.3)
    generator.save_dataset(test_df, "raw/behavioral_test_data.csv")
    
    print("\n✓ Synthetic behavioral biometric data generation complete!")
