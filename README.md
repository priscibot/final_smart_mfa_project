# Smart Multi-Factor Authentication System with Behavioral Biometrics

A complete implementation of an intelligent authentication system combining traditional password-based authentication with behavioral biometric verification (keystroke dynamics and mouse movement patterns) for higher education institutions.

## Project Structure

```
smart-mfa-system/
├── backend/
│   ├── app.py                          # Flask web application
│   ├── models/
│   │   └── train_models.py             # ML model training (Isolation Forest, SVM)
│   ├── utils/
│   │   ├── generate_synthetic_data.py  # Synthetic behavioral data generator
│   │   └── feature_extraction.py       # Real-time feature extraction
├── frontend/
│   ├── templates/                      # HTML templates
│   └── static/                         # CSS and JavaScript
├── data/
│   ├── raw/                            # Raw behavioral data
│   ├── models/                         # Trained ML models
│       ├── isolation_forest/
│       └── ocsvm/
├── evaluation/
│   ├── evaluate_models.py              # Model evaluation & metrics
│   └── results/                        # Confusion matrices, ROC curves
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Install Dependencies
```bash
cd smart-mfa-system
pip install -r requirements.txt
```

### 2. Generate Synthetic Data
```bash
cd backend/utils
python generate_synthetic_data.py
```

### 3. Train Models
```bash
cd ../models
python train_models.py
```

### 4. Evaluate Models (Generate Charts for Chapter 4)
```bash
cd ../../evaluation
python evaluate_models.py
```

### 5. Run Web Application
```bash
cd ../backend
python app.py
```

Access at: http://127.0.0.1:5000

## Demo Accounts

- **Student**: john.doe / password123 (user_000)
- **Student**: jane.smith / password123 (user_001)
- **Admin**: admin / admin123 (user_002)

## Key Features

✅ Multi-factor authentication (password + behavioral biometrics)  
✅ Keystroke dynamics (typing rhythm, dwell/flight times)  
✅ Mouse movement patterns (speed, acceleration, pauses)  
✅ Isolation Forest & One-Class SVM models  
✅ Real-time authentication with confidence scores  
✅ Confusion matrices, ROC curves, FAR/FRR metrics  
✅ Admin dashboard with system statistics  

## Expected Results

| Metric    | Isolation Forest | One-Class SVM |
|-----------|------------------|---------------|
| Accuracy  | ~94-96%          | ~91-93%       |
| FAR       | ~2-4%            | ~4-6%         |
| FRR       | ~3-5%            | ~5-7%         |
| ROC AUC   | ~0.96            | ~0.93         |

## Generated Files for Report

After running evaluation:
- `evaluation/results/isolation_forest_confusion_matrix.png`
- `evaluation/results/isolation_forest_roc_curve.png`
- `evaluation/results/ocsvm_confusion_matrix.png`
- `evaluation/results/model_comparison.png`
- `evaluation/results/*_report.txt`

## License

Academic Project - Final Year BSc Computer Science
