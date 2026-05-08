"""
Synthetic Behavioral Biometric Data Generator
Generates realistic keystroke dynamics and mouse movement patterns for multiple users.
"""

import numpy as np
import pandas as pd
import json
from pathlib import Path

np.random.seed(42)

class BehavioralDataGenerator:
    """Generate synthetic behavioral biometric data for authentication research."""
    
    def __init__(self, num_users=50, sessions_per_user=30):
        self.num_users = num_users
        self.sessions_per_user = sessions_per_user
        self.user_profiles = {}
        
    def generate_user_profile(self, user_id):
        """Generate a unique behavioral profile for a user."""
        profile = {
            'user_id': user_id,
            # Keystroke dynamics parameters
            'avg_dwell_time': np.random.uniform(80, 180),  # ms
            'dwell_std': np.random.uniform(15, 40),
            'avg_flight_time': np.random.uniform(100, 250),  # ms
            'flight_std': np.random.uniform(20, 50),
            'typing_speed': np.random.uniform(150, 400),  # chars per minute
            'error_rate': np.random.uniform(0.01, 0.08),
            
            # Mouse movement parameters
            'avg_mouse_speed': np.random.uniform(200, 600),  # pixels per second
            'mouse_speed_std': np.random.uniform(50, 150),
            'avg_mouse_acceleration': np.random.uniform(50, 200),
            'click_frequency': np.random.uniform(0.5, 3.0),  # clicks per second
            'avg_pause_duration': np.random.uniform(500, 2000),  # ms
            'movement_smoothness': np.random.uniform(0.6, 0.95),  # 0-1 scale
        }
        return profile
    
    def generate_keystroke_session(self, profile, is_legitimate=True, session_id=0):
        """Generate keystroke dynamics for a single session."""
        num_keystrokes = np.random.randint(100, 300)
        
        if is_legitimate:
            # Legitimate user - centered around their profile
            dwell_times = np.random.normal(
                profile['avg_dwell_time'], 
                profile['dwell_std'], 
                num_keystrokes
            )
            flight_times = np.random.normal(
                profile['avg_flight_time'], 
                profile['flight_std'], 
                num_keystrokes - 1
            )
        else:
            # Impostor - different behavioral pattern
            dwell_times = np.random.normal(
                profile['avg_dwell_time'] + np.random.uniform(-50, 50), 
                profile['dwell_std'] * np.random.uniform(1.2, 2.0), 
                num_keystrokes
            )
            flight_times = np.random.normal(
                profile['avg_flight_time'] + np.random.uniform(-60, 60), 
                profile['flight_std'] * np.random.uniform(1.2, 2.0), 
                num_keystrokes - 1
            )
        
        # Ensure positive values
        dwell_times = np.abs(dwell_times)
        flight_times = np.abs(flight_times)
        
        # Calculate aggregate features
        features = {
            'user_id': profile['user_id'],
            'session_id': session_id,
            'is_legitimate': 1 if is_legitimate else 0,
            
            # Dwell time features
            'dwell_mean': np.mean(dwell_times),
            'dwell_std': np.std(dwell_times),
            'dwell_median': np.median(dwell_times),
            'dwell_q1': np.percentile(dwell_times, 25),
            'dwell_q3': np.percentile(dwell_times, 75),
            
            # Flight time features
            'flight_mean': np.mean(flight_times),
            'flight_std': np.std(flight_times),
            'flight_median': np.median(flight_times),
            'flight_q1': np.percentile(flight_times, 25),
            'flight_q3': np.percentile(flight_times, 75),
            
            # Derived features
            'typing_speed_cpm': 60000 / (np.mean(dwell_times) + np.mean(flight_times)),
            'dwell_flight_ratio': np.mean(dwell_times) / (np.mean(flight_times) + 1e-6),
            'keystroke_variance': np.var(dwell_times) + np.var(flight_times),
        }
        
        return features
    
    def generate_mouse_session(self, profile, is_legitimate=True, session_id=0):
        """Generate mouse movement dynamics for a single session."""
        num_movements = np.random.randint(50, 150)
        
        if is_legitimate:
            # Legitimate user
            speeds = np.random.normal(
                profile['avg_mouse_speed'],
                profile['mouse_speed_std'],
                num_movements
            )
            accelerations = np.random.normal(
                profile['avg_mouse_acceleration'],
                profile['mouse_speed_std'] * 0.5,
                num_movements
            )
            pause_durations = np.random.exponential(
                profile['avg_pause_duration'],
                num_movements // 5
            )
        else:
            # Impostor
            speeds = np.random.normal(
                profile['avg_mouse_speed'] + np.random.uniform(-100, 100),
                profile['mouse_speed_std'] * np.random.uniform(1.3, 2.0),
                num_movements
            )
            accelerations = np.random.normal(
                profile['avg_mouse_acceleration'] + np.random.uniform(-50, 50),
                profile['mouse_speed_std'] * np.random.uniform(1.3, 2.0) * 0.5,
                num_movements
            )
            pause_durations = np.random.exponential(
                profile['avg_pause_duration'] * np.random.uniform(0.5, 1.5),
                num_movements // 5
            )
        
        speeds = np.abs(speeds)
        accelerations = np.abs(accelerations)
        pause_durations = np.abs(pause_durations)
        
        features = {
            'user_id': profile['user_id'],
            'session_id': session_id,
            'is_legitimate': 1 if is_legitimate else 0,
            
            # Speed features
            'speed_mean': np.mean(speeds),
            'speed_std': np.std(speeds),
            'speed_median': np.median(speeds),
            'speed_max': np.max(speeds),
            
            # Acceleration features
            'accel_mean': np.mean(accelerations),
            'accel_std': np.std(accelerations),
            'accel_max': np.max(accelerations),
            
            # Pause features
            'pause_mean': np.mean(pause_durations),
            'pause_std': np.std(pause_durations),
            'pause_count': len(pause_durations),
            
            # Derived features
            'movement_efficiency': np.mean(speeds) / (np.std(speeds) + 1e-6),
            'smoothness_score': profile['movement_smoothness'] * (1 + np.random.uniform(-0.1, 0.1)),
        }
        
        return features
    
    def generate_combined_session(self, profile, is_legitimate=True, session_id=0):
        """Generate combined keystroke and mouse features for a session."""
        keystroke_features = self.generate_keystroke_session(profile, is_legitimate, session_id)
        mouse_features = self.generate_mouse_session(profile, is_legitimate, session_id)
        
        # Remove duplicate keys
        mouse_features.pop('user_id', None)
        mouse_features.pop('session_id', None)
        mouse_features.pop('is_legitimate', None)
        
        # Combine
        combined = {**keystroke_features, **mouse_features}
        return combined
    
    def generate_dataset(self):
        """Generate complete dataset with legitimate and impostor sessions."""
        all_sessions = []
        
        print(f"Generating behavioral data for {self.num_users} users...")
        
        for user_id in range(self.num_users):
            # Generate unique profile
            profile = self.generate_user_profile(f"user_{user_id:03d}")
            self.user_profiles[profile['user_id']] = profile
            
            # Generate legitimate sessions
            for session_id in range(self.sessions_per_user):
                session = self.generate_combined_session(profile, is_legitimate=True, session_id=session_id)
                all_sessions.append(session)
            
            # Generate impostor sessions (20% of legitimate sessions)
            num_impostor = int(self.sessions_per_user * 0.2)
            for session_id in range(num_impostor):
                session = self.generate_combined_session(
                    profile, 
                    is_legitimate=False, 
                    session_id=self.sessions_per_user + session_id
                )
                all_sessions.append(session)
        
        df = pd.DataFrame(all_sessions)
        print(f"Generated {len(df)} total sessions ({df['is_legitimate'].sum()} legitimate, {(~df['is_legitimate'].astype(bool)).sum()} impostor)")
        
        return df, self.user_profiles
    
    def save_dataset(self, df, profiles, output_dir='data/raw'):
        """Save generated dataset and profiles to disk."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save main dataset
        df.to_csv(output_path / 'behavioral_data.csv', index=False)
        print(f"Saved dataset to {output_path / 'behavioral_data.csv'}")
        
        # Save user profiles
        with open(output_path / 'user_profiles.json', 'w') as f:
            json.dump(profiles, f, indent=2)
        print(f"Saved user profiles to {output_path / 'user_profiles.json'}")
        
        # Save dataset summary
        summary = {
            'num_users': self.num_users,
            'sessions_per_user': self.sessions_per_user,
            'total_sessions': len(df),
            'legitimate_sessions': int(df['is_legitimate'].sum()),
            'impostor_sessions': int((~df['is_legitimate'].astype(bool)).sum()),
            'feature_columns': list(df.columns),
        }
        
        with open(output_path / 'dataset_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Saved summary to {output_path / 'dataset_summary.json'}")


if __name__ == '__main__':
    # Generate dataset
    generator = BehavioralDataGenerator(num_users=50, sessions_per_user=30)
    df, profiles = generator.generate_dataset()
    
    # Save to disk
    generator.save_dataset(df, profiles, output_dir='../data/raw')
    
    print("\nDataset Statistics:")
    print(f"Total sessions: {len(df)}")
    print(f"Legitimate sessions: {df['is_legitimate'].sum()}")
    print(f"Impostor sessions: {(~df['is_legitimate'].astype(bool)).sum()}")
    print(f"Number of users: {df['user_id'].nunique()}")
    print(f"Features per session: {len(df.columns) - 3}")  # Exclude user_id, session_id, is_legitimate
    print("\nSample features:")
    print(df.head())
