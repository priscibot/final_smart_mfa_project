"""
Feature Extraction Module
Extracts behavioral biometric features from raw keystroke and mouse event data.
"""

import numpy as np
from typing import List, Dict, Any


class BehavioralFeatureExtractor:
    """Extract features from keystroke and mouse behavioral data."""
    
    @staticmethod
    def extract_keystroke_features(keystroke_events: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Extract keystroke dynamics features from raw events.
        
        Args:
            keystroke_events: List of dicts with keys: 'key', 'press_time', 'release_time'
            
        Returns:
            Dictionary of extracted features
        """
        if len(keystroke_events) < 5:
            return None
        
        dwell_times = []
        flight_times = []
        
        for i, event in enumerate(keystroke_events):
            # Dwell time: time between press and release
            dwell = event['release_time'] - event['press_time']
            dwell_times.append(dwell)
            
            # Flight time: time between release of one key and press of next
            if i < len(keystroke_events) - 1:
                flight = keystroke_events[i + 1]['press_time'] - event['release_time']
                flight_times.append(max(0, flight))  # Ensure non-negative
        
        dwell_times = np.array(dwell_times)
        flight_times = np.array(flight_times) if flight_times else np.array([0])
        
        features = {
            # Dwell time features
            'dwell_mean': float(np.mean(dwell_times)),
            'dwell_std': float(np.std(dwell_times)),
            'dwell_median': float(np.median(dwell_times)),
            'dwell_q1': float(np.percentile(dwell_times, 25)),
            'dwell_q3': float(np.percentile(dwell_times, 75)),
            
            # Flight time features
            'flight_mean': float(np.mean(flight_times)),
            'flight_std': float(np.std(flight_times)),
            'flight_median': float(np.median(flight_times)),
            'flight_q1': float(np.percentile(flight_times, 25)),
            'flight_q3': float(np.percentile(flight_times, 75)),
            
            # Derived features
            'typing_speed_cpm': 60000 / (np.mean(dwell_times) + np.mean(flight_times)),
            'dwell_flight_ratio': float(np.mean(dwell_times) / (np.mean(flight_times) + 1e-6)),
            'keystroke_variance': float(np.var(dwell_times) + np.var(flight_times)),
        }
        
        return features
    
    @staticmethod
    def extract_mouse_features(mouse_events: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Extract mouse movement features from raw events.
        
        Args:
            mouse_events: List of dicts with keys: 'x', 'y', 'timestamp', 'event_type'
            
        Returns:
            Dictionary of extracted features
        """
        if len(mouse_events) < 10:
            return None
        
        speeds = []
        accelerations = []
        pause_durations = []
        prev_speed = 0
        last_move_time = mouse_events[0]['timestamp']
        
        for i in range(1, len(mouse_events)):
            curr = mouse_events[i]
            prev = mouse_events[i - 1]
            
            # Calculate distance and time
            dx = curr['x'] - prev['x']
            dy = curr['y'] - prev['y']
            distance = np.sqrt(dx**2 + dy**2)
            time_delta = curr['timestamp'] - prev['timestamp']
            
            if time_delta > 0:
                # Speed in pixels per second
                speed = (distance / time_delta) * 1000
                speeds.append(speed)
                
                # Acceleration
                acceleration = abs(speed - prev_speed) / time_delta * 1000
                accelerations.append(acceleration)
                prev_speed = speed
                
                # Detect pauses (movement below threshold)
                if speed < 10:  # pixels per second
                    pause_durations.append(time_delta)
                else:
                    last_move_time = curr['timestamp']
        
        speeds = np.array(speeds)
        accelerations = np.array(accelerations)
        pause_durations = np.array(pause_durations) if pause_durations else np.array([0])
        
        features = {
            # Speed features
            'speed_mean': float(np.mean(speeds)),
            'speed_std': float(np.std(speeds)),
            'speed_median': float(np.median(speeds)),
            'speed_max': float(np.max(speeds)),
            
            # Acceleration features
            'accel_mean': float(np.mean(accelerations)),
            'accel_std': float(np.std(accelerations)),
            'accel_max': float(np.max(accelerations)),
            
            # Pause features
            'pause_mean': float(np.mean(pause_durations)),
            'pause_std': float(np.std(pause_durations)),
            'pause_count': len(pause_durations),
            
            # Derived features
            'movement_efficiency': float(np.mean(speeds) / (np.std(speeds) + 1e-6)),
            'smoothness_score': float(1.0 / (1.0 + np.std(accelerations) / (np.mean(accelerations) + 1e-6))),
        }
        
        return features
    
    @staticmethod
    def combine_features(keystroke_features: Dict, mouse_features: Dict) -> Dict[str, float]:
        """Combine keystroke and mouse features into a single feature vector."""
        if keystroke_features is None or mouse_features is None:
            return None
        
        combined = {**keystroke_features, **mouse_features}
        return combined
    
    @staticmethod
    def features_to_array(features: Dict[str, float], feature_order: List[str]) -> np.ndarray:
        """Convert feature dictionary to ordered numpy array."""
        return np.array([features.get(f, 0.0) for f in feature_order])
