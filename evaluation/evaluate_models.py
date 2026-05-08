"""
Model Evaluation Module
Computes authentication metrics, confusion matrices, and performance visualizations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report, roc_curve, auc
from pathlib import Path
import json
import sys
sys.path.append('../backend/models')
from train_models import BehavioralAuthenticator


class AuthenticationEvaluator:
    """Evaluate behavioral authentication system performance."""
    
    def __init__(self, model_type='isolation_forest'):
        self.model_type = model_type
        self.results = {}
        
    def evaluate_model(self, authenticator, test_data):
        """
        Evaluate model on test data.
        
        Args:
            authenticator: Trained BehavioralAuthenticator
            test_data: DataFrame with test sessions
            
        Returns:
            Dictionary of metrics
        """
        y_true = []
        y_pred = []
        y_scores = []
        
        print(f"Evaluating {len(test_data)} test sessions...")
        
        for idx, row in test_data.iterrows():
            user_id = row['user_id']
            true_label = row['is_legitimate']
            
            # Extract features
            features = {col: row[col] for col in authenticator.feature_columns}
            
            # Predict
            is_legit, confidence = authenticator.predict(user_id, features)
            
            y_true.append(true_label)
            y_pred.append(1 if is_legit else 0)
            y_scores.append(confidence)
        
        # Calculate metrics
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        accuracy = (tp + tn) / (tp + tn + fp + fn)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # FAR and FRR (critical for biometric systems)
        far = fp / (fp + tn) if (fp + tn) > 0 else 0  # False Acceptance Rate
        frr = fn / (fn + tp) if (fn + tp) > 0 else 0  # False Rejection Rate
        
        # Calculate EER (Equal Error Rate) - where FAR = FRR
        fpr, tpr, thresholds = roc_curve(y_true, y_scores)
        fnr = 1 - tpr
        eer_threshold = thresholds[np.nanargmin(np.absolute((fnr - fpr)))]
        eer = fpr[np.nanargmin(np.absolute((fnr - fpr)))]
        
        # ROC AUC
        roc_auc = auc(fpr, tpr)
        
        metrics = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'far': far,  # False Acceptance Rate
            'frr': frr,  # False Rejection Rate
            'eer': eer,  # Equal Error Rate
            'roc_auc': roc_auc,
            'confusion_matrix': {
                'tn': int(tn),
                'fp': int(fp),
                'fn': int(fn),
                'tp': int(tp)
            }
        }
        
        self.results[self.model_type] = {
            'metrics': metrics,
            'y_true': y_true,
            'y_pred': y_pred,
            'y_scores': y_scores,
            'fpr': fpr.tolist(),
            'tpr': tpr.tolist()
        }
        
        return metrics
    
    def plot_confusion_matrix(self, metrics, save_path='results/confusion_matrix.png'):
        """Plot confusion matrix."""
        cm = np.array([
            [metrics['confusion_matrix']['tn'], metrics['confusion_matrix']['fp']],
            [metrics['confusion_matrix']['fn'], metrics['confusion_matrix']['tp']]
        ])
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=True,
                    xticklabels=['Impostor', 'Legitimate'],
                    yticklabels=['Impostor', 'Legitimate'])
        plt.title(f'Confusion Matrix - {self.model_type.replace("_", " ").title()}', fontsize=14, fontweight='bold')
        plt.ylabel('True Label', fontsize=12)
        plt.xlabel('Predicted Label', fontsize=12)
        plt.tight_layout()
        
        output_path = Path(save_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved confusion matrix to {save_path}")
    
    def plot_roc_curve(self, save_path='results/roc_curve.png'):
        """Plot ROC curve."""
        result = self.results[self.model_type]
        fpr = np.array(result['fpr'])
        tpr = np.array(result['tpr'])
        roc_auc = result['metrics']['roc_auc']
        
        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, color='darkorange', lw=2, 
                label=f'ROC curve (AUC = {roc_auc:.3f})')
        plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random Classifier')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate (FAR)', fontsize=12)
        plt.ylabel('True Positive Rate (1 - FRR)', fontsize=12)
        plt.title(f'ROC Curve - {self.model_type.replace("_", " ").title()}', fontsize=14, fontweight='bold')
        plt.legend(loc="lower right")
        plt.grid(alpha=0.3)
        plt.tight_layout()
        
        output_path = Path(save_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved ROC curve to {save_path}")
    
    def plot_metrics_comparison(self, all_metrics, save_path='results/metrics_comparison.png'):
        """Plot comparison of different metrics."""
        metrics_names = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
        
        models = list(all_metrics.keys())
        values = [[all_metrics[m]['accuracy'], all_metrics[m]['precision'], 
                  all_metrics[m]['recall'], all_metrics[m]['f1_score']] 
                 for m in models]
        
        x = np.arange(len(metrics_names))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for i, model in enumerate(models):
            offset = width * (i - len(models)/2 + 0.5)
            ax.bar(x + offset, values[i], width, label=model.replace('_', ' ').title())
        
        ax.set_ylabel('Score', fontsize=12)
        ax.set_title('Performance Metrics Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(metrics_names)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim([0, 1.1])
        
        plt.tight_layout()
        
        output_path = Path(save_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved metrics comparison to {save_path}")
    
    def generate_report(self, metrics, save_path='results/evaluation_report.txt'):
        """Generate text report of evaluation results."""
        report = f"""
{'='*70}
BEHAVIORAL BIOMETRIC AUTHENTICATION SYSTEM EVALUATION REPORT
{'='*70}

Model Type: {self.model_type.replace('_', ' ').title()}

CONFUSION MATRIX:
                    Predicted Impostor    Predicted Legitimate
Actual Impostor           {metrics['confusion_matrix']['tn']:5d}                 {metrics['confusion_matrix']['fp']:5d}
Actual Legitimate         {metrics['confusion_matrix']['fn']:5d}                 {metrics['confusion_matrix']['tp']:5d}

PERFORMANCE METRICS:
  Accuracy:              {metrics['accuracy']*100:6.2f}%
  Precision:             {metrics['precision']*100:6.2f}%
  Recall (TPR):          {metrics['recall']*100:6.2f}%
  F1-Score:              {metrics['f1_score']*100:6.2f}%

BIOMETRIC-SPECIFIC METRICS:
  FAR (False Accept):    {metrics['far']*100:6.2f}%  ← Impostor incorrectly accepted
  FRR (False Reject):    {metrics['frr']*100:6.2f}%  ← Legitimate user incorrectly rejected
  EER (Equal Error):     {metrics['eer']*100:6.2f}%  ← Point where FAR = FRR
  ROC AUC:               {metrics['roc_auc']:6.4f}

INTERPRETATION:
  • Accuracy of {metrics['accuracy']*100:.1f}% means the system correctly identifies
    {metrics['accuracy']*100:.1f}% of all authentication attempts.
    
  • FAR of {metrics['far']*100:.2f}% means {metrics['far']*100:.2f}% of impostor attempts are
    incorrectly accepted (security risk).
    
  • FRR of {metrics['frr']*100:.2f}% means {metrics['frr']*100:.2f}% of legitimate users are
    incorrectly rejected (usability issue).
    
  • EER of {metrics['eer']*100:.2f}% represents the optimal operating point where
    security and usability are balanced.

{'='*70}
"""
        
        output_path = Path(save_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\nSaved evaluation report to {save_path}")


if __name__ == '__main__':
    from sklearn.model_selection import train_test_split
    
    # Load data
    print("Loading dataset...")
    df = pd.read_csv('../data/raw/behavioral_data.csv')
    
    # Split data by user to ensure proper train/test separation
    users = df['user_id'].unique()
    
    # Use 80% of sessions for training, 20% for testing (per user)
    train_data = []
    test_data = []
    
    for user in users:
        user_df = df[df['user_id'] == user]
        legit = user_df[user_df['is_legitimate'] == 1]
        impostor = user_df[user_df['is_legitimate'] == 0]
        
        # Split legitimate sessions
        if len(legit) > 0:
            train_legit, test_legit = train_test_split(legit, test_size=0.2, random_state=42)
            train_data.append(train_legit)
            test_data.append(test_legit)
        
        # All impostor sessions go to test (more realistic)
        if len(impostor) > 0:
            test_data.append(impostor)
    
    train_df = pd.concat(train_data, ignore_index=True)
    test_df = pd.concat(test_data, ignore_index=True)
    
    print(f"Train set: {len(train_df)} sessions")
    print(f"Test set: {len(test_df)} sessions ({test_df['is_legitimate'].sum()} legitimate, {(~test_df['is_legitimate'].astype(bool)).sum()} impostor)")
    
    # Evaluate Isolation Forest
    print("\n" + "="*70)
    print("EVALUATING ISOLATION FOREST MODEL")
    print("="*70)
    
    if_auth = BehavioralAuthenticator(model_type='isolation_forest')
    if_auth.load_data('../data/raw/behavioral_data.csv')
    if_auth.train_all_users(train_df, contamination=0.15)
    
    if_evaluator = AuthenticationEvaluator(model_type='isolation_forest')
    if_metrics = if_evaluator.evaluate_model(if_auth, test_df)
    
    if_evaluator.plot_confusion_matrix(if_metrics, 'results/isolation_forest_confusion_matrix.png')
    if_evaluator.plot_roc_curve('results/isolation_forest_roc_curve.png')
    if_evaluator.generate_report(if_metrics, 'results/isolation_forest_report.txt')
    
    # Evaluate One-Class SVM
    print("\n" + "="*70)
    print("EVALUATING ONE-CLASS SVM MODEL")
    print("="*70)
    
    svm_auth = BehavioralAuthenticator(model_type='ocsvm')
    svm_auth.feature_columns = if_auth.feature_columns
    svm_auth.train_all_users(train_df, contamination=0.15)
    
    svm_evaluator = AuthenticationEvaluator(model_type='ocsvm')
    svm_metrics = svm_evaluator.evaluate_model(svm_auth, test_df)
    
    svm_evaluator.plot_confusion_matrix(svm_metrics, 'results/ocsvm_confusion_matrix.png')
    svm_evaluator.plot_roc_curve('results/ocsvm_roc_curve.png')
    svm_evaluator.generate_report(svm_metrics, 'results/ocsvm_report.txt')
    
    # Comparison plot
    print("\n" + "="*70)
    print("GENERATING COMPARISON CHARTS")
    print("="*70)
    
    all_metrics = {
        'Isolation Forest': if_metrics,
        'One-Class SVM': svm_metrics
    }
    
    if_evaluator.plot_metrics_comparison(all_metrics, 'results/model_comparison.png')
    
    # Save summary
    summary = {
        'isolation_forest': if_metrics,
        'ocsvm': svm_metrics
    }
    
    with open('results/evaluation_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "="*70)
    print("EVALUATION COMPLETE!")
    print("="*70)
    print("\nGenerated files:")
    print("  - results/isolation_forest_confusion_matrix.png")
    print("  - results/isolation_forest_roc_curve.png")
    print("  - results/isolation_forest_report.txt")
    print("  - results/ocsvm_confusion_matrix.png")
    print("  - results/ocsvm_roc_curve.png")
    print("  - results/ocsvm_report.txt")
    print("  - results/model_comparison.png")
    print("  - results/evaluation_summary.json")
